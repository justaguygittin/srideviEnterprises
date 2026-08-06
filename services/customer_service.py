"""
=========================================================
Project : Sridevi Enterprises
File    : customer_service.py
Purpose : Homepage data retrieval and presentation helpers.

Author  : Srikar
=========================================================
"""

from database.db import fetch_all
from services.department_service import get_active_department_cards
from services.product_service import add_primary_images


def get_home_departments():
    """
    Return active, employee-configured departments with product totals and
    images, for the homepage Featured Categories slider and the standalone
    Categories page.

    Delegates to department_service.get_active_department_cards() (Department
    Image Management) - the old hardcoded _CATEGORY_IMAGES lookup (which only
    covered 4 of the catalog's 10 departments, silently falling back to a
    placeholder for the rest) has been fully replaced by the
    employee-managed DepartmentImages table.
    """

    return get_active_department_cards()


def get_featured_products():
    """
    Return eight randomly selected catalog products, with their real images.

    v1.0 Sprint 7 (Product Lifecycle Management): IsActive = 1 - a
    deactivated product must never surface on the customer-facing homepage,
    even by random chance (see AI_CONTEXT.md "Customer Site (IsActive
    Filtering)").
    """

    products = fetch_all("""
        SELECT
            id,
            product_name,
            NULLIF(TRIM(brand), '') AS brand,
            CASE
                WHEN stock_quantity > 0 THEN 'In stock'
                ELSE 'Available on request'
            END AS availability
        FROM Catalog
        WHERE product_name IS NOT NULL AND TRIM(product_name) <> '' AND IsActive = 1
        ORDER BY RAND()
        LIMIT 8;
    """)

    # Bug fix: this previously left every card on a hardcoded placeholder
    # image (see home.html) even though real ProductImages rows existed -
    # every other product listing already attaches images this way.
    add_primary_images(products)
    return products


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
