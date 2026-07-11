"""
=========================================================
Project : Sridevi Enterprises
File    : customer.py
Purpose : Customer-facing routes.

Author  : Srikar
=========================================================
"""

from flask import Blueprint, render_template
from services.customer_service import (
    get_featured_products,
    get_home_departments,
    get_popular_brands,
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
    return "<h2>Products - Coming Soon</h2>"


@customer_bp.route("/categories")
def categories():
    return "<h2>Categories - Coming Soon</h2>"


@customer_bp.route("/compare")
def compare():
    return "<h2>Compare - Coming Soon</h2>"


@customer_bp.route("/contact")
def contact():
    return "<h2>Contact - Coming Soon</h2>"
