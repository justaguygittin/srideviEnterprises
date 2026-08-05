"""
=========================================================
Project : Sridevi Enterprises
File    : product_service.py
Purpose : Product catalog retrieval and filtering services.

Author  : Srikar
=========================================================
"""

import re
from typing import Any

from database.db import execute, fetch_all, fetch_one, transaction
from services.image_service import delete_image_file, delete_product_folder, save_product_images


_PLACEHOLDER_IMAGE = "images/placeholder.png"
_SORT_OPTIONS = {
    "newest": "id DESC",
    "name": "product_name ASC",
    "brand": "brand ASC",
}

# v1.0 Sprint 1 (Inventory Dashboard Foundation): temporary global threshold
# used to classify every product's inventory status. A later sprint will
# replace this with a per-product `MinimumStock` column on Catalog - do not
# treat this as permanent. Private: nothing outside get_low_stock_threshold()
# below should reference this constant directly.
_LOW_STOCK_THRESHOLD = 5


def get_low_stock_threshold() -> int:
    """
    Single source of truth for the "low stock" cutoff used by every inventory
    query and by the Inventory Summary page's threshold note.

    v1.0 Sprint 1/2: returns the temporary global _LOW_STOCK_THRESHOLD constant
    above - the same number applies to every product regardless of department,
    category, or typical turnover.

    Future sprint (MinimumStock column): once Catalog gains a per-product
    `MinimumStock` column, this is the ONLY function that needs to change.
    It would stop returning a single int and the call sites below would move
    from a literal `stock_quantity <= %s` comparison to a per-row column
    comparison (e.g. `stock_quantity <= COALESCE(MinimumStock, <fallback>)`).
    No other function in this file, and nothing in routes/employee.py or the
    templates, would need to change.
    """

    return _LOW_STOCK_THRESHOLD


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

    add_primary_images(products)
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
    """Return database-driven values for product listing/form filters."""

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
        "department_category_map": _get_department_category_map(),
    }


def _get_department_category_map() -> dict[str, list[str]]:
    """
    Group distinct categories by department, for the Add/Edit Product form's
    cascading Department -> Category searchable dropdown (v1.0 Sprint 4).

    Not used by the customer Products page filter, which keeps its own flat
    `categories` list above (unchanged) - this is an additive key only.
    """

    rows = fetch_all("""
        SELECT DISTINCT Department AS department, category
        FROM Catalog
        WHERE Department IS NOT NULL AND TRIM(Department) <> ''
              AND category IS NOT NULL AND TRIM(category) <> ''
        ORDER BY Department, category;
    """)

    department_category_map: dict[str, list[str]] = {}
    for row in rows:
        department_category_map.setdefault(row["department"], []).append(row["category"])
    return department_category_map


def get_inventory_summary() -> dict[str, int]:
    """Return catalog-wide inventory counts using the temporary low-stock threshold."""

    threshold = get_low_stock_threshold()
    result = fetch_one("""
        SELECT
            COUNT(*) AS total_products,
            COALESCE(SUM(stock_quantity), 0) AS total_stock_units,
            SUM(CASE WHEN stock_quantity > %s THEN 1 ELSE 0 END) AS healthy_count,
            SUM(CASE WHEN stock_quantity BETWEEN 1 AND %s THEN 1 ELSE 0 END) AS low_stock_count,
            SUM(CASE WHEN stock_quantity IS NULL OR stock_quantity = 0 THEN 1 ELSE 0 END) AS out_of_stock_count
        FROM Catalog
        WHERE product_name IS NOT NULL AND TRIM(product_name) <> '';
    """, (threshold, threshold))
    return {key: int(value) for key, value in result.items()}


def get_inventory_by_department():
    """Return per-department product counts, stock totals, and status breakdown."""

    return _get_inventory_group_summary("Department")


def get_inventory_by_category():
    """Return per-category product counts, stock totals, and status breakdown."""

    return _get_inventory_group_summary("category")


def _get_inventory_group_summary(column: str) -> list[dict[str, Any]]:
    """Shared aggregation query behind get_inventory_by_department/_category."""

    rows = fetch_all(f"""
        SELECT
            {column} AS name,
            COUNT(*) AS total_products,
            COALESCE(SUM(stock_quantity), 0) AS total_stock_units,
            SUM(CASE WHEN stock_quantity BETWEEN 1 AND %s THEN 1 ELSE 0 END) AS low_stock_count,
            SUM(CASE WHEN stock_quantity IS NULL OR stock_quantity = 0 THEN 1 ELSE 0 END) AS out_of_stock_count
        FROM Catalog
        WHERE product_name IS NOT NULL AND TRIM(product_name) <> ''
              AND {column} IS NOT NULL AND TRIM({column}) <> ''
        GROUP BY {column}
        ORDER BY {column};
    """, (get_low_stock_threshold(),))

    for row in rows:
        row["total_products"] = int(row["total_products"])
        row["total_stock_units"] = int(row["total_stock_units"])
        row["low_stock_count"] = int(row["low_stock_count"])
        row["out_of_stock_count"] = int(row["out_of_stock_count"])
    return rows


