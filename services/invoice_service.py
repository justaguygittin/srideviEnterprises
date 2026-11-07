"""
=========================================================
Project : Sridevi Enterprises
File    : invoice_service.py
Purpose : Invoice Generator module - form validation, GST calculation
          orchestration, and persistence for Invoices/InvoiceItems.
          services/gst_service.py owns the pure tax math; this module owns
          everything that touches the database or a submitted form.

Author  : Srikar
=========================================================
"""

import logging
import re
from decimal import Decimal
from typing import Any

from num2words import num2words

from database.db import fetch_all, fetch_one, transaction
from services import gst_service
from services.product_service import get_catalog_product_for_invoice, parse_price

logger = logging.getLogger(__name__)

_MULTI_SPACE_PATTERN = re.compile(r"\s+")


def _number_to_title_words(n: int) -> str:
    """
    num2words(..., lang='en_IN') as clean title-cased words: no commas, no
    internal hyphens ("Ninety-Six" -> "Ninety Six"), no "And" ("Seven
    Hundred And Four" -> "Seven Hundred Four") - matching how amounts are
    conventionally spelled out on a GST invoice.
    """

    words = num2words(n, lang="en_IN").title().replace("-", " ").replace(",", "")
    words = re.sub(r"\bAnd\b", "", words)
    return _MULTI_SPACE_PATTERN.sub(" ", words).strip()


def amount_to_words(amount: Decimal) -> str:
    """
    Render a rupee amount as "INR <rupees> Rupees and <paise> Paise Only".
    Splits rupees/paise explicitly rather than handing the raw Decimal to
    num2words, which would spell out a decimal point instead of "... and
    N Paise" - see AI_CONTEXT.md "Invoice Generator Module (Merge)" for the
    reference invoice this wording was verified against.
    """

    rupees = int(amount)
    paise = int((amount - rupees) * 100)

    words = "INR " + _number_to_title_words(rupees) + " Rupees"
    if paise:
        words += " and " + _number_to_title_words(paise) + " Paise"
    words += " Only"
    return words


def _clean_party_fields(form: dict, prefix: str, errors: dict) -> dict[str, Any]:
    """Validate and normalise one Buyer/Consignee field group (prefix is 'buyer' or 'consignee')."""

    label = prefix.capitalize()
    data = {
        "name": form.get(f"{prefix}_name", "").strip(),
        "address": form.get(f"{prefix}_address", "").strip(),
        "contact": form.get(f"{prefix}_contact", "").strip(),
        "gstin": form.get(f"{prefix}_gstin", "").strip().upper(),
        "contract": form.get(f"{prefix}_contract", "").strip(),
    }

    if not data["name"]:
        errors[f"{prefix}_name"] = f"{label} name is required."
    elif len(data["name"]) > 255:
        errors[f"{prefix}_name"] = f"{label} name must be 255 characters or fewer."

    if not data["address"]:
        errors[f"{prefix}_address"] = f"{label} address is required."

    # GSTIN is optional (an invoice to an unregistered consumer legitimately
    # has none - see the reference invoice in AI_CONTEXT.md, whose GSTIN
    # line prints blank) - format is checked only when one is supplied.
    if data["gstin"] and not gst_service.is_valid_gstin(data["gstin"]):
        errors[f"{prefix}_gstin"] = f"{label} GSTIN doesn't look like a valid 15-character GSTIN."

    return data


