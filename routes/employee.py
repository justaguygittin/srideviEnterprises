"""
=========================================================
Project : Sridevi Enterprises
File    : employee.py
Purpose : Employee routes.

Author  : Srikar
=========================================================
"""

from math import ceil

from flask import Blueprint, abort, flash, render_template, request, session, redirect, url_for
from services.auth_service import authenticate_employee
from services.image_service import validate_image_files
from services.product_service import (
    create_product,
    find_similar_product,
    get_product,
    get_product_count,
    get_product_filters,
    get_products,
    get_related_products,
    validate_product_form,
    validate_specifications,
)

EMPLOYEE_PORTAL_ROLES = ("Employee", "Admin")
SPEC_ROW_COUNT = 6

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
                session["Designation"] = user["Designation"]

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
    designation = session.get("Designation")

    return render_template(
        "employee/dashboard.html",
        username=username,
        role=role,
        designation=designation,
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


@employee_bp.route("/employee/products/add", methods=["GET", "POST"])
def add_product():
    """Display and handle the Add Product form for Employee and Admin roles."""

    if not session.get("UserID"):
        return redirect(url_for("employee.login"))

    if session.get("Role") not in EMPLOYEE_PORTAL_ROLES:
        abort(403)

    form_data: dict = {}
    errors: dict = {}
    spec_rows = [{"property": "", "value": ""} for _ in range(SPEC_ROW_COUNT)]

    if request.method == "POST":
        form_data, errors = validate_product_form(request.form)

        spec_properties = request.form.getlist("spec_property")
        spec_values = request.form.getlist("spec_value")
        spec_rows = [
            {"property": property_name, "value": property_value}
            for property_name, property_value in zip(spec_properties, spec_values)
        ]
        while len(spec_rows) < SPEC_ROW_COUNT:
            spec_rows.append({"property": "", "value": ""})

        specifications, spec_error = validate_specifications(spec_properties, spec_values)
        if spec_error:
            errors["specifications"] = spec_error

        images = request.files.getlist("images")
        image_error = validate_image_files(images)
        if image_error:
            errors["images"] = image_error

        if not errors:
            duplicate = find_similar_product(
                form_data["product_name"], form_data["brand"], form_data["model"]
            )

            try:
                product_id = create_product(form_data, images, specifications)
            except Exception:
                errors["form"] = "Could not save this product. Please try again."
            else:
                if duplicate:
                    flash(
                        f"Note: product #{duplicate['id']} (\"{duplicate['product_name']}\") "
                        "looks similar to this one.",
                        "warning",
                    )
                flash("Product created successfully.", "success")
                return redirect(url_for("employee.product_details", product_id=product_id))

    return render_template(
        "employee/product_form.html",
        username=session.get("Username"),
        role=session.get("Role"),
        current_page="products",
        form_data=form_data,
        errors=errors,
        spec_rows=spec_rows,
        filter_options=get_product_filters(),
    )


@employee_bp.route("/employee/products/<int:product_id>", methods=["GET"])
def product_details(product_id):
    """Display one product's read-only details for Employee and Admin roles."""

    if not session.get("UserID"):
        return redirect(url_for("employee.login"))

    if session.get("Role") not in EMPLOYEE_PORTAL_ROLES:
        abort(403)

    product = get_product(product_id)
    if product is None:
        abort(404)

    return render_template(
        "employee/product_details.html",
        username=session.get("Username"),
        role=session.get("Role"),
        current_page="products",
        product=product,
        related_products=get_related_products(product),
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