def _stock_status_filter(status: str) -> tuple[str, list[Any]]:
    """Return the WHERE fragment and params identifying one inventory status bucket."""

    if status == "out_of_stock":
        return "(stock_quantity IS NULL OR stock_quantity = 0)", []
    if status == "low_stock":
        return "stock_quantity BETWEEN 1 AND %s", [get_low_stock_threshold()]
    raise ValueError(f"Unknown stock status: {status}")


def get_stock_status_count(status: str) -> int:
    """Return how many catalog products fall into one inventory status bucket."""

    clause, params = _stock_status_filter(status)
    result = fetch_one(f"""
        SELECT COUNT(*) AS total FROM Catalog
        WHERE product_name IS NOT NULL AND TRIM(product_name) <> '' AND {clause};
    """, tuple(params))
    return result["total"]


def get_products_by_stock_status(status: str, page: int, per_page: int):
    """Return one paginated page of catalog products in one inventory status bucket."""

    clause, params = _stock_status_filter(status)
    products = fetch_all(f"""
        SELECT id, product_name, Department, category, NULLIF(TRIM(brand), '') AS brand, stock_quantity
        FROM Catalog
        WHERE product_name IS NOT NULL AND TRIM(product_name) <> '' AND {clause}
        ORDER BY stock_quantity ASC, product_name ASC
        LIMIT %s OFFSET %s;
    """, tuple(params + [per_page, (page - 1) * per_page]))

    for product in products:
        product["product_name"] = _normalise_catalog_text(product["product_name"])
        product["stock_quantity"] = product["stock_quantity"] or 0
    return products


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

    add_primary_images(related_products)
    return related_products


def add_primary_images(products: list[dict[str, Any]]) -> None:
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


_MULTI_SPACE_PATTERN = re.compile(r"\s+")


def _normalise_name_for_comparison(name: str) -> str:
    """
    Case-insensitive, whitespace-collapsed comparison key for product names
    (v1.0 Sprint 4) - shared logic mirrored by the Add/Edit Product form's
    client-side live duplicate check, so both agree on what counts as "the
    same name".
    """

    return _MULTI_SPACE_PATTERN.sub(" ", name.strip()).lower()


def get_all_product_names(exclude_id: int | None = None) -> list[dict[str, Any]]:
    """
    Return every catalog product's id/name (v1.0 Sprint 4). Powers both the
    Add/Edit Product form's client-side live duplicate-name hint and the
    authoritative server-side check below, from one shared query.
    """

    where_clause = "product_name IS NOT NULL AND TRIM(product_name) <> ''"
    params: list[Any] = []
    if exclude_id is not None:
        where_clause += " AND id <> %s"
        params.append(exclude_id)

    return fetch_all(f"SELECT id, product_name FROM Catalog WHERE {where_clause};", tuple(params))


def find_duplicate_product_name(product_name: str, exclude_id: int | None = None) -> dict[str, Any] | None:
    """
    Return an existing catalog product whose name matches product_name once
    both are case-insensitively compared with whitespace collapsed
    (v1.0 Sprint 4). This is the authoritative, final duplicate-name check
    enforced on every submit - the client-side live check is a hint only and
    can never be trusted on its own.

    Distinct from find_similar_product() above: that function compares
    name+brand+model together and only produces a soft "looks similar"
    warning: this function compares name alone and blocks the save.
    """

    target = _normalise_name_for_comparison(product_name)
    for candidate in get_all_product_names(exclude_id):
        if _normalise_name_for_comparison(candidate["product_name"]) == target:
            return candidate
    return None


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


# =========================================================
# Inventory Transactions (v1.0 Sprint 5.1: Stock In / Stock Out / Adjustment)
#
# One reusable transaction, not three separate features - "transaction_type"
# is one of the keys in _TRANSACTION_TYPE_LABELS below, and every write goes
# through apply_stock_transaction() so Catalog.stock_quantity and
# StockHistory can never drift out of sync (see Write Operation Pattern).
# =========================================================

_TRANSACTION_TYPE_LABELS = {
    "stock_in": "Stock In",
    "stock_out": "Stock Out",
    "adjustment": "Adjustment",
}

# The actual StockHistory.TransactionType values written to the database.
# ALL_CAPS to match this column's own DEFAULT 'ADJUSTMENT' (see
# 009_alter_stockhistory_add_transaction_columns.sql / AI_CONTEXT.md for the
# schema-drift note explaining why - the live column defaults were hardened
# to NOT NULL with specific defaults after the migration file was written).
_TRANSACTION_TYPE_DB_VALUES = {
    "stock_in": "STOCK_IN",
    "stock_out": "STOCK_OUT",
    "adjustment": "ADJUSTMENT",
}

# Every Sprint 5.1 transaction is directly employee-initiated - there is no
# Purchase Order/Goods Receipt/Sales Invoice to point back to yet (see
# AI_CONTEXT.md Out of Scope), so ReferenceType is always this sentinel
# (matching StockHistory.ReferenceType's own DEFAULT) and ReferenceID stays
# NULL.
_MANUAL_REFERENCE_TYPE = "MANUAL"


