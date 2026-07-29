"""
=========================================================
Project : Sridevi Enterprises
File    : customer_service.py
Purpose : Homepage data retrieval and presentation helpers.

Author  : Srikar
=========================================================
"""

import os

from database.db import fetch_all


_CATEGORY_IMAGES = {
    "electronics": "images/categories/electronics.jpg",
    "furniture": "images/categories/furniture.jpg",
    "miscellaneous": "images/categories/miscellaneous.jpg",
    "utility": "images/categories/utility.jpg",
}
_PLACEHOLDER_IMAGE = "images/placeholder.png"
_STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")


def _resolve_category_image(department_name):
    """Return the mapped category image, or the placeholder if it is missing or empty."""

    image_path = _CATEGORY_IMAGES.get(department_name.strip().lower())

    if image_path:
        full_path = os.path.join(_STATIC_DIR, *image_path.split("/"))
        if os.path.isfile(full_path) and os.path.getsize(full_path) > 0:
            return image_path

    return _PLACEHOLDER_IMAGE


def get_home_departments():
    """Return catalog departments with product totals and available images."""

    departments = fetch_all("""
        SELECT Department, COUNT(*) AS total_products
        FROM Catalog
        WHERE Department IS NOT NULL AND TRIM(Department) <> ''
        GROUP BY Department
        ORDER BY Department;
    """)

    for department in departments:
        department["image_path"] = _resolve_category_image(department["Department"])

    return departments


def get_featured_products():
    """Return eight randomly selected catalog products for the homepage."""

    return fetch_all("""
        SELECT
            id,
            product_name,
            NULLIF(TRIM(brand), '') AS brand,
            CASE
                WHEN stock_quantity > 0 THEN 'In stock'
                ELSE 'Available on request'
            END AS availability
        FROM Catalog
        WHERE product_name IS NOT NULL AND TRIM(product_name) <> ''
        ORDER BY RAND()
        LIMIT 8;
    """)


def get_popular_brands():
    """Return a concise set of distinct catalog brands for the homepage."""

    return fetch_all("""
        SELECT DISTINCT TRIM(brand) AS brand
        FROM Catalog
        WHERE brand IS NOT NULL
          AND TRIM(brand) NOT IN ('', 'NA')
        ORDER BY brand
        LIMIT 12;
    """)
