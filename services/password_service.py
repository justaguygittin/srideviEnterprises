"""
=========================================================
Project : Sridevi Enterprises
File    : password_service.py
Purpose : Password Management - password policy, change password,
          single-use reset tokens, database-backed rate limiting and
          session invalidation.

          Security rules this module follows (see AI_CONTEXT.md
          "Password Management"):
            * Passwords are hashed with Werkzeug (scrypt). Plaintext is
              never stored, logged or returned.
            * Reset tokens: secrets.token_urlsafe(32); only SHA-256 stored;
              30-minute expiry; single use; issuing a new token revokes the
              account's older unused ones; redeeming requires the account's
              role to still match the token's role.
            * A password change or reset increments Users.SessionEpoch, which
              invalidates every existing session (app.py checks it).
            * All timestamps are UTC_TIMESTAMP() so expiry is time-zone safe.

Author  : Srikar
=========================================================
"""

import hashlib
import logging
import random
import re
import secrets
import threading
from typing import Any

from werkzeug.security import check_password_hash, generate_password_hash

from config import Config
from database.db import execute, fetch_all, fetch_one, transaction
from services import email_service

logger = logging.getLogger(__name__)

PORTAL_ROLES = ("Employee", "Admin")

PASSWORD_MIN_LENGTH = 12
PASSWORD_MAX_LENGTH = 128

# Small deny-list of passwords that satisfy the length rule but are
# trivially guessable. Compared case-insensitively.
_COMMON_PASSWORDS = {
    "password1234", "password12345", "password123456", "passw0rd1234",
    "123456789012", "1234567890123", "12345678901234", "qwertyuiop12",
    "qwerty123456", "qwertyuiop123", "abcdefghijkl", "abcd12345678",
    "iloveyou1234", "welcome12345", "admin1234567", "administrator",
    "letmein12345", "changeme1234", "sridevi12345", "sridevi@1234",
    "sridevienterprises", "employee1234",
}

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# action -> (max attempts, window in minutes)
RATE_LIMITS = {
    "login_user": (10, 15),
    "login_ip": (30, 15),
    "reset_request_email": (3, 60),
    "reset_request_ip": (10, 60),
    "reset_submit_ip": (10, 15),
    "change_password_user": (5, 15),
    "admin_reset_target": (3, 60),
    # Admin password re-entry on /admin/invoice-numbering
    # (services/invoice_number_service.py).
    "invoice_number_reauth": (5, 15),
}


# ---------------------------------------------------------------------------
# Hashing helpers
# ---------------------------------------------------------------------------

def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def hash_password(password: str) -> str:
    return generate_password_hash(password)


# ---------------------------------------------------------------------------
# Rate limiting (AuthThrottle)
# ---------------------------------------------------------------------------

def _throttle_key(action: str, subject: str) -> str:
    return _sha256(f"{action}:{(subject or '').strip().lower()}")


def is_rate_limited(action: str, subject: str) -> bool:
    """True when `subject` has reached the configured limit for `action`."""

    limit, window = RATE_LIMITS[action]
    row = fetch_one(
        """
        SELECT COUNT(*) AS attempts FROM AuthThrottle
        WHERE Action = %s AND KeyHash = %s
          AND CreatedAt > UTC_TIMESTAMP() - INTERVAL %s MINUTE
        """,
        (action, _throttle_key(action, subject), window),
    )
    return bool(row) and int(row["attempts"]) >= limit


def record_attempt(action: str, subject: str) -> None:
    """Record one attempt; occasionally purge rows older than a day."""

    execute(
        "INSERT INTO AuthThrottle (Action, KeyHash, CreatedAt) VALUES (%s, %s, UTC_TIMESTAMP());",
        (action, _throttle_key(action, subject)),
    )
    if random.random() < 0.05:
        execute("DELETE FROM AuthThrottle WHERE CreatedAt < UTC_TIMESTAMP() - INTERVAL 1 DAY;")


def clear_attempts(action: str, subject: str) -> None:
    execute(
        "DELETE FROM AuthThrottle WHERE Action = %s AND KeyHash = %s;",
        (action, _throttle_key(action, subject)),
    )


# ---------------------------------------------------------------------------
# Password policy
# ---------------------------------------------------------------------------

def validate_new_password(
    new_password: str,
    confirm_password: str,
    username: str = "",
) -> list[str]:
    """Return a list of user-facing policy errors (empty when acceptable)."""

    errors: list[str] = []
    new_password = new_password or ""

    if len(new_password) < PASSWORD_MIN_LENGTH:
        errors.append(f"Password must be at least {PASSWORD_MIN_LENGTH} characters long.")
    if len(new_password) > PASSWORD_MAX_LENGTH:
        errors.append(f"Password must be at most {PASSWORD_MAX_LENGTH} characters long.")
    if new_password and not new_password.strip():
        errors.append("Password cannot be only spaces.")
    if new_password and len(set(new_password)) == 1:
        errors.append("Password cannot be a single repeated character.")
    if new_password.lower() in _COMMON_PASSWORDS:
        errors.append("This password is too common. Choose something harder to guess.")
    if username and len(username) >= 3 and username.lower() in new_password.lower():
        errors.append("Password must not contain your username.")
    if new_password != (confirm_password or ""):
        errors.append("New password and confirmation do not match.")

    return errors


