"""
=========================================================
Project : Sridevi Enterprises
File    : customer.py
Purpose : Customer-facing routes.

Author  : Srikar
=========================================================
"""

from flask import Blueprint, abort, render_template, request
from services.customer_service import (
    get_featured_products,
    get_home_departments,
    get_popular_brands,
)
from services.product_service import get_product, get_product_filters, get_products, get_related_products

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
        "min_price": request.args.get("min_price", type=float),
        "max_price": request.args.get("max_price", type=float),
    }
    return render_template(
        "customer/products.html",
        products=get_products(filters),
        filter_options=get_product_filters(),
        filters=filters,
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


@customer_bp.route("/categories")
def categories():
    return "<h2>Categories - Coming Soon</h2>"


@customer_bp.route("/compare")
def compare():
    return "<h2>Compare - Coming Soon</h2>"


@customer_bp.route("/contact")
def contact():
    return "<h2>Contact - Coming Soon</h2>"
