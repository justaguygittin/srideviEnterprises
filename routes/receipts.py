"""
=========================================================
Project : Sridevi Enterprises
File    : receipts.py
Purpose : Invoice Generator module routes - Buyer/Consignee/Product entry,
          GST calculation, PDF generation, and invoice history for
          employees.

          Replaces the Employee Portal's former external-launch bridge to
          the standalone Receipt Generator project (see AI_CONTEXT.md
          "Invoice Generator Module (Merge)"): this module now generates
          invoices itself, inside this application, using the existing
          employee session/auth and the existing Catalog table - it does
          not launch or link to anything external any more.

Author  : Srikar
=========================================================
"""

import logging

from flask import Blueprint, Response, abort, flash, jsonify, redirect, render_template, request, session, url_for

from routes.employee import EMPLOYEE_PORTAL_ROLES, _paginate
from services import gst_service
from services.auth_service import get_employee_id_for_user
from services.invoice_service import create_invoice, get_invoice, get_invoice_count, get_invoices, validate_invoice_form
from services.pdf_service import PDFGenerationError, render_invoice_pdf
from services.product_service import get_active_product_names, get_product_variants

logger = logging.getLogger(__name__)

receipts_bp = Blueprint("receipts", __name__)


@receipts_bp.route("/employee/invoices", methods=["GET"])
def history():
    """Display the paginated Invoice History page for employees."""

    if not session.get("UserID"):
        return redirect(url_for("employee.login"))
    if session.get("Role") not in EMPLOYEE_PORTAL_ROLES:
        abort(403)

    page = request.args.get("page", 1, type=int)
    search = request.args.get("search", "").strip()
    filters = {"search": search}

    per_page = 20
    total_invoices = get_invoice_count(filters)
    page, total_pages, start_page, end_page = _paginate(page, total_invoices, per_page)

    return render_template(
        "employee/invoice_history.html",
        username=session.get("Username"),
        role=session.get("Role"),
        current_page="invoices",
        invoices=get_invoices(filters, page, per_page),
        search=search,
        total_invoices=total_invoices,
        total_pages=total_pages,
        page=page,
        start_page=start_page,
        end_page=end_page,
    )


@receipts_bp.route("/employee/invoices/new", methods=["GET", "POST"])
def new_invoice():
    """
    Display and handle the New Invoice form for Employee and Admin roles.

    Error codes shown on failure (INV-01/INV-02/INV-99) are documented in
    ERROR_CODES.md (INV-xx section) - add a row there for any new one.
    """

    if not session.get("UserID"):
        return redirect(url_for("employee.login"))
    if session.get("Role") not in EMPLOYEE_PORTAL_ROLES:
        abort(403)

    errors: dict = {}

    if request.method == "POST":
        cleaned, errors = validate_invoice_form(request.form)
        employee_id = None

        if not errors:
            employee_id = get_employee_id_for_user(session["UserID"])
            if employee_id is None:
                errors["form"] = (
                    "(Error INV-01) Your account is not linked to an employee record, so this "
                    "invoice cannot be recorded. Contact your administrator."
                )

        if not errors:
            try:
                invoice_id, invoice_number = create_invoice(cleaned, employee_id)
            except ValueError as error:
                # Deliberate flow control, not a fault: create_invoice() raises
                # ValueError with a user-facing message for expected refusals
                # (missing SELLER_GSTIN, a product deactivated since the form
                # was loaded) - mirrors apply_stock_transaction()'s convention.
                # The message itself already names the specific reason; the
                # INV-02 code just labels this as "expected refusal" so it's
                # easy to tell apart from an INV-99 crash when reported.
                logger.info(
                    "Invoice creation REFUSED [INV-02] - user=%s reason=%s", session.get("Username"), error
                )
                errors["form"] = f"(Error INV-02) {error}"
            except Exception:
                logger.exception("Invoice creation FAILED [INV-99, unexpected] - user=%s", session.get("Username"))
                errors["form"] = "(Error INV-99) Could not generate this invoice. Please try again."
            else:
                flash(f"Invoice #{invoice_number:05d} generated successfully.", "success")
                return redirect(url_for("receipts.view_invoice", invoice_id=invoice_id))

    return render_template(
        "employee/invoice_form.html",
        username=session.get("Username"),
        role=session.get("Role"),
        current_page="invoices",
        errors=errors,
        products=get_active_product_names(),
        states=gst_service.STATE_NAMES,
    )


@receipts_bp.route("/employee/invoices/models/<product_name>", methods=["GET"])
def product_models(product_name):
    """
    JSON lookup of a product's active model variants (id/model/brand/price/
    GST%) for the New Invoice form's model dropdown - mirrors the
    standalone Receipt Generator's original /get_models/<product_name>.
    """

    if not session.get("UserID"):
        return redirect(url_for("employee.login"))
    if session.get("Role") not in EMPLOYEE_PORTAL_ROLES:
        abort(403)

    return jsonify(get_product_variants(product_name))


@receipts_bp.route("/employee/invoices/<int:invoice_id>", methods=["GET"])
def view_invoice(invoice_id):
    """Display one generated invoice's details, with a link to its PDF."""

    if not session.get("UserID"):
        return redirect(url_for("employee.login"))
    if session.get("Role") not in EMPLOYEE_PORTAL_ROLES:
        abort(403)

    invoice = get_invoice(invoice_id)
    if invoice is None:
        abort(404)

    return render_template(
        "employee/invoice_view.html",
        username=session.get("Username"),
        role=session.get("Role"),
        current_page="invoices",
        invoice=invoice,
        tax_type=gst_service.determine_tax_type(invoice["SellerState"], invoice["BuyerState"]),
        buyer_state_name=gst_service.state_name(invoice["BuyerState"]),
    )


@receipts_bp.route("/employee/invoices/<int:invoice_id>/pdf", methods=["GET"])
def invoice_pdf(invoice_id):
    """
    Regenerate and stream one invoice's PDF from its stored (snapshotted)
    data - see services/pdf_service.py. The PDF itself is never stored;
    every request re-renders it from Invoices/InvoiceItems, which is cheap
    and guarantees a reprint always matches what's in the database.

    Error codes shown on failure (PDF-xx) are documented in
    ERROR_CODES.md.
    """

    if not session.get("UserID"):
        return redirect(url_for("employee.login"))
    if session.get("Role") not in EMPLOYEE_PORTAL_ROLES:
        abort(403)

    invoice = get_invoice(invoice_id)
    if invoice is None:
        abort(404)

    try:
        pdf_bytes = render_invoice_pdf(invoice)
    except PDFGenerationError as error:
        logger.exception(
            "Invoice PDF generation FAILED [%s] - invoice_id=%s user=%s",
            error.code, invoice_id, session.get("Username"),
        )
        flash(f"Could not generate the PDF for this invoice (error {error.code}: {error}).", "danger")
        return redirect(url_for("receipts.view_invoice", invoice_id=invoice_id))
    except Exception:
        logger.exception(
            "Invoice PDF generation FAILED [PDF-99, unexpected] - invoice_id=%s user=%s",
            invoice_id, session.get("Username"),
        )
        flash("Could not generate the PDF for this invoice (error PDF-99). Please try again.", "danger")
        return redirect(url_for("receipts.view_invoice", invoice_id=invoice_id))

    response = Response(pdf_bytes, mimetype="application/pdf")
    response.headers["Content-Disposition"] = f'inline; filename="Invoice_{invoice["InvoiceNumber"]:05d}.pdf"'
    return response