# ---------------------------------------------------------------------------
# Session invalidation
# ---------------------------------------------------------------------------

def get_session_epoch(user_id: int) -> int | None:
    """Current Users.SessionEpoch, or None if the account no longer exists."""

    row = fetch_one("SELECT SessionEpoch FROM Users WHERE UserID = %s;", (user_id,))
    return int(row["SessionEpoch"]) if row else None


def _set_password_and_bump_epoch(cursor, user_id: int, new_password: str) -> None:
    cursor.execute(
        "UPDATE Users SET Password = %s, SessionEpoch = SessionEpoch + 1 WHERE UserID = %s;",
        (hash_password(new_password), user_id),
    )
    # Any reset link still outstanding for this account is now pointless.
    cursor.execute(
        """
        UPDATE PasswordResetTokens SET RevokedAt = UTC_TIMESTAMP()
        WHERE UserID = %s AND UsedAt IS NULL AND RevokedAt IS NULL;
        """,
        (user_id,),
    )


# ---------------------------------------------------------------------------
# Change password (logged in)
# ---------------------------------------------------------------------------

def change_password(
    user_id: int,
    current_password: str,
    new_password: str,
    confirm_password: str,
) -> list[str]:
    """
    Change a logged-in user's password. Returns a list of user-facing errors;
    an empty list means the password was changed and every session for the
    account has been invalidated.
    """

    if is_rate_limited("change_password_user", str(user_id)):
        return ["Too many incorrect attempts. Please wait 15 minutes and try again."]

    user = fetch_one(
        "SELECT UserID, Username, Password, Role FROM Users WHERE UserID = %s;",
        (user_id,),
    )
    if user is None or user["Role"] not in PORTAL_ROLES:
        return ["Your account could not be found. Please log in again."]

    if not current_password or not check_password_hash(user["Password"], current_password):
        record_attempt("change_password_user", str(user_id))
        return ["Current password is incorrect."]

    errors = validate_new_password(new_password, confirm_password, user["Username"])
    if not errors and check_password_hash(user["Password"], new_password):
        errors.append("New password must be different from your current password.")
    if errors:
        return errors

    with transaction() as conn:
        cursor = conn.cursor()
        _set_password_and_bump_epoch(cursor, user_id, new_password)
        cursor.close()

    clear_attempts("change_password_user", str(user_id))
    logger.info("Password changed - user_id=%s role=%s", user_id, user["Role"])
    return []


# ---------------------------------------------------------------------------
# Reset tokens
# ---------------------------------------------------------------------------

def issue_reset_token(user_id: int, role: str, initiated_by_user_id: int | None = None) -> str:
    """
    Create a new reset token for an account and return the RAW token (to be
    emailed, never stored or logged). Revokes the account's older unused
    tokens so only the newest link works.
    """

    raw_token = secrets.token_urlsafe(32)

    with transaction() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE PasswordResetTokens SET RevokedAt = UTC_TIMESTAMP()
            WHERE UserID = %s AND UsedAt IS NULL AND RevokedAt IS NULL;
            """,
            (user_id,),
        )
        cursor.execute(
            """
            INSERT INTO PasswordResetTokens
                (UserID, UserRole, TokenHash, ExpiresAt, CreatedAt, InitiatedByUserID)
            VALUES (%s, %s, %s, UTC_TIMESTAMP() + INTERVAL %s MINUTE, UTC_TIMESTAMP(), %s);
            """,
            (user_id, role, _sha256(raw_token), Config.PASSWORD_RESET_TOKEN_MINUTES, initiated_by_user_id),
        )
        cursor.close()

    return raw_token


_VALID_TOKEN_QUERY = """
    SELECT t.TokenID, t.UserID, t.UserRole, u.Username
    FROM PasswordResetTokens t
    JOIN Users u ON u.UserID = t.UserID
    WHERE t.TokenHash = %s
      AND t.UsedAt IS NULL
      AND t.RevokedAt IS NULL
      AND t.ExpiresAt > UTC_TIMESTAMP()
      AND CAST(u.Role AS BINARY) = CAST(t.UserRole AS BINARY)
