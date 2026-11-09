"""
=========================================================
Project : Sridevi Enterprises
File    : admin.py
Purpose : Admin routes.

          Password Management cycle: a minimal Employees page listing
          Employee/Admin accounts with their registered email status, an
          Admin-only "Send reset link" action, and "Add Employee". Admins
          never see, set, or retrieve any password, and never see the
          reset/set-password link itself.

          Invoice Number Settings (/admin/invoice-numbering): Admin-only
          control of the next customer-visible invoice number.

Author  : Srikar
=========================================================
"""

import logging
from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

from config import Config
from services import email_service, invoice_number_service, password_service
from services.employee_account_service import create_employee_account, validate_new_employee_form
from services.csrf_service import csrf_protect

logger = logging.getLogger(__name__)

admin_bp = Blueprint("admin", __name__)


def _require_admin():
    """Return a redirect for anonymous users, abort 403 for non-Admins, else None."""

    if not session.get("UserID"):
        return redirect(url_for("employee.login"))
    if session.get("Role") != "Admin":
        abort(403)
    return None


@admin_bp.route("/admin/employees", methods=["GET"])
def employees():
    """List Employee/Admin accounts with a Reset Password action (Admin only)."""

    denied = _require_admin()
    if denied:
        return denied

    return render_template(
        "admin/employees.html",
        username=session.get("Username"),
        role=session.get("Role"),
        current_page="employees",
        accounts=password_service.get_accounts_for_admin(),
        email_issue_messages=password_service.EMAIL_ISSUE_MESSAGES,
        email_available=email_service.is_email_configured(),
        current_user_id=session.get("UserID"),
        token_minutes=Config.PASSWORD_RESET_TOKEN_MINUTES,
    )


@admin_bp.route("/admin/employees/add", methods=["GET", "POST"])
@csrf_protect
def add_employee():
    """
    Add Employee (Admin only). Creates an Employee-role account and emails
    the new employee a single-use link to choose their own password - the
    Admin never sets or sees one.
    """

    denied = _require_admin()
    if denied:
        return denied

    form_data: dict = {}
    errors: dict = {}
    email_available = email_service.is_email_configured()

    if request.method == "POST":
        form_data, errors = validate_new_employee_form(request.form)
        if not errors:
            account, category, message = create_employee_account(
                session["UserID"],
                form_data,
                lambda raw_token: url_for("employee.reset_password_link", token=raw_token),
            )
            if account is not None:
                flash(message, category)
                return redirect(url_for("admin.employees"))
            errors["form"] = message

    return render_template(
        "admin/employee_form.html",
        username=session.get("Username"),
        role=session.get("Role"),
        current_page="employees",
        form_data=form_data,
        errors=errors,
        email_available=email_available,
        token_minutes=Config.PASSWORD_RESET_TOKEN_MINUTES,
    )


def _admin_only(view):
    """
    Run _require_admin() BEFORE any other decorator (notably @csrf_protect),
    so a non-Admin always gets 403 - even on a POST without a CSRF token,
    which @csrf_protect alone would answer with a redirect.
    """

    @wraps(view)
    def wrapper(*args, **kwargs):
        denied = _require_admin()
        if denied:
            return denied
        return view(*args, **kwargs)

    return wrapper


@admin_bp.route("/admin/invoice-numbering", methods=["GET", "POST"])
@_admin_only
@csrf_protect
def invoice_numbering():
    """
    Invoice Number Settings (Admin only): show the highest issued and next
    invoice number, and let an Admin move the next number UP after an
    explicit confirmation and re-entering their own password. Existing
    invoices are never changed - see services/invoice_number_service.py.
    """

    errors: dict = {}
    form_message = None
    submitted_value = ""

    if request.method == "POST":
        submitted_value = request.form.get("next_number", "").strip()
        success, message, errors = invoice_number_service.set_next_number(
            session["UserID"],
            submitted_value,
            request.form.get("password", ""),
            request.form.get("confirm") == "yes",
        )
        if success:
            flash(message, "success")
            return redirect(url_for("admin.invoice_numbering"))
        form_message = message

    return render_template(
        "admin/invoice_numbering.html",
        username=session.get("Username"),
        role=session.get("Role"),
        current_page="invoice_numbering",
        status=invoice_number_service.get_numbering_status(),
        recent_changes=invoice_number_service.get_recent_changes(),
        errors=errors,
        form_message=form_message,
        submitted_value=submitted_value,
    )


@admin_bp.route("/admin/employees/<int:user_id>/reset-password", methods=["POST"])
@csrf_protect(redirect_endpoint="admin.employees")
def reset_employee_password(user_id):
    """Email a single-use reset link to an Employee (Admin only)."""

    denied = _require_admin()
    if denied:
        return denied

    success, message = password_service.admin_initiate_reset(
        session["UserID"],
        user_id,
        lambda raw_token: url_for("employee.reset_password_link", token=raw_token),
    )
    flash(message, "success" if success else "danger")
    return redirect(url_for("admin.employees"))
