"""
=========================================================
Project : Sridevi Enterprises
File    : enquiry_service.py
Purpose : Customer product enquiry validation and persistence.

Author  : Srikar
=========================================================
"""

import re
from typing import Any

import mysql.connector

from database.db import execute, fetch_all, fetch_one


_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_MOBILE_PATTERN = re.compile(r"^[6-9]\d{9}$")
_MINIMUM_MESSAGE_LENGTH = 10


def get_enquiry_product(product_id: int):
    """Return the product summary required by the customer enquiry form."""

    try:
        return fetch_one("""
            SELECT id, product_name, NULLIF(TRIM(brand), '') AS brand
            FROM Catalog
            WHERE id = %s;
        """, (product_id,))
    except mysql.connector.Error:
        return None


def validate_enquiry(
    form_data: dict[str, str], require_subject: bool = False
) -> tuple[dict[str, str], dict[str, str]]:
    """Validate and normalize product or general customer enquiry fields."""

    cleaned_data = {
        "customer_name": form_data.get("customer_name", "").strip(),
        "phone": _normalise_phone(form_data.get("phone", "")),
        "email": form_data.get("email", "").strip(),
        "subject": form_data.get("subject", "").strip(),
        "message": form_data.get("message", "").strip(),
    }
    errors: dict[str, str] = {}

    if not cleaned_data["customer_name"]:
        errors["customer_name"] = "Please enter your name."
    elif len(cleaned_data["customer_name"]) > 100:
        errors["customer_name"] = "Name must be 100 characters or fewer."

    if not _MOBILE_PATTERN.fullmatch(cleaned_data["phone"]):
        errors["phone"] = "Enter a valid 10-digit Indian mobile number."

    if not _EMAIL_PATTERN.fullmatch(cleaned_data["email"]):
        errors["email"] = "Enter a valid email address."

    if require_subject and not cleaned_data["subject"]:
        errors["subject"] = "Please enter a subject."
    elif len(cleaned_data["subject"]) > 150:
        errors["subject"] = "Subject must be 150 characters or fewer."

    if len(cleaned_data["message"]) < _MINIMUM_MESSAGE_LENGTH:
        errors["message"] = f"Message must contain at least {_MINIMUM_MESSAGE_LENGTH} characters."

    return cleaned_data, errors


def create_enquiry(product_id: int | None, enquiry: dict[str, str]) -> tuple[bool, str | None]:
    """Save a validated enquiry and return a safe customer-facing failure message."""

    if product_id is not None and get_enquiry_product(product_id) is None:
        return False, "This product is no longer available."

    message = enquiry["message"]
    if enquiry.get("subject"):
        message = f"Subject: {enquiry['subject']}\n\n{message}"

    try:
        execute("""
            INSERT INTO Enquiries (ProductID, CustomerName, Phone, Email, Message, Status)
            VALUES (%s, %s, %s, %s, %s, 'Pending');
        """, (
            product_id,
            enquiry["customer_name"],
            enquiry["phone"],
            enquiry["email"],
            message,
        ))
    except mysql.connector.Error:
        return False, "We could not submit your enquiry right now. Please try again shortly."

    # TODO: Integrate email notification for new customer enquiries.
    return True, None


def get_enquiries(filters: dict[str, Any], page: int, per_page: int):
    """Return one paginated page of enquiries matching the supplied filters, newest first."""

    where_clause, params = _build_enquiry_filters(filters)
    return fetch_all(f"""
        SELECT
            e.EnquiryID, e.CustomerName, e.Phone, e.Email, e.Message,
            e.Status, e.EnquiryDate, e.ProductID, c.product_name AS ProductName
        FROM Enquiries e
        LEFT JOIN Catalog c ON c.id = e.ProductID
        WHERE {where_clause}
        ORDER BY e.EnquiryDate DESC
        LIMIT %s OFFSET %s;
    """, tuple(params + [per_page, (page - 1) * per_page]))


def get_enquiry_count(filters: dict[str, Any]) -> int:
    """Return the number of enquiries matching the supplied filters."""

    where_clause, params = _build_enquiry_filters(filters)
    result = fetch_one(f"""
        SELECT COUNT(*) AS total
        FROM Enquiries e
        LEFT JOIN Catalog c ON c.id = e.ProductID
        WHERE {where_clause};
    """, tuple(params))
    return result["total"]


def _build_enquiry_filters(filters: dict[str, Any]) -> tuple[str, list[Any]]:
    """Build the reusable SQL WHERE clause for enquiry listing and count queries."""

    where_clauses = ["1=1"]
    params: list[Any] = []

    search = filters.get("search", "").strip()
    if search:
        like_value = f"%{search}%"
        where_clauses.append("""(
            e.CustomerName LIKE %s OR e.Email LIKE %s OR e.Phone LIKE %s OR c.product_name LIKE %s
        )""")
        params.extend([like_value] * 4)

    return " AND ".join(where_clauses), params


def _normalise_phone(phone: str) -> str:
    """Normalize optional Indian country prefixes before mobile validation."""

    normalized_phone = re.sub(r"[\s-]", "", phone)
    if normalized_phone.startswith("+91"):
        return normalized_phone[3:]
    if normalized_phone.startswith("91") and len(normalized_phone) == 12:
        return normalized_phone[2:]
    return normalized_phone
