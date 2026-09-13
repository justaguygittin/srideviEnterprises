"""
=========================================================
Project : Sridevi Enterprises
File    : gst_service.py
Purpose : GST calculation for the Invoice Generator module - pure functions
          only (no database, no Flask). Kept separate from
          invoice_service.py (which owns validation/persistence) so the tax
          math can be read, and unit tested, without a request or a
          database connection in the picture.

Author  : Srikar
=========================================================
"""

import re
from decimal import ROUND_HALF_UP, Decimal

from config import Config

# Every monetary value in this module is a Decimal, never a float - GST
# invoices are legal/financial documents, and float's binary rounding
# (0.1 + 0.2 != 0.3) is not an acceptable source of error on one. Every
# Decimal is quantized with ROUND_HALF_UP, matching how paise are rounded
# on a printed invoice (never Python's own default round-half-to-even).
TWO_PLACES = Decimal("0.01")

_GSTIN_PATTERN = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$")

# Standard GST state codes -> state name, for the invoice's "Place of
# Supply" line. Fixed, not user-configurable - these codes are set by the
# GST Council, not by this application.
STATE_NAMES = {
    "01": "Jammu and Kashmir", "02": "Himachal Pradesh", "03": "Punjab",
    "04": "Chandigarh", "05": "Uttarakhand", "06": "Haryana", "07": "Delhi",
    "08": "Rajasthan", "09": "Uttar Pradesh", "10": "Bihar", "11": "Sikkim",
    "12": "Arunachal Pradesh", "13": "Nagaland", "14": "Manipur", "15": "Mizoram",
    "16": "Tripura", "17": "Meghalaya", "18": "Assam", "19": "West Bengal",
    "20": "Jharkhand", "21": "Odisha", "22": "Chhattisgarh", "23": "Madhya Pradesh",
    "24": "Gujarat", "25": "Daman and Diu", "26": "Dadra and Nagar Haveli",
    "27": "Maharashtra", "28": "Andhra Pradesh", "29": "Karnataka", "30": "Goa",
    "31": "Lakshadweep", "32": "Kerala", "33": "Tamil Nadu", "34": "Puducherry",
    "35": "Andaman and Nicobar Islands", "36": "Telangana", "37": "Andhra Pradesh",
    "38": "Ladakh", "97": "Other Territory",
}


def quantize(amount) -> Decimal:
    """Round any numeric value to 2 decimal places, ROUND_HALF_UP."""

    return Decimal(str(amount)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def state_name(state_code: str) -> str:
    """Return the display name for a 2-digit GST state code, or '' if unknown."""

    return STATE_NAMES.get(state_code, "")


def is_valid_gstin(gstin: str) -> bool:
    """
    Validate a GSTIN's format (15 characters: 2-digit state code, 10-character
    PAN, 1-digit entity code, literal 'Z', 1 checksum character).

    Format only - this does not verify the GSTIN is real or registered
    (that would require calling the GST Network's API, out of scope here).
    An invoice's Buyer/Consignee GSTIN is optional (an invoice to an
    unregistered consumer legitimately has none); call this only when a
    GSTIN was actually supplied.
    """

    return bool(_GSTIN_PATTERN.match((gstin or "").strip().upper()))


def determine_tax_type(seller_state: str, buyer_state: str) -> str:
    """Return 'CGST_SGST' for an intra-state sale, 'IGST' for inter-state."""

    return "CGST_SGST" if seller_state == buyer_state else "IGST"


def calculate_line_item(quantity: int, unit_price, gst_percent, tax_type: str) -> dict:
    """
    Calculate one invoice line's tax breakdown from an INCLUSIVE unit price
    (the Catalog offer_price already includes GST - matches the Invoice
    Generator's existing, preserved behaviour).

    Returns a dict of Decimals: line_total (qty * unit_price, the inclusive
    amount actually charged), taxable_value, cgst_amount, sgst_amount,
    igst_amount. Exactly one of (cgst_amount, sgst_amount) or (igst_amount)
    is non-zero, per tax_type.
    """

    unit_price = Decimal(str(unit_price))
    gst_percent = Decimal(str(gst_percent))
    line_total = quantize(unit_price * quantity)

    taxable_value = quantize(line_total * 100 / (100 + gst_percent))
    total_gst = quantize(line_total - taxable_value)

    if tax_type == "CGST_SGST":
        cgst_amount = quantize(total_gst / 2)
        sgst_amount = total_gst - cgst_amount  # remainder, so the two halves always sum to total_gst exactly
        igst_amount = Decimal("0.00")
    else:
        cgst_amount = Decimal("0.00")
        sgst_amount = Decimal("0.00")
        igst_amount = total_gst

    return {
        "line_total": line_total,
        "taxable_value": taxable_value,
        "cgst_amount": cgst_amount,
        "sgst_amount": sgst_amount,
        "igst_amount": igst_amount,
    }


def calculate_invoice_totals(line_items: list[dict]) -> dict:
    """
    Sum a list of calculate_line_item() results into invoice-level totals,
    plus the reconciling Round Off and the words-ready subtotal.

    "Amount Chargeable in Words" (see invoice_service.amount_to_words)
    describes `subtotal` - the sum of the already-2dp-rounded Taxable/CGST/
    SGST/IGST totals below, exactly as printed - not the raw grand_total.
    Rounding each total independently before summing can leave a paisa or
    two of drift against the true line-total sum; `round_off` is what
    reconciles the printed subtotal back to the actual payable
    `grand_total`, matching standard GST invoice practice (and matching a
    real reference invoice's own numbers - see AI_CONTEXT.md).
    """

    taxable_total = quantize(sum((item["taxable_value"] for item in line_items), Decimal("0")))
    cgst_total = quantize(sum((item["cgst_amount"] for item in line_items), Decimal("0")))
    sgst_total = quantize(sum((item["sgst_amount"] for item in line_items), Decimal("0")))
    igst_total = quantize(sum((item["igst_amount"] for item in line_items), Decimal("0")))
    total_tax = quantize(cgst_total + sgst_total + igst_total)

    subtotal = quantize(taxable_total + total_tax)

    grand_total = quantize(sum((item["line_total"] for item in line_items), Decimal("0")))
    round_off = quantize(grand_total - subtotal)

    return {
        "taxable_total": taxable_total,
        "cgst_total": cgst_total,
        "sgst_total": sgst_total,
        "igst_total": igst_total,
        "total_tax": total_tax,
        "subtotal": subtotal,
        "round_off": round_off,
        "grand_total": grand_total,
    }


def get_seller_state() -> str:
    """Return the seller's 2-digit GST state code, derived from Config.SELLER_GSTIN."""

    return Config.SELLER_GSTIN[:2] if Config.SELLER_GSTIN else ""
