"""
=========================================================
Project : Sridevi Enterprises
File    : customer.py
Purpose : Customer-facing routes.

Author  : Srikar
=========================================================
"""

from math import ceil

from flask import Blueprint, abort, render_template, request
from services.customer_service import (
    get_featured_products,
    get_home_departments,
    get_popular_brands,
)
from services.enquiry_service import create_enquiry, get_enquiry_product, validate_enquiry
from services.product_service import (
    get_product,
    get_product_count,
    get_product_filters,
    get_products,
    get_related_products,
)

customer_bp = Blueprint("customer", __name__)


@customer_bp.route("/")
def home():
    """Render the database-driven customer homepage."""

    return render_template(
        "customer/home.html",
        departments=get_home_departments(),
        featured_products=get_featured_products(),
        brands=get_popular_brands(),
    )


@customer_bp.route("/products")
def products():
    """Render the searchable and filterable product listing."""

    filters = {
        "search": request.args.get("search", ""),
        "department": request.args.get("department", ""),
        "category": request.args.get("category", ""),
        "brand": request.args.get("brand", ""),
        "availability": request.args.get("availability", ""),
        "sort": request.args.get("sort", "newest"),
    }
    per_page = 24
    total_products = get_product_count(filters)
    total_pages = max(ceil(total_products / per_page), 1)
    requested_page = request.args.get("page", 1, type=int) or 1
    page = min(max(requested_page, 1), total_pages)
    page_start = max(page - 2, 1)
    page_end = min(page_start + 4, total_pages)
    page_start = max(page_end - 4, 1)

    return render_template(
        "customer/products.html",
        products=get_products(filters, page, per_page),
        filter_options=get_product_filters(),
        filters=filters,
        page=page,
        page_numbers=range(page_start, page_end + 1),
        total_pages=total_pages,
        total_products=total_products,
    )


@customer_bp.route("/products/<int:product_id>")
def product_details(product_id):
    """Render one product's details, gallery, specifications, and related products."""

    product = get_product(product_id)
    if product is None:
        abort(404)

    return render_template(
        "customer/product_details.html",
        product=product,
        related_products=get_related_products(product),
    )


@customer_bp.route("/products/<int:product_id>/enquiry", methods=["GET", "POST"])
def product_enquiry(product_id):
    """Display and submit a customer enquiry for a catalog product."""

    product = get_enquiry_product(product_id)
    if product is None:
        return render_template(
            "customer/enquiry_form.html",
            product=None,
            form_data={},
            errors={"form": "This product is no longer available."},
        ), 404

    form_data = {}
    errors = {}
    if request.method == "POST":
        form_data, errors = validate_enquiry(request.form)
        if not errors:
            saved, failure_message = create_enquiry(product_id, form_data)
            if saved:
                return render_template("customer/enquiry_success.html", product=product)
            errors["form"] = failure_message

    return render_template(
        "customer/enquiry_form.html",
        product=product,
        form_data=form_data,
        errors=errors,
    )


@customer_bp.route("/categories")
def categories():
    return "<h2>Categories - Coming Soon</h2>"


@customer_bp.route("/compare")
def compare():
    return "<h2>Compare - Coming Soon</h2>"


@customer_bp.route("/contact", methods=["GET", "POST"])
def contact():
    """Display and submit general customer enquiries."""

    form_data = {}
    errors = {}
    if request.method == "POST":
        form_data, errors = validate_enquiry(request.form, require_subject=True)
        if not errors:
            saved, failure_message = create_enquiry(None, form_data)
            if saved:
                return render_template("customer/enquiry_success.html", product=None)
            errors["form"] = failure_message

    return render_template(
        "customer/contact.html",
        form_data=form_data,
        errors=errors,
    )
