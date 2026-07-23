"""
=========================================================
Project : Sridevi Enterprises
File    : auth_service.py
Purpose : Authentication service for employee login.

Author  : Srikar
=========================================================
"""

from database.db import fetch_one
from typing import Any
from werkzeug.security import check_password_hash


def authenticate_employee(
    username: str,
    password: str,
) -> dict[str, Any] | None:
    """
    Authenticate an employee by username and password against the stored hash.

    Args:
        username (str): Employee username
        password (str): Employee plaintext password, as submitted

    Returns:
        dict: User data (including job Designation, for display only) if
        authentication successful, None otherwise
    """

    if not username or not password:
        return None

    query = """
        SELECT Users.UserID, Users.Username, Users.Password, Users.Role, Employees.Designation
        FROM Users
        LEFT JOIN Employees ON Employees.UserID = Users.UserID
        WHERE Users.Username = %s
    """
    user = fetch_one(query, (username,))

    if user is None or not check_password_hash(user["Password"], password):
        return None

    del user["Password"]
    return user
