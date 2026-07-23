"""
=========================================================
Project : Sridevi Enterprises
File    : product_service.py
Purpose : Product catalog retrieval and filtering services.

Author  : Srikar
=========================================================
"""

from typing import Any

from database.db import execute, fetch_all, fetch_one, transaction
from services.image_service import delete_image_file, delete_product_folder, save_product_images


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
    product["specifications"] = _get_product_specifications(product_id)
    return product


def _get_product_specifications(product_id: int):
    """Return a product's specification rows, ordered as entered."""

    return fetch_all("""
        SELECT Property AS property, PropertyValue AS value
        FROM ProductDetails WHERE ProductID = %s ORDER BY DetailID;
    """, (product_id,))


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


def get_product_images_with_ids(product_id: int):
    """Return a product's images including ImageID, for image management on Edit Product."""

    return fetch_all("""
        SELECT ImageID AS id, ImageURL AS image_path FROM ProductImages
        WHERE ProductID = %s AND TRIM(ImageURL) <> '' ORDER BY ImageID;
    """, (product_id,))


def get_product_for_edit(product_id: int):
    """Return one catalog product's raw editable fields and specifications."""

    product = fetch_one("""
        SELECT id, product_name, Department AS department, category,
               NULLIF(TRIM(brand), '') AS brand, model, stock_quantity
        FROM Catalog
        WHERE id = %s;
    """, (product_id,))

    if product is None:
        return None

    product["product_name"] = _normalise_catalog_text(product["product_name"])
    product["specifications"] = _get_product_specifications(product_id)
    return product


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


def update_product(
    product_id: int,
    product_data: dict[str, Any],
    specifications: list[tuple[str, str]],
    new_images: list,
    replacement_images: dict[int, Any],
) -> None:
    """
    Update a catalog product's fields, specifications, and images as one atomic write.

    Standard write-operation pattern (see AI_CONTEXT.md):
    Begin Transaction -> Database Update -> Filesystem Update -> Database Metadata -> Commit.
    On failure: Rollback Database -> Cleanup Files -> Return Error (re-raised).

    Replaced images are only deleted from disk after the transaction commits,
    so a mid-write failure never destroys a still-referenced file.
    """

    replaced_image_ids = list(replacement_images.keys())
    newly_saved_paths: list[str] = []
    old_paths_to_delete: list[str] = []

    try:
        with transaction() as conn:
            cursor = conn.cursor(dictionary=True)
            try:
                cursor.execute("""
                    UPDATE Catalog
                    SET product_name = %s, Department = %s, category = %s,
                        brand = %s, model = %s, stock_quantity = %s
                    WHERE id = %s;
                """, (
                    product_data["product_name"],
                    product_data["department"],
                    product_data["category"],
                    product_data["brand"],
                    product_data["model"],
                    product_data["stock_quantity"],
                    product_id,
                ))

                current_rows: dict[int, str] = {}
                if replaced_image_ids:
                    placeholders = ", ".join(["%s"] * len(replaced_image_ids))
                    cursor.execute(f"""
                        SELECT ImageID, ImageURL FROM ProductImages
                        WHERE ProductID = %s AND ImageID IN ({placeholders});
                    """, (product_id, *replaced_image_ids))
                    current_rows = {row["ImageID"]: row["ImageURL"] for row in cursor.fetchall()}

                files_to_save = list(new_images) + [replacement_images[image_id] for image_id in replaced_image_ids]
                saved_paths = save_product_images(product_id, files_to_save)
                newly_saved_paths = saved_paths

                added_paths = saved_paths[:len(new_images)]
                replacement_paths = saved_paths[len(new_images):]

                for image_path in added_paths:
                    cursor.execute("""
                        INSERT INTO ProductImages (ProductID, ImageURL) VALUES (%s, %s);
                    """, (product_id, image_path))

                for image_id, new_path in zip(replaced_image_ids, replacement_paths):
                    cursor.execute("""
                        UPDATE ProductImages SET ImageURL = %s WHERE ImageID = %s;
                    """, (new_path, image_id))
                    if image_id in current_rows:
                        old_paths_to_delete.append(current_rows[image_id])

                cursor.execute("DELETE FROM ProductDetails WHERE ProductID = %s;", (product_id,))
                for property_name, property_value in specifications:
                    cursor.execute("""
                        INSERT INTO ProductDetails (ProductID, Property, PropertyValue) VALUES (%s, %s, %s);
                    """, (product_id, property_name, property_value))
            finally:
                cursor.close()
    except Exception:
        for image_path in newly_saved_paths:
            delete_image_file(image_path)
        raise

    for image_path in old_paths_to_delete:
        delete_image_file(image_path)


def delete_product_image(product_id: int, image_id: int) -> tuple[bool, str | None]:
    """Delete one product image; refuses to delete a product's last remaining image."""

    image_count = fetch_one(
        "SELECT COUNT(*) AS total FROM ProductImages WHERE ProductID = %s;", (product_id,)
    )["total"]
    if image_count <= 1:
        return False, "A product must have at least one image. Add a replacement before deleting this one."

    image = fetch_one(
        "SELECT ImageURL FROM ProductImages WHERE ImageID = %s AND ProductID = %s;",
        (image_id, product_id),
    )
    if image is None:
        return False, "Image not found."

    execute("DELETE FROM ProductImages WHERE ImageID = %s;", (image_id,))
    delete_image_file(image["ImageURL"])
    return True, None


def delete_product(product_id: int) -> None:
    """
    Delete a product and all its related rows as one atomic write.

    Standard write-operation pattern (see AI_CONTEXT.md):
    Begin Transaction -> Database Delete -> Commit -> Filesystem Cleanup.

    The upload folder is removed only after the transaction commits, so a
    mid-transaction failure can never delete images for a product that
    still exists in the database.
    """

    with transaction() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM ProductDetails WHERE ProductID = %s;", (product_id,))
            cursor.execute("DELETE FROM ProductImages WHERE ProductID = %s;", (product_id,))
            cursor.execute("DELETE FROM Catalog WHERE id = %s;", (product_id,))
        finally:
            cursor.close()

    delete_product_folder(product_id)
