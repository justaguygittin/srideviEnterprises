"""
=========================================================
Project : Sridevi Enterprises
File    : migrate_password_hashes.py
Purpose : One-time migration converting plaintext Users.Password values
          to Werkzeug password hashes.

          Safe to re-run: rows whose Password already looks hashed
          (starts with a known Werkzeug method prefix) are left untouched.

Usage   : python scripts/migrate_password_hashes.py

Author  : Srikar
=========================================================
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import execute, fetch_all
from werkzeug.security import generate_password_hash

_HASHED_PREFIXES = ("scrypt:", "pbkdf2:")


def _looks_hashed(password: str) -> bool:
    return password.startswith(_HASHED_PREFIXES)


def migrate_password_hashes() -> None:
    users = fetch_all("SELECT UserID, Username, Password FROM Users;")

    migrated = 0
    skipped = 0

    for user in users:
        if _looks_hashed(user["Password"]):
            skipped += 1
            continue

        hashed_password = generate_password_hash(user["Password"])
        execute("UPDATE Users SET Password = %s WHERE UserID = %s;", (hashed_password, user["UserID"]))
        migrated += 1
        print(f"Migrated: {user['Username']} (UserID {user['UserID']})")

    print(f"\nDone. Migrated {migrated} user(s), skipped {skipped} already-hashed user(s).")


if __name__ == "__main__":
    migrate_password_hashes()