def validate_invoice_form(form) -> tuple[dict[str, Any], dict[str, str]]:
    """
    Validate and normalise the New Invoice form (routes/receipts.py). Pure
    validation only - no database access and no GST calculation happens
    here (see create_invoice() below for both), matching this codebase's
    existing split between field validation and DB-backed checks
    (product_service.validate_product_form / find_duplicate_product).

    Buyer/Place-of-Supply state (`buyer_state`) is its own required field,
    not derived from the Buyer GSTIN's first two digits: GSTIN is optional
    (see _clean_party_fields above), but every invoice still needs a
    determinable place of supply to know whether CGST+SGST or IGST applies,
    including for an unregistered buyer who has no GSTIN at all.
    """

    errors: dict[str, str] = {}
    cleaned: dict[str, Any] = {"buyer": _clean_party_fields(form, "buyer", errors)}

    # "Consignee details same as buyer": the form mirrors the buyer's
    # name/address/contact/GSTIN into read-only consignee fields, but those
    # submitted copies are not trusted - the server re-copies them from the
    # buyer values it just validated, so a disabled/blocked script or an
    # edited read-only field can never produce a mismatched Ship To. The
    # consignee's contract number is not part of the link.
    if form.get("consignee_same_as_buyer"):
        cleaned["consignee"] = {key: cleaned["buyer"][key] for key in ("name", "address", "contact", "gstin")}
        cleaned["consignee"]["contract"] = form.get("consignee_contract", "").strip()
    else:
        cleaned["consignee"] = _clean_party_fields(form, "consignee", errors)

    buyer_state = form.get("buyer_state", "").strip()
    if buyer_state not in gst_service.STATE_NAMES:
        errors["buyer_state"] = "Please select the buyer's state (for place of supply)."
    cleaned["buyer_state"] = buyer_state

    product_ids = form.getlist("product_id[]")
    quantities = form.getlist("qty[]")
    hsn_codes = form.getlist("hsn[]")
    prices = form.getlist("price[]")

    if not product_ids:
        errors["items"] = "Add at least one product."
    elif not (len(product_ids) == len(quantities) == len(hsn_codes) == len(prices)):
        # Previously a mismatched zip() silently truncated to the shortest
        # list instead of rejecting the submission - see AI_CONTEXT.md.
        errors["items"] = "Product rows are inconsistent. Please re-add the product rows and try again."
    else:
        items: list[dict[str, Any]] = []
        rows = zip(product_ids, quantities, hsn_codes, prices)
        for index, (product_id, quantity, hsn, price) in enumerate(rows, start=1):
            if not product_id.isdigit():
                errors["items"] = f"Row {index}: please select a product model."
                break
            if not quantity.isdigit() or int(quantity) <= 0:
                errors["items"] = f"Row {index}: quantity must be a whole number greater than 0."
                break
            hsn = hsn.strip()
            if not hsn:
                errors["items"] = f"Row {index}: HSN code is required."
                break
            # Per-row price: pre-filled from the catalog in the browser but
            # editable for this invoice only, so it is validated here like
            # any other submitted value. Zero stays allowed, as before.
            unit_price, price_error = parse_price(price, allow_zero=True)
            if price_error:
                errors["items"] = f"Row {index}: {price_error}"
                break
            items.append({
                "product_id": int(product_id), "quantity": int(quantity), "hsn": hsn, "unit_price": unit_price,
            })
        else:
            cleaned["items"] = items

    return cleaned, errors


