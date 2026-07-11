"""
=========================================================
Project : Sridevi Enterprises
File    : product_service.py
Purpose : Product catalog retrieval and filtering services.

Author  : Srikar
=========================================================
"""

from typing import Any

from database.db import fetch_all, fetch_one


_PLACEHOLDER_IMAGE = "images/placeholder.png"
_SORT_OPTIONS = {
    "newest": "id DESC",
    "name": "product_name ASC",
    "brand": "brand ASC",
}


def get_products(filters: dict[str, Any], page: int, per_page: int):
    """Return one paginated page of catalog products matching the supplied filters."""

    where_clause, params = _build_product_filters(filters)

    order_by = _SORT_OPTIONS.get(filters.get("sort"), _SORT_OPTIONS["newest"])
    products = fetch_all(f"""
        SELECT
            id, product_name, NULLIF(TRIM(brand), '') AS brand, Department,
            category,
            CASE WHEN stock_quantity > 0 THEN 'In stock' ELSE 'Available on request' END AS availability
        FROM Catalog
        WHERE {where_clause}
        ORDER BY {order_by}
        LIMIT %s OFFSET %s;
    """, tuple(params + [per_page, (page - 1) * per_page]))

    _add_primary_images(products)
    return products


def get_product_count(filters: dict[str, Any]) -> int:
    """Return the number of catalog products matching the supplied filters."""

    where_clause, params = _build_product_filters(filters)
    result = fetch_one(f"SELECT COUNT(*) AS total FROM Catalog WHERE {where_clause};", tuple(params))
    return result["total"]


def _build_product_filters(filters: dict[str, Any]) -> tuple[str, list[Any]]:
    """Build the reusable SQL WHERE clause for product listing and count queries."""

    where_clauses = ["product_name IS NOT NULL", "TRIM(product_name) <> ''"]
    params: list[Any] = []

    search = filters.get("search", "").strip()
    if search:
        like_value = f"%{search}%"
        where_clauses.append("""(
            product_name LIKE %s OR brand LIKE %s OR Department LIKE %s
            OR category LIKE %s OR model LIKE %s
        )""")
        params.extend([like_value] * 5)

    for field, column in (("department", "Department"), ("category", "category"), ("brand", "brand")):
        if filters.get(field):
            where_clauses.append(f"{column} = %s")
            params.append(filters[field])

    availability = filters.get("availability")
    if availability == "in_stock":
        where_clauses.append("stock_quantity > 0")
    elif availability == "on_request":
        where_clauses.append("stock_quantity <= 0")

    return " AND ".join(where_clauses), params


def get_product_filters():
    """Return database-driven values for product listing filters."""

    return {
        "departments": fetch_all("""
            SELECT DISTINCT Department AS value FROM Catalog
            WHERE Department IS NOT NULL AND TRIM(Department) <> '' ORDER BY Department;
        """),
        "categories": fetch_all("""
            SELECT DISTINCT category AS value FROM Catalog
            WHERE category IS NOT NULL AND TRIM(category) <> '' ORDER BY category;
        """),
        "brands": fetch_all("""
            SELECT DISTINCT TRIM(brand) AS value FROM Catalog
            WHERE brand IS NOT NULL AND TRIM(brand) NOT IN ('', 'NA') ORDER BY brand;
        """),
    }


def get_product(product_id: int):
    """Return one catalog product and its related detail records."""

    product = fetch_one("""
        SELECT
            id, product_name, NULLIF(TRIM(brand), '') AS brand, Department,
            category, model,
            CASE WHEN stock_quantity > 0 THEN 'In stock' ELSE 'Available on request' END AS availability
        FROM Catalog
        WHERE id = %s;
    """, (product_id,))

    if product is None:
        return None

    # TODO: Correct UTF-8 encoding in legacy imported catalog data if its source CSV is updated.
    product["product_name"] = _normalise_catalog_text(product["product_name"])
    product["images"] = get_product_images(product_id)
    product["specifications"] = fetch_all("""
        SELECT Property AS property, PropertyValue AS value
        FROM ProductDetails WHERE ProductID = %s ORDER BY DetailID;
    """, (product_id,))
    return product


def get_related_products(product: dict[str, Any]):
    """Return up to four products from the same department, preferring its category."""

    related_products = fetch_all("""
        SELECT
            id, product_name, NULLIF(TRIM(brand), '') AS brand,
            CASE WHEN stock_quantity > 0 THEN 'In stock' ELSE 'Available on request' END AS availability
        FROM Catalog
        WHERE id <> %s AND Department = %s
        ORDER BY (category = %s) DESC, id DESC
        LIMIT 4;
    """, (product["id"], product["Department"], product["category"]))

    _add_primary_images(related_products)
    return related_products


def _add_primary_images(products: list[dict[str, Any]]) -> None:
    """Attach each product's first image path with a single gallery query."""

    if not products:
        return

    product_ids = [product["id"] for product in products]
    placeholders = ", ".join(["%s"] * len(product_ids))
    images = fetch_all(f"""
        SELECT product_image.ProductID, product_image.ImageURL
        FROM ProductImages AS product_image
        INNER JOIN (
            SELECT ProductID, MIN(ImageID) AS image_id
            FROM ProductImages
            WHERE ProductID IN ({placeholders}) AND TRIM(ImageURL) <> ''
            GROUP BY ProductID
        ) AS first_image ON first_image.image_id = product_image.ImageID;
    """, tuple(product_ids))
    image_paths = {image["ProductID"]: image["ImageURL"] for image in images}

    for product in products:
        product["image_path"] = image_paths.get(product["id"], _PLACEHOLDER_IMAGE)
        # TODO: Correct UTF-8 encoding in legacy imported catalog data if its source CSV is updated.
        product["product_name"] = _normalise_catalog_text(product["product_name"])


def _normalise_catalog_text(value: str) -> str:
    """Hide replacement characters present in legacy catalog imports."""

    return value.replace("\ufffd", "")


def get_primary_product_image(product_id: int) -> str:
    """Return the first uploaded product image or the shared fallback image."""

    image = fetch_one("""
        SELECT ImageURL FROM ProductImages
        WHERE ProductID = %s AND TRIM(ImageURL) <> ''
        ORDER BY ImageID LIMIT 1;
    """, (product_id,))
    return image["ImageURL"] if image else _PLACEHOLDER_IMAGE


def get_product_images(product_id: int):
    """Return uploaded product gallery images or one fallback image."""

    images = fetch_all("""
        SELECT ImageURL AS image_path FROM ProductImages
        WHERE ProductID = %s AND TRIM(ImageURL) <> '' ORDER BY ImageID;
    """, (product_id,))
    return images or [{"image_path": _PLACEHOLDER_IMAGE, "is_placeholder": True}]
