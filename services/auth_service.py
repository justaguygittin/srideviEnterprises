"""
=========================================================
Project : Sridevi Enterprises
File    : auth_service.py
Purpose : Authentication service for employee login.

Author  : Srikar
# TODO:
# Replace plaintext comparison with password hashing
# before production deployment.
=========================================================
"""

from database.db import fetch_one
from typing import Any


def authenticate_employee(
    username: str,
    password: str,
) -> dict[str, Any] | None:
    """
    Authenticate an employee by username and plaintext password.

    Args:
        username (str): Employee username
        password (str): Employee plaintext password

    Returns:
        dict: User data (including job Designation, for display only) if
        authentication successful, None otherwise
    """

    if not username or not password:
        return None

    query = """
        SELECT Users.UserID, Users.Username, Users.Role, Employees.Designation
        FROM Users
        LEFT JOIN Employees ON Employees.UserID = Users.UserID
        WHERE Users.Username = %s AND Users.Password = %s
    """
    user = fetch_one(query, (username, password))

    return user
