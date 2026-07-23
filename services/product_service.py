"""
=========================================================
Project : Sridevi Enterprises
File    : product_service.py
Purpose : Product catalog retrieval and filtering services.

Author  : Srikar
=========================================================
"""

from typing import Any

from database.db import fetch_all, fetch_one, transaction
from services.image_service import delete_product_folder, save_product_images


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


def validate_product_form(form_data: dict[str, str]) -> tuple[dict[str, Any], dict[str, str]]:
    """Validate and normalize Add/Edit Product form fields."""

    cleaned_data: dict[str, Any] = {
        "product_name": form_data.get("product_name", "").strip(),
        "department": form_data.get("department", "").strip(),
        "category": form_data.get("category", "").strip(),
        "brand": form_data.get("brand", "").strip() or None,
        "model": form_data.get("model", "").strip() or None,
        "stock_quantity": form_data.get("stock_quantity", "").strip(),
    }
    errors: dict[str, str] = {}

    if not cleaned_data["product_name"]:
        errors["product_name"] = "Please enter a product name."
    elif len(cleaned_data["product_name"]) > 255:
        errors["product_name"] = "Product name must be 255 characters or fewer."

    if not cleaned_data["department"]:
        errors["department"] = "Please enter a department."
    elif len(cleaned_data["department"]) > 100:
        errors["department"] = "Department must be 100 characters or fewer."

    if not cleaned_data["category"]:
        errors["category"] = "Please enter a category."
    elif len(cleaned_data["category"]) > 255:
        errors["category"] = "Category must be 255 characters or fewer."

    if cleaned_data["brand"] and len(cleaned_data["brand"]) > 255:
        errors["brand"] = "Brand must be 255 characters or fewer."

    if cleaned_data["model"] and len(cleaned_data["model"]) > 255:
        errors["model"] = "Model must be 255 characters or fewer."

    stock_quantity_raw = cleaned_data["stock_quantity"]
    if not stock_quantity_raw:
        cleaned_data["stock_quantity"] = 0
    elif not stock_quantity_raw.isdigit():
        errors["stock_quantity"] = "Stock quantity must be a non-negative whole number."
    else:
        cleaned_data["stock_quantity"] = int(stock_quantity_raw)

    return cleaned_data, errors


def validate_specifications(
    properties: list[str], values: list[str]
) -> tuple[list[tuple[str, str]], str | None]:
    """Pair, trim, and validate submitted specification rows, skipping fully blank rows."""

    specifications: list[tuple[str, str]] = []

    for property_name, property_value in zip(properties, values):
        property_name = property_name.strip()
        property_value = property_value.strip()

        if not property_name and not property_value:
            continue
        if not property_name or not property_value:
            return [], "Each specification needs both a property and a value."
        if len(property_name) > 100 or len(property_value) > 255:
            return [], "Specification property or value is too long."

        specifications.append((property_name, property_value))

    return specifications, None


def find_similar_product(
    product_name: str, brand: str | None, model: str | None, exclude_id: int | None = None
) -> dict[str, Any] | None:
    """Return an existing catalog product with a matching name, brand, and model, if any."""

    where_clauses = [
        "LOWER(TRIM(product_name)) = LOWER(%s)",
        "LOWER(TRIM(COALESCE(brand, ''))) = LOWER(%s)",
        "LOWER(TRIM(COALESCE(model, ''))) = LOWER(%s)",
    ]
    params: list[Any] = [product_name, brand or "", model or ""]

    if exclude_id is not None:
        where_clauses.append("id <> %s")
        params.append(exclude_id)

    return fetch_one(f"""
        SELECT id, product_name FROM Catalog WHERE {" AND ".join(where_clauses)} LIMIT 1;
    """, tuple(params))


def create_product(
    product_data: dict[str, Any],
    image_files: list,
    specifications: list[tuple[str, str]],
) -> int:
    """
    Create a catalog product with its images and specifications as one atomic write.

    Standard write-operation pattern (see AI_CONTEXT.md):
    Begin Transaction -> Database Write -> Filesystem Write -> Database Metadata -> Commit.
    On failure: Rollback Database -> Delete Uploaded Files -> Return Error (re-raised).
    """

    product_id = None

    try:
        with transaction() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO Catalog (product_name, Department, category, brand, model, stock_quantity)
                    VALUES (%s, %s, %s, %s, %s, %s);
                """, (
                    product_data["product_name"],
                    product_data["department"],
                    product_data["category"],
                    product_data["brand"],
                    product_data["model"],
                    product_data["stock_quantity"],
                ))
                product_id = cursor.lastrowid

                image_paths = save_product_images(product_id, image_files)

                for image_path in image_paths:
                    cursor.execute("""
                        INSERT INTO ProductImages (ProductID, ImageURL) VALUES (%s, %s);
                    """, (product_id, image_path))

                for property_name, property_value in specifications:
                    cursor.execute("""
                        INSERT INTO ProductDetails (ProductID, Property, PropertyValue) VALUES (%s, %s, %s);
                    """, (product_id, property_name, property_value))
            finally:
                cursor.close()
    except Exception:
        if product_id is not None:
            delete_product_folder(product_id)
        raise

    return product_id
