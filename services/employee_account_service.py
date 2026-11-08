"""
=========================================================
Project : Sridevi Enterprises
File    : employee_account_service.py
Purpose : Admin "Add Employee" - create an Employee Portal account
          (Users + Employees rows) and email the new employee a
          single-use link to choose their own password.

          The Admin never sets, sees, or receives a password: the account
          is created with a random password nobody knows (hashed, then
          discarded), so the only way in is the emailed link - or, once it
          expires, "Forgot password?" / the Admin's "Send reset link".

          New accounts are always Role = 'Employee'. Creating Admin
          accounts is deliberately not offered here.

Author  : Srikar
=========================================================
"""

import logging
import re
import secrets
from typing import Any

import mysql.connector

from config import Config
from database.db import execute, fetch_one, transaction
from services import email_service, password_service

logger = logging.getLogger(__name__)

# Column limits from 002_create_users.sql / 003_create_employees.sql.
USERNAME_MIN, USERNAME_MAX = 3, 50
NAME_MAX = 100
EMAIL_MAX = 100
PHONE_MAX = 20
DESIGNATION_MAX = 50

_USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
_PHONE_PATTERN = re.compile(r"^\+?[0-9 ()-]{6,20}$")


def validate_new_employee_form(form) -> tuple[dict[str, str], dict[str, str]]:
    """
    Validate the Add Employee form. Returns (form_data, errors) where
    errors maps a field name to a user-facing message.
    """

    data = {
        "username": (form.get("username") or "").strip(),
        "name": (form.get("name") or "").strip(),
        "email": password_service.normalise_email(form.get("email") or ""),
        "phone": (form.get("phone") or "").strip(),
        "designation": (form.get("designation") or "").strip(),
    }
    errors: dict[str, str] = {}

    username = data["username"]
    if not USERNAME_MIN <= len(username) <= USERNAME_MAX:
        errors["username"] = f"Username must be {USERNAME_MIN}-{USERNAME_MAX} characters."
    elif not _USERNAME_PATTERN.match(username):
        # No "@": login accepts a username OR an email, so a username that
        # looks like an email would make the two ambiguous.
        errors["username"] = "Use only letters, numbers, dots, hyphens and underscores (no spaces or @)."
    elif fetch_one("SELECT UserID FROM Users WHERE LOWER(Username) = %s LIMIT 1;", (username.lower(),)):
        errors["username"] = "This username is already taken."

    if not data["name"]:
        errors["name"] = "Full name is required."
    elif len(data["name"]) > NAME_MAX:
        errors["name"] = f"Full name must be at most {NAME_MAX} characters."

    email = data["email"]
    if not email:
        errors["email"] = "Email is required - the employee sets their password from a link sent to it."
    elif len(email) > EMAIL_MAX or not password_service.is_valid_email(email):
        errors["email"] = "Enter a valid email address."
    elif fetch_one(
        "SELECT EmployeeID FROM Employees WHERE LOWER(TRIM(Email)) = %s LIMIT 1;", (email,)
    ) or fetch_one("SELECT UserID FROM Users WHERE LOWER(Username) = %s LIMIT 1;", (email,)):
        errors["email"] = "Another account already uses this email address. Each employee needs their own."

    if data["phone"] and not _PHONE_PATTERN.match(data["phone"]):
        errors["phone"] = "Enter a valid phone number (digits, spaces, +, - only)."

    if len(data["designation"]) > DESIGNATION_MAX:
        errors["designation"] = f"Designation must be at most {DESIGNATION_MAX} characters."

    return data, errors


def create_employee_account(
    admin_user_id: int,
    data: dict[str, str],
    path_for_token,
) -> tuple[dict[str, Any] | None, str, str]:
    """
    Create the account and email the set-password link.

    Returns (account or None, flash category, message for the Admin):
      * (None, "danger", ...)   - nothing was created.
      * (account, "success", ...) - created and the email was sent.
      * (account, "warning", ...) - created, but the email failed; the
        undelivered link is revoked and the Admin can use "Send reset link"
        once mail works.
    """

    if not email_service.is_email_configured():
        return None, "danger", (
            "Employee not created: outgoing email is not configured on this server, so the new "
            "employee would have no way to set a password."
        )

    unusable_password = password_service.hash_password(secrets.token_urlsafe(48))

    try:
        with transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO Users (Username, Password, Role) VALUES (%s, %s, 'Employee');",
                (data["username"], unusable_password),
            )
            user_id = cursor.lastrowid
            cursor.execute(
                """
                INSERT INTO Employees (UserID, Name, Phone, Email, Designation)
                VALUES (%s, %s, %s, %s, %s);
                """,
                (user_id, data["name"], data["phone"] or None, data["email"], data["designation"] or None),
            )
            cursor.close()
    except mysql.connector.IntegrityError:
        # Lost a race with another Admin creating the same username.
        return None, "danger", "Employee not created: this username was just taken. Choose another."

    account = {"UserID": user_id, "Username": data["username"], "Email": data["email"]}
    logger.info("Employee account created - admin_user_id=%s new_user_id=%s", admin_user_id, user_id)

    raw_token = password_service.issue_reset_token(user_id, "Employee", initiated_by_user_id=admin_user_id)
    try:
        password_service.send_reset_email(
            data["email"], data["username"], password_service.build_reset_link(path_for_token(raw_token)), "welcome"
        )
    except Exception as error:
        execute(
            """
            UPDATE PasswordResetTokens SET RevokedAt = UTC_TIMESTAMP()
            WHERE UserID = %s AND UsedAt IS NULL AND RevokedAt IS NULL;
            """,
            (user_id,),
        )
        logger.error(
            "Welcome email FAILED - admin_user_id=%s new_user_id=%s error=%s",
            admin_user_id, user_id, type(error).__name__,
        )
        return account, "warning", (
            f'Employee "{data["username"]}" was created, but the set-password email could not be '
            'delivered. Check the mail settings, then use "Send reset link" for this employee.'
        )

    return account, "success", (
        f'Employee "{data["username"]}" was created. A link to set their password was emailed to '
        f'{data["email"]} (valid for {Config.PASSWORD_RESET_TOKEN_MINUTES} minutes).'
    )
