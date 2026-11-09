"""
=========================================================
Project : Sridevi Enterprises
File    : invoice_number_service.py
Purpose : Admin Invoice Number Configuration - allocation of
          customer-visible invoice numbers and the Admin-only "next invoice
          number" setting.

          Rules this module enforces (see AI_CONTEXT.md "Admin Invoice
          Number Configuration"):
            * Invoices.InvoiceID stays the internal primary key; the number
              printed on an invoice is Invoices.InvoiceNumber (UNIQUE).
            * Numbers come from the single InvoiceNumberSequence row, locked
              with SELECT ... FOR UPDATE inside the caller's invoice
              transaction - concurrent invoices queue on that row, and a
              rolled-back invoice also rolls back its number.
            * An Admin may only move the next number UP: it must be greater
              than both the current next number and the highest number ever
              issued, and within 1..99,999,999. Existing invoices are never
              touched. Every change is audited (InvoiceNumberAudit, UTC).
            * Changing it requires an explicit confirmation and the Admin's
              own password (rate limited via AuthThrottle).

Author  : Srikar
=========================================================
"""

import logging
from typing import Any

from werkzeug.security import check_password_hash

from database.db import fetch_all, fetch_one, transaction
from services import password_service

logger = logging.getLogger(__name__)

MIN_INVOICE_NUMBER = 1
MAX_INVOICE_NUMBER = 99_999_999

REAUTH_ACTION = "invoice_number_reauth"

_SEQUENCE_MISSING = (
    "Invoice numbering is not set up on this server (InvoiceNumberSequence is missing). "
    "Contact your administrator."
)


def allocate_invoice_number(cursor) -> int:
    """
    Reserve the next invoice number using the caller's open transaction.

    Must be called inside the same transaction that inserts the invoice:
    the sequence row stays locked until that transaction commits or rolls
    back, so two invoices can never receive the same number and a failed
    invoice gives its number back.

    Raises ValueError (user-facing) if the sequence is missing or exhausted.
    """

    cursor.execute("SELECT NextNumber FROM InvoiceNumberSequence WHERE SequenceID = 1 FOR UPDATE;")
    row = cursor.fetchone()
    if row is None:
        raise ValueError(_SEQUENCE_MISSING)

    number = int(row[0])
    if number > MAX_INVOICE_NUMBER:
        raise ValueError(
            f"Invoice numbers are exhausted (maximum {MAX_INVOICE_NUMBER:,}). Contact your administrator."
        )

    cursor.execute(
        "UPDATE InvoiceNumberSequence SET NextNumber = %s, UpdatedAt = UTC_TIMESTAMP() WHERE SequenceID = 1;",
        (number + 1,),
    )
    return number


def get_numbering_status() -> dict[str, Any]:
    """Current highest issued number, next number and invoice count for the Admin page."""

    issued = fetch_one("SELECT MAX(InvoiceNumber) AS highest, COUNT(*) AS total FROM Invoices;")
    sequence = fetch_one("SELECT NextNumber, UpdatedAt FROM InvoiceNumberSequence WHERE SequenceID = 1;")
    return {
        "highest_issued": int(issued["highest"]) if issued and issued["highest"] is not None else None,
        "invoice_count": int(issued["total"]) if issued else 0,
        "next_number": int(sequence["NextNumber"]) if sequence else None,
        "updated_at": sequence["UpdatedAt"] if sequence else None,
        "max_number": MAX_INVOICE_NUMBER,
    }


def get_recent_changes(limit: int = 10) -> list[dict[str, Any]]:
    """Most recent audit rows (newest first) for the Admin page."""

    return fetch_all("""
        SELECT InvoiceNumberAudit.*, Users.Username AS AdminUsername
        FROM InvoiceNumberAudit
        LEFT JOIN Users ON Users.UserID = InvoiceNumberAudit.AdminUserID
        ORDER BY InvoiceNumberAudit.AuditID DESC
        LIMIT %s;
    """, (limit,))


