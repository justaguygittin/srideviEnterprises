"""
=========================================================
Project : Sridevi Enterprises
File    : auth_service.py
Purpose : Authentication service for employee login.

Author  : Srikar
=========================================================
"""

from database.db import fetch_all, fetch_one
from typing import Any
from werkzeug.security import check_password_hash

_ACCOUNT_COLUMNS = """
    SELECT Users.UserID, Users.Username, Users.Password, Users.Role, Users.SessionEpoch,
           Employees.Designation
    FROM Users
    LEFT JOIN Employees ON Employees.UserID = Users.UserID
"""


def find_login_account(identifier: str) -> dict[str, Any] | None:
    """
    Resolve a login identifier - a username OR a registered email address -
    to exactly one account (including its password hash), or None.

    Username is tried first, exactly as before, so every existing login
    keeps working unchanged. Only if no username matches and the identifier
    looks like an email is Employees.Email searched (trimmed,
    case-insensitive). An email shared by more than one account matches
    nothing: logging into "whichever account happened to come first" would
    be a security bug, so those users must log in by username.
    """

    identifier = (identifier or "").strip()
    if not identifier:
        return None

    account = fetch_one(_ACCOUNT_COLUMNS + " WHERE Users.Username = %s LIMIT 1;", (identifier,))
    if account is not None or "@" not in identifier:
        return account

    matches = fetch_all(
        _ACCOUNT_COLUMNS + " WHERE LOWER(TRIM(Employees.Email)) = %s LIMIT 2;",
        (identifier.lower(),),
    )
    return matches[0] if len(matches) == 1 else None


def authenticate_employee(
    identifier: str,
    password: str,
) -> dict[str, Any] | None:
    """
    Authenticate by username or registered email, and password, against the
    stored hash.

    Args:
        identifier (str): Username, or the email address registered in Employees
        password (str): Plaintext password, as submitted

    Returns:
        dict: User data (including job Designation, for display only) if
        authentication successful, None otherwise
    """

    if not identifier or not password:
        return None

    user = find_login_account(identifier)

    if user is None or not check_password_hash(user["Password"], password):
        return None

    del user["Password"]
    return user


def login_throttle_subject(identifier: str) -> str:
    """
    The key failed-login rate limiting is counted against: the resolved
    account when the identifier matches one, so guesses made by username
    and by email share ONE limit; otherwise the identifier as typed.
    """

    account = find_login_account(identifier)
    return f"user:{account['UserID']}" if account else (identifier or "").strip().lower()


def get_employee_id_for_user(user_id: int) -> int | None:
    """
    Return the Employees.EmployeeID linked to a Users.UserID, or None if this
    account has no linked Employees row (v1.0 Sprint 5.1: StockHistory's
    EmployeeID foreign key requires a real Employees row, which is a
    different id than the session's UserID).
    """

    row = fetch_one("SELECT EmployeeID FROM Employees WHERE UserID = %s;", (user_id,))
    return row["EmployeeID"] if row else None
