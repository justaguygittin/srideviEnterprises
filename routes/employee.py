"""
=========================================================
Project : Sridevi Enterprises
File    : employee.py
Purpose : Employee routes.

Author  : Srikar
=========================================================
"""

from math import ceil

from flask import Blueprint, render_template, request, session, redirect, url_for
from services.auth_service import authenticate_employee
from services.product_service import get_products, get_product_count

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
    """Display read-only products list for employees."""

    if not session.get("UserID"):
        return redirect(url_for("employee.login"))

    username = session.get("Username")
    role = session.get("Role")

    page = request.args.get("page", 1, type=int)
    search = request.args.get("search", "").strip()
    department = request.args.get("department", "").strip()
    category = request.args.get("category", "").strip()
    brand = request.args.get("brand", "").strip()

    filters = {
        "search": search,
        "department": department if department else None,
        "category": category if category else None,
        "brand": brand if brand else None,
    }

    per_page = 20
    total_products = get_product_count(filters)
    total_pages = ceil(total_products / per_page) if total_products > 0 else 1

    if page < 1 or page > total_pages:
        page = 1

    product_list = get_products(filters, page, per_page)

    start_page = max(1, page - 2)
    end_page = min(total_pages, page + 2)

    return render_template(
        "employee/products.html",
        username=username,
        role=role,
        current_page="products",
        products=product_list,
        page=page,
        total_pages=total_pages,
        total_products=total_products,
        search=search,
        department=department,
        category=category,
        brand=brand,
        start_page=start_page,
        end_page=end_page,
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

    return redirect(url_for("employee.login", logout_success=True))
