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

Author  : Srikar
=========================================================
"""

import logging

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

from config import Config
from services import email_service, password_service
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
