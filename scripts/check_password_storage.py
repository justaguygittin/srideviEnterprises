"""
=========================================================
Project : Sridevi Enterprises
File    : check_password_storage.py
Purpose : READ-ONLY check of how Users.Password values are stored, and
          whether every Employee/Admin account has a unique registered
          email (needed for password-reset links).

          Prints COUNTS ONLY - never a password, hash, username or email.
          Writes nothing. Safe to run on the production server.

Usage   : python scripts/check_password_storage.py
Author  : Srikar
=========================================================
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import fetch_one  # noqa: E402


def main() -> None:
    storage = fetch_one(
        """
        SELECT
            COUNT(*) AS total,
            SUM(Password LIKE 'scrypt:%%' OR Password LIKE 'pbkdf2:%%') AS hashed
        FROM Users;
        """
    )
    total = int(storage["total"] or 0)
    hashed = int(storage["hashed"] or 0)

    emails = fetch_one(
        """
        SELECT
            SUM(e.EmployeeID IS NULL) AS no_employee_record,
            SUM(e.EmployeeID IS NOT NULL AND (e.Email IS NULL OR TRIM(e.Email) = '')) AS missing_email
        FROM Users u
        LEFT JOIN Employees e ON e.UserID = u.UserID
        WHERE u.Role IN ('Employee', 'Admin');
        """
    )
    shared = fetch_one(
        """
        SELECT COUNT(*) AS shared_addresses FROM (
            SELECT LOWER(TRIM(e.Email)) AS address
            FROM Employees e JOIN Users u ON u.UserID = e.UserID
            WHERE u.Role IN ('Employee', 'Admin') AND TRIM(COALESCE(e.Email, '')) <> ''
            GROUP BY LOWER(TRIM(e.Email)) HAVING COUNT(*) > 1
        ) duplicates;
        """
    )

    print(f"Accounts:                         {total}")
    print(f"  stored as Werkzeug hashes:      {hashed}")
    print(f"  NOT hashed (cannot log in):     {total - hashed}")
    print(f"Accounts without employee record: {int(emails['no_employee_record'] or 0)}")
    print(f"Accounts with no email:           {int(emails['missing_email'] or 0)}")
    print(f"Email addresses shared by >1 acct:{int(shared['shared_addresses'] or 0):>2}")

    if total - hashed:
        print("\nSome passwords are not hashed. Those accounts cannot log in with the current code. "
              "Do NOT bulk-convert without approval - see AI_CONTEXT.md 'Password Management'.")


if __name__ == "__main__":
    main()
