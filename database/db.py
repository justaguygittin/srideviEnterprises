"""
=========================================================
Project : Sridevi Enterprises
File    : db.py
Purpose : Database helper functions.

Author  : Srikar
=========================================================
"""

from contextlib import contextmanager

import mysql.connector
from config import Config
from typing import Any, cast


def get_connection():
    """
    Create and return a database connection.
    """

    return mysql.connector.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
        charset="utf8mb4",
        collation="utf8mb4_unicode_ci",
    )


def fetch_all(query: str, params=None) -> list[dict[str, Any]]:
    """
    Execute a SELECT query and return all rows.
    """

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(query, params or ())

    rows = cast(list[dict[str, Any]], cursor.fetchall())

    cursor.close()
    conn.close()

    return rows


def fetch_one(query: str, params=None) -> dict[str, Any] | None:
    """
    Execute a SELECT query and return one row.
    """

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(query, params or ())

    row = cast(dict[str, Any] | None, cursor.fetchone())

    cursor.close()
    conn.close()

    return row


def execute(query, params=None):
    """
    Execute INSERT, UPDATE or DELETE queries.
    """

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(query, params or ())

    conn.commit()

    cursor.close()
    conn.close()


@contextmanager
def transaction():
    """
    Yield a connection for multi-statement atomic writes.

    Commits on success, rolls back on any exception raised inside the
    `with` block, and always closes the connection. Callers create their
    own cursor(s) from the yielded connection.
    """

    conn = get_connection()

    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
