"""
=========================================================
Project : Sridevi Enterprises
File    : customer.py
Purpose : Customer-facing routes.

Author  : Srikar
=========================================================
"""

from flask import Blueprint, render_template
from database.db import fetch_all

customer_bp = Blueprint("customer", __name__)


@customer_bp.route("/")
def home():

    departments = fetch_all("""
        SELECT
            Department,
            COUNT(*) AS total_products
        FROM Catalog
        GROUP BY Department
        ORDER BY Department
    """)

    return render_template("customer/home.html", departments=departments)


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