"""
# The role comparison is binary (exact, case-sensitive) on purpose: it is a
# security check, and it also avoids a collation clash between the existing
# Users table (server-default collation) and the new table (unicode_ci).


def get_valid_reset_token(raw_token: str) -> dict[str, Any] | None:
    """Return {TokenID, UserID, UserRole, Username} if the token is usable."""

    if not raw_token or len(raw_token) > 200:
        return None
    return fetch_one(_VALID_TOKEN_QUERY + ";", (_sha256(raw_token),))


def redeem_reset_token(raw_token: str, new_password: str) -> dict[str, Any] | None:
    """
    Atomically consume a reset token and set the new password. Returns the
    token row on success, or None if the token is invalid, expired, already
    used, revoked, or its role no longer matches the account.

    The SELECT ... FOR UPDATE plus the guarded UPDATE make two concurrent
    submissions of the same link impossible to both succeed.
    """

    if not raw_token or len(raw_token) > 200:
        return None

    with transaction() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(_VALID_TOKEN_QUERY + " FOR UPDATE;", (_sha256(raw_token),))
        token = cursor.fetchone()
        if token is None:
            cursor.close()
            return None

        cursor.execute(
            """
            UPDATE PasswordResetTokens SET UsedAt = UTC_TIMESTAMP()
            WHERE TokenID = %s AND UsedAt IS NULL AND RevokedAt IS NULL;
            """,
            (token["TokenID"],),
        )
        if cursor.rowcount != 1:
            cursor.close()
            return None

        _set_password_and_bump_epoch(cursor, token["UserID"], new_password)
        cursor.close()

    logger.info("Password reset completed - user_id=%s role=%s", token["UserID"], token["UserRole"])
    return token


# ---------------------------------------------------------------------------
# Account lookup by email
# ---------------------------------------------------------------------------

def normalise_email(email: str) -> str:
    return (email or "").strip().lower()


def is_valid_email(email: str) -> bool:
    return bool(email) and len(email) <= 254 and bool(_EMAIL_PATTERN.match(email))


def find_accounts_by_email(email: str) -> list[dict[str, Any]]:
    """Every Employee/Admin account whose registered email matches."""

    return fetch_all(
        """
        SELECT u.UserID, u.Username, u.Role, TRIM(e.Email) AS Email
        FROM Users u
        JOIN Employees e ON e.UserID = u.UserID
        WHERE LOWER(TRIM(e.Email)) = %s AND u.Role IN ('Employee', 'Admin');
        """,
        (normalise_email(email),),
    )


# ---------------------------------------------------------------------------
# Reset email
# ---------------------------------------------------------------------------

def build_reset_link(path: str) -> str:
    """Absolute reset link from Config.PUBLIC_BASE_URL (never the Host header)."""

    base = email_service.public_base_url()
    if not base:
        raise email_service.EmailNotConfigured()
    return f"{base}{path}"


_EMAIL_INTROS = {
    "self": "We received a request to reset the password for your Sridevi Enterprises account.",
    "admin": "An administrator has started a password reset for your Sridevi Enterprises account.",
    "welcome": "An administrator has created a Sridevi Enterprises Employee Portal account for you.",
}


def send_reset_email(to_address: str, username: str, link: str, kind: str = "self") -> None:
    """
    Send a set/reset-password email. `kind` is "self" (Forgot Password),
    "admin" (Admin-assisted reset) or "welcome" (new account created by an
    Admin). Raises on configuration or delivery failure.
    """

    if kind == "welcome":
        subject = "Set up your Sridevi Enterprises account"
        action = "To choose your password"
        closing = (
            f"You can log in with your username ({username}) or this email address. If the link has "
            "expired, use \"Forgot password?\" on the login page to get a new one.\n\n"
        )
    else:
        subject = "Reset your Sridevi Enterprises password"
        action = "To choose a new password"
        closing = (
            "If you did not expect this email, you can ignore it - your current password stays unchanged.\n\n"
        )

    body = (
        f"Hello {username},\n\n"
        f"{_EMAIL_INTROS[kind]}\n\n"
        f"{action}, open this link within {Config.PASSWORD_RESET_TOKEN_MINUTES} minutes:\n\n"
        f"{link}\n\n"
        "The link works only once. "
        f"{closing}"
        "Sridevi Enterprises"
    )
    email_service.send_email(to_address, subject, body)


def dispatch_in_background(func, *args) -> None:
    """
    Run `func(*args)` on a short-lived daemon thread so the public
    "Forgot password" response takes the same time whether or not the email
    address belongs to an account (prevents timing-based enumeration).
    Exceptions are logged by type only - never the link or address.
    Tests replace this with a synchronous call.
    """

    def runner():
        try:
            func(*args)
        except Exception as error:
            logger.error("Password reset email FAILED - %s", type(error).__name__)

    threading.Thread(target=runner, daemon=True).start()


def request_self_service_reset(email: str, path_for_token) -> None:
    """
    Handle a public "Forgot password" submission. Always returns None - the
    caller shows the same generic message whatever happens, so the response
    never reveals whether the address is registered.

    `path_for_token(raw_token)` builds the site-relative reset path.
    """

    accounts = find_accounts_by_email(email)

    if len(accounts) != 1:
        if len(accounts) > 1:
            logger.warning(
                "Password reset request matched %d accounts sharing one email - no email sent. "
                "Give each account a unique email address.",
                len(accounts),
            )
        return

    account = accounts[0]
    raw_token = issue_reset_token(account["UserID"], account["Role"])
    link = build_reset_link(path_for_token(raw_token))
    logger.info("Password reset requested - user_id=%s role=%s", account["UserID"], account["Role"])
    dispatch_in_background(send_reset_email, account["Email"], account["Username"], link, "self")


# ---------------------------------------------------------------------------
# Admin-assisted reset
# ---------------------------------------------------------------------------

def get_accounts_for_admin() -> list[dict[str, Any]]:
    """
    Every Employee/Admin account with its registered email and an
    `email_issue` explaining why a reset link could not be sent
    ("missing", "invalid", "ambiguous", "no_record") or None.
    """

    rows = fetch_all(
        """
        SELECT u.UserID, u.Username, u.Role, e.Name, e.Designation, TRIM(e.Email) AS Email,
               e.EmployeeID
        FROM Users u
        LEFT JOIN Employees e ON e.UserID = u.UserID
        WHERE u.Role IN ('Employee', 'Admin')
        ORDER BY u.Role DESC, u.Username;
        """
    )

    counts: dict[str, int] = {}
    for row in rows:
        key = normalise_email(row["Email"])
        if key:
            counts[key] = counts.get(key, 0) + 1

    for row in rows:
        key = normalise_email(row["Email"])
        if row["EmployeeID"] is None:
            row["email_issue"] = "no_record"
        elif not key:
            row["email_issue"] = "missing"
        elif not is_valid_email(key):
            row["email_issue"] = "invalid"
        elif counts.get(key, 0) > 1:
            row["email_issue"] = "ambiguous"
        else:
            row["email_issue"] = None

    return rows


EMAIL_ISSUE_MESSAGES = {
    "no_record": "has no employee record, so there is no registered email to send a reset link to",
    "missing": "has no registered email address",
    "invalid": "has a registered email address that is not valid",
    "ambiguous": "shares its registered email address with another account, so the link could go to the wrong person",
}


def admin_initiate_reset(admin_user_id: int, target_user_id: int, path_for_token) -> tuple[bool, str]:
    """
    Email a reset link to an Employee on an Admin's behalf. Returns
    (success, message for the Admin). The Admin never sees or sets the
    password, and never sees the link.
    """

    target = next((row for row in get_accounts_for_admin() if row["UserID"] == target_user_id), None)

    if target is None:
        return False, "That account was not found."
    if target_user_id == admin_user_id:
        return False, "Use Change Password to change your own password."
    if target["Role"] != "Employee":
        return False, "Only Employee accounts can be reset from this page."

    issue = target["email_issue"]
    if issue:
        return False, (
            f'Reset not sent: "{target["Username"]}" {EMAIL_ISSUE_MESSAGES[issue]}. '
            "Update the employee's email address first."
        )

    if not email_service.is_email_configured():
        return False, "Reset not sent: outgoing email is not configured on this server."

    if is_rate_limited("admin_reset_target", str(target_user_id)):
        return False, "Too many reset links have been sent to this employee recently. Please wait an hour."

    record_attempt("admin_reset_target", str(target_user_id))
    raw_token = issue_reset_token(target_user_id, target["Role"], initiated_by_user_id=admin_user_id)

    try:
        send_reset_email(target["Email"], target["Username"], build_reset_link(path_for_token(raw_token)), "admin")
    except Exception as error:
        # Revoke the link we could not deliver so nothing usable is left behind.
        execute(
            """
            UPDATE PasswordResetTokens SET RevokedAt = UTC_TIMESTAMP()
            WHERE UserID = %s AND UsedAt IS NULL AND RevokedAt IS NULL;
            """,
            (target_user_id,),
        )
        logger.error(
            "Admin-initiated reset email FAILED - admin_user_id=%s target_user_id=%s error=%s",
            admin_user_id, target_user_id, type(error).__name__,
        )
        return False, "Reset not sent: the email could not be delivered. Check the mail settings and try again."

    logger.info(
        "Admin-initiated password reset sent - admin_user_id=%s target_user_id=%s",
        admin_user_id, target_user_id,
    )
    return True, f'A password reset link was emailed to "{target["Username"]}". It expires in ' \
                 f"{Config.PASSWORD_RESET_TOKEN_MINUTES} minutes."