def parse_next_number(raw: str | None) -> tuple[int | None, str | None]:
    """Parse the submitted value: a plain whole number within range, or a user-facing error."""

    value = (raw or "").strip().replace(",", "")
    if not value:
        return None, "Enter the next invoice number."
    if not value.isdigit() or not value.isascii():
        return None, "The invoice number must be a whole number (digits only, no signs or decimals)."
    number = int(value)
    if number < MIN_INVOICE_NUMBER:
        return None, "The invoice number must be greater than 0."
    if number > MAX_INVOICE_NUMBER:
        return None, f"The invoice number cannot be greater than {MAX_INVOICE_NUMBER:,}."
    return number, None


def set_next_number(
    admin_user_id: int,
    raw_value: str | None,
    password: str | None,
    confirmed: bool,
) -> tuple[bool, str, dict[str, str]]:
    """
    Change InvoiceNumberSequence.NextNumber (Admin only - the route checks
    the role; this re-checks it against the database).

    Returns (success, message, field_errors). Nothing is written unless
    every check passes; on success one InvoiceNumberAudit row is written in
    the same transaction as the change.
    """

    errors: dict[str, str] = {}

    new_number, number_error = parse_next_number(raw_value)
    if number_error:
        errors["next_number"] = number_error
    if not confirmed:
        errors["confirm"] = "Tick the confirmation box to change the invoice number."
    if not password:
        errors["password"] = "Enter your password to confirm this change."
    if errors:
        return False, "Please correct the errors below.", errors

    subject = str(admin_user_id)
    if password_service.is_rate_limited(REAUTH_ACTION, subject):
        return False, "Too many incorrect password attempts. Please wait 15 minutes and try again.", {}

    admin = fetch_one("SELECT Password, Role FROM Users WHERE UserID = %s;", (admin_user_id,))
    if admin is None or admin["Role"] != "Admin":
        return False, "Only an Admin can change invoice numbering.", {}
    if not check_password_hash(admin["Password"], password):
        password_service.record_attempt(REAUTH_ACTION, subject)
        logger.warning("Invoice number change REFUSED (wrong password) - admin_user_id=%s", admin_user_id)
        return False, "Please correct the errors below.", {"password": "Incorrect password."}
    password_service.clear_attempts(REAUTH_ACTION, subject)

    with transaction() as conn:
        cursor = conn.cursor()
        try:
            # Same lock create_invoice() takes, so no invoice can be issued
            # between reading the highest number and moving the sequence.
            cursor.execute("SELECT NextNumber FROM InvoiceNumberSequence WHERE SequenceID = 1 FOR UPDATE;")
            row = cursor.fetchone()
            if row is None:
                return False, _SEQUENCE_MISSING, {}
            old_next = int(row[0])

            # Locking read: always sees the latest committed invoices,
            # whatever snapshot the transaction might otherwise use.
            cursor.execute("SELECT MAX(InvoiceNumber) FROM Invoices LOCK IN SHARE MODE;")
            highest = cursor.fetchone()[0]
            highest = int(highest) if highest is not None else 0

            if new_number == old_next:
                return False, "Please correct the errors below.", {
                    "next_number": f"The next invoice number is already {old_next:05d} - no change was made.",
                }
            if new_number <= highest:
                return False, "Please correct the errors below.", {
                    "next_number": (
                        f"{new_number:05d} has already been issued or is below the highest issued number "
                        f"({highest:05d}). Invoice numbers can never be reused."
                    ),
                }
            if new_number < old_next:
                return False, "Please correct the errors below.", {
                    "next_number": (
                        f"The next invoice number can only be increased (currently {old_next:05d}). "
                        "Lowering it is not allowed."
                    ),
                }

            cursor.execute(
                "UPDATE InvoiceNumberSequence SET NextNumber = %s, UpdatedAt = UTC_TIMESTAMP() WHERE SequenceID = 1;",
                (new_number,),
            )
            cursor.execute("""
                INSERT INTO InvoiceNumberAudit (AdminUserID, OldNextNumber, NewNextNumber, HighestIssued, ChangedAt)
                VALUES (%s, %s, %s, %s, UTC_TIMESTAMP());
            """, (admin_user_id, old_next, new_number, highest))
        finally:
            cursor.close()

    logger.warning(
        "Invoice number sequence CHANGED - admin_user_id=%s old_next=%s new_next=%s highest_issued=%s",
        admin_user_id, old_next, new_number, highest,
    )
    return True, f"The next invoice will be numbered {new_number:05d}.", {}
