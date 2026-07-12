"""
=========================================================
Project : Sridevi Enterprises
File    : employee.py
Purpose : Employee routes.

Author  : Srikar
=========================================================
"""

from flask import Blueprint, render_template, request, session, redirect, url_for
from services.auth_service import authenticate_employee
from flask import flash

employee_bp = Blueprint("employee", __name__)


@employee_bp.route("/employee/login", methods=["GET", "POST"])
def login():
    """Handle employee login page and authentication."""

    error = None
    success_message = None

    if request.args.get("logout_success"):
        success_message = "You have been logged out successfully."

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            error = "Username and password are required."
        else:
            user = authenticate_employee(username, password)

            if user:
                session["UserID"] = user["UserID"]
                session["Username"] = user["Username"]
                session["Role"] = user["Role"]

                return redirect(url_for("employee.dashboard"))
            else:
                error = "Invalid username or password."

    return render_template(
        "employee/login.html", error=error, success_message=success_message
    )


@employee_bp.route("/employee/dashboard", methods=["GET"])
def dashboard():
    """Display employee dashboard."""

    if not session.get("UserID"):
        return redirect(url_for("employee.login"))

    username = session.get("Username")
    role = session.get("Role")

    return render_template(
        "employee/dashboard.html",
        username=username,
        role=role,
        current_page="dashboard",
    )


@employee_bp.route("/employee/products", methods=["GET"])
def products():
    """Placeholder products route."""

    if not session.get("UserID"):
        return redirect(url_for("employee.login"))

    username = session.get("Username")
    role = session.get("Role")

    return render_template(
        "employee/dashboard.html",
        username=username,
        role=role,
        current_page="products",
        coming_soon_message="Products module coming in next phase",
    )


@employee_bp.route("/employee/enquiries", methods=["GET"])
def enquiries():
    """Placeholder enquiries route."""

    if not session.get("UserID"):
        return redirect(url_for("employee.login"))

    username = session.get("Username")
    role = session.get("Role")

    return render_template(
        "employee/dashboard.html",
        username=username,
        role=role,
        current_page="enquiries",
        coming_soon_message="Enquiries module coming in next phase",
    )


@employee_bp.route("/employee/customers", methods=["GET"])
def customers():
    """Placeholder customers route."""

    if not session.get("UserID"):
        return redirect(url_for("employee.login"))

    username = session.get("Username")
    role = session.get("Role")

    return render_template(
        "employee/dashboard.html",
        username=username,
        role=role,
        current_page="customers",
        coming_soon_message="Customers module coming in next phase",
    )


@employee_bp.route("/employee/logout", methods=["GET"])
def logout():
    """Clear session and redirect to login."""

    session.clear()
    flash("You have been logged out successfully.", "success")
    return redirect(url_for("employee.login"))
