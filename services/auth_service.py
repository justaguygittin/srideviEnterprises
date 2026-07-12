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


def authenticate_employee(username, password):
    """
    Authenticate an employee by username and plaintext password.

    Args:
        username (str): Employee username
        password (str): Employee plaintext password

    Returns:
        dict: User data if authentication successful, None otherwise
    """

    if not username or not password:
        return None

    query = (
        "SELECT UserID, Username, Role FROM Users WHERE Username = %s AND Password = %s"
    )
    user = fetch_one(query, (username, password))

    return user