def get_products_for_transaction() -> list[dict[str, Any]]:
    """
    Return every catalog product's id/name/department/category/stock, for
    the Inventory Transaction form's searchable product selector and its
    client-side current-stock preview (v1.0 Sprint 5.1). Unpaginated and
    deliberately minimal - reuses the same "valid product" WHERE clause as
    every other product-listing query.
    """

    products = fetch_all("""
        SELECT id, product_name, Department, category, stock_quantity
        FROM Catalog
        WHERE product_name IS NOT NULL AND TRIM(product_name) <> ''
        ORDER BY product_name;
    """)

    for product in products:
        product["product_name"] = _normalise_catalog_text(product["product_name"])
        product["stock_quantity"] = product["stock_quantity"] or 0
    return products


def validate_stock_transaction_form(form_data: dict[str, str]) -> tuple[dict[str, Any], dict[str, str]]:
    """
    Validate and normalize the Inventory Transaction form (v1.0 Sprint 5.1).

    quantity_input means different things depending on transaction_type: the
    amount to add/remove for Stock In/Stock Out, or the new absolute stock
    level for Adjustment - apply_stock_transaction() below is what turns it
    into an actual OldStock/NewStock/QuantityChanged triple. This function
    only checks shape (present, numeric, in-range) - it does not touch the
    database, matching validate_product_form()'s existing split between pure
    field validation and the separate DB-backed checks (find_similar_product,
    find_duplicate_product_name) called from the route.
    """

    cleaned_data: dict[str, Any] = {
        "product_id": form_data.get("product_id", "").strip(),
        "transaction_type": form_data.get("transaction_type", "").strip(),
        "quantity_input": form_data.get("quantity_input", "").strip(),
        "reason": form_data.get("reason", "").strip(),
    }
    errors: dict[str, str] = {}

    if cleaned_data["transaction_type"] not in _TRANSACTION_TYPE_LABELS:
        errors["transaction_type"] = "Please choose a transaction type."

    if not cleaned_data["product_id"].isdigit():
        errors["product_id"] = "Please select a product."
    else:
        cleaned_data["product_id"] = int(cleaned_data["product_id"])

    if not cleaned_data["quantity_input"].isdigit():
        errors["quantity_input"] = "Please enter a quantity."
    else:
        cleaned_data["quantity_input"] = int(cleaned_data["quantity_input"])
        if cleaned_data["transaction_type"] == "adjustment":
            if cleaned_data["quantity_input"] < 0:
                errors["quantity_input"] = "New stock quantity cannot be negative."
        elif cleaned_data["quantity_input"] <= 0:
            errors["quantity_input"] = "Quantity must be greater than 0."

    if not cleaned_data["reason"]:
        errors["reason"] = "Please enter a reason."
    elif len(cleaned_data["reason"]) > 255:
        errors["reason"] = "Reason must be 255 characters or fewer."

    return cleaned_data, errors


def apply_stock_transaction(
    product_id: int, transaction_type: str, quantity_input: int, reason: str, employee_id: int
) -> tuple[int, int]:
    """
    Atomically update Catalog.stock_quantity and insert exactly one
    StockHistory row - the two writes always happen together or not at all
    (see Write Operation Pattern in AI_CONTEXT.md). Returns (old_stock,
    new_stock) on success.

    Raises ValueError with a user-facing message, and writes nothing at all,
    if the product doesn't exist or a Stock Out would produce negative
    stock. The current stock is re-read here with FOR UPDATE (not trusted
    from an earlier page load) so two concurrent Stock Out requests for the
    same product can never both succeed and push stock negative.
    """

    if transaction_type not in _TRANSACTION_TYPE_LABELS:
        raise ValueError("Unknown transaction type.")

    with transaction() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT stock_quantity FROM Catalog WHERE id = %s FOR UPDATE;", (product_id,))
            row = cursor.fetchone()
            if row is None:
                raise ValueError("This product could not be found.")
            old_stock = row["stock_quantity"] or 0

            if transaction_type == "stock_in":
                new_stock = old_stock + quantity_input
            elif transaction_type == "stock_out":
                new_stock = old_stock - quantity_input
                if new_stock < 0:
                    raise ValueError(
                        f"Cannot stock out {quantity_input} units - only {old_stock} currently in stock."
                    )
            else:  # adjustment
                new_stock = quantity_input

            quantity_changed = new_stock - old_stock

            cursor.execute("UPDATE Catalog SET stock_quantity = %s WHERE id = %s;", (new_stock, product_id))
            cursor.execute("""
                INSERT INTO StockHistory
                    (ProductID, EmployeeID, TransactionType, OldStock, NewStock,
                     QuantityChanged, Reason, ReferenceType)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
            """, (
                product_id,
                employee_id,
                _TRANSACTION_TYPE_DB_VALUES[transaction_type],
                old_stock,
                new_stock,
                quantity_changed,
                reason,
                _MANUAL_REFERENCE_TYPE,
            ))
        finally:
            cursor.close()

    return old_stock, new_stock