def create_invoice(cleaned: dict[str, Any], employee_id: int) -> int:
    """
    Calculate and persist one invoice: uses each line item's submitted unit
    price (pre-filled from Catalog.offer_price, but overridable per row) and
    the current Catalog GST rate, computes the full tax breakdown
    (services/gst_service.py), then inserts the Invoices row and every
    InvoiceItems row inside one transaction.

    Raises ValueError (nothing is written) if:
      - Config.SELLER_GSTIN is not configured, or
      - any submitted product is missing or has been deactivated since the
        form was loaded (re-checked here, not trusted from the form - the
        same "don't trust an earlier page load" principle
        product_service.apply_stock_transaction() already applies to stock).

    Invoice numbering: InvoiceID is a plain AUTO_INCREMENT, only consumed
    once every validation and Catalog lookup above has already succeeded -
    a failed submission never reserves a number (see
    database/schema/012_create_invoices.sql for the one-time numbering
    -continuity check this relies on against the standalone Receipt
    Generator's own prior invoices).
    """

    seller_gstin = _require_seller_gstin()
    seller_state = seller_gstin[:2]
    buyer_state = cleaned["buyer_state"]
    tax_type = gst_service.determine_tax_type(seller_state, buyer_state)

    line_items: list[dict[str, Any]] = []
    for item in cleaned["items"]:
        catalog_row = get_catalog_product_for_invoice(item["product_id"])
        if catalog_row is None:
            raise ValueError(
                f"Product #{item['product_id']} could not be found or is no longer available. "
                "Please remove it and try again."
            )

        # The employee's (possibly overridden) row price, not the catalog's -
        # the catalog only supplied the default. GST rate still comes from
        # the catalog. Nothing here writes back to Catalog.
        unit_price = item["unit_price"]
        catalog_price = Decimal(str(catalog_row["offer_price"] or 0))
        if unit_price != catalog_price:
            logger.info(
                "Invoice price override - product_id=%s catalog_price=%s invoice_price=%s",
                catalog_row["id"], catalog_price, unit_price,
            )

        calc = gst_service.calculate_line_item(
            item["quantity"], unit_price, catalog_row["gst_percent"] or 0, tax_type
        )
        line_items.append({
            **calc,
            "product_id": catalog_row["id"],
            "product_name": catalog_row["product_name"],
            "model": catalog_row["model"],
            "hsn": item["hsn"],
            "quantity": item["quantity"],
            "unit_price": unit_price,
            "gst_percent": Decimal(str(catalog_row["gst_percent"] or 0)),
        })

    totals = gst_service.calculate_invoice_totals(line_items)
    amount_words = amount_to_words(totals["subtotal"])

    buyer = cleaned["buyer"]
    consignee = cleaned["consignee"]

    with transaction() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO Invoices (
                    BuyerName, BuyerAddress, BuyerContact, BuyerGSTIN, BuyerContract,
                    ConsigneeName, ConsigneeAddress, ConsigneeContact, ConsigneeGSTIN, ConsigneeContract,
                    SellerState, BuyerState,
                    TaxableTotal, CGSTTotal, SGSTTotal, IGSTTotal, RoundOff, GrandTotal, AmountInWords,
                    CreatedBy
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s,
                    %s, %s, %s, %s, %s, %s, %s,
                    %s
                );
            """, (
                buyer["name"], buyer["address"], buyer["contact"] or None, buyer["gstin"] or None, buyer["contract"] or None,
                consignee["name"], consignee["address"], consignee["contact"] or None,
                consignee["gstin"] or None, consignee["contract"] or None,
                seller_state, buyer_state,
                totals["taxable_total"], totals["cgst_total"], totals["sgst_total"],
                totals["igst_total"], totals["round_off"], totals["grand_total"], amount_words,
                employee_id,
            ))
            invoice_id = cursor.lastrowid

            for item in line_items:
                cursor.execute("""
                    INSERT INTO InvoiceItems (
                        InvoiceID, ProductID, ProductName, Model, HSN, Quantity,
                        UnitPrice, GSTPercent, TaxableValue, CGSTAmount, SGSTAmount, IGSTAmount, LineTotal
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                """, (
                    invoice_id, item["product_id"], item["product_name"], item["model"], item["hsn"],
                    item["quantity"], item["unit_price"], item["gst_percent"], item["taxable_value"],
                    item["cgst_amount"], item["sgst_amount"], item["igst_amount"], item["line_total"],
                ))
        finally:
            cursor.close()

    logger.info(
        "Invoice created - invoice_id=%s employee_id=%s buyer=%r items=%d grand_total=%s",
        invoice_id, employee_id, buyer["name"], len(line_items), totals["grand_total"],
    )
    return invoice_id


def _require_seller_gstin() -> str:
    """Raise ValueError with a user-facing message if SELLER_GSTIN isn't configured."""

    from config import Config

    if not Config.SELLER_GSTIN:
        raise ValueError(
            "The seller's GSTIN is not configured (SELLER_GSTIN). "
            "Contact your administrator before generating invoices."
        )
    return Config.SELLER_GSTIN


def get_invoice_count(filters: dict[str, Any]) -> int:
    """Return how many invoices match the History page's search filter."""

    where_clause, params = _build_invoice_filters(filters)
    result = fetch_one(f"SELECT COUNT(*) AS total FROM Invoices WHERE {where_clause};", tuple(params))
    return result["total"]


def get_invoices(filters: dict[str, Any], page: int, per_page: int) -> list[dict[str, Any]]:
    """Return one paginated page of invoices (newest first) for the History page."""

    where_clause, params = _build_invoice_filters(filters)
    return fetch_all(f"""
        SELECT
            Invoices.InvoiceID, Invoices.InvoiceDate, Invoices.BuyerName,
            Invoices.GrandTotal, Employees.Name AS CreatedByName
        FROM Invoices
        LEFT JOIN Employees ON Employees.EmployeeID = Invoices.CreatedBy
        WHERE {where_clause}
        ORDER BY Invoices.InvoiceID DESC
        LIMIT %s OFFSET %s;
    """, tuple(params + [per_page, (page - 1) * per_page]))


def _build_invoice_filters(filters: dict[str, Any]) -> tuple[str, list[Any]]:
    """Shared WHERE clause for the History page's list/count queries."""

    where_clauses = ["1 = 1"]
    params: list[Any] = []

    search = (filters.get("search") or "").strip()
    if search:
        where_clauses.append("(BuyerName LIKE %s OR InvoiceID = %s)")
        like_value = f"%{search}%"
        params.extend([like_value, search if search.isdigit() else -1])

    return " AND ".join(where_clauses), params


def get_invoice(invoice_id: int) -> dict[str, Any] | None:
    """Return one invoice (with its line items) for the View/PDF pages, or None if not found."""

    invoice = fetch_one("""
        SELECT Invoices.*, Employees.Name AS CreatedByName
        FROM Invoices
        LEFT JOIN Employees ON Employees.EmployeeID = Invoices.CreatedBy
        WHERE Invoices.InvoiceID = %s;
    """, (invoice_id,))

    if invoice is None:
        return None

    invoice["items"] = fetch_all("""
        SELECT * FROM InvoiceItems WHERE InvoiceID = %s ORDER BY ItemID;
    """, (invoice_id,))
    return invoice
