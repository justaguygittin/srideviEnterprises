"""
=========================================================
Project : Sridevi Enterprises
File    : department_service.py
Purpose : Department Image Management. DepartmentImages stores presentation
          information only (image, display order, active flag) for each
          Catalog department - Catalog.Department remains the sole source
          of truth for product classification. Rows are matched to Catalog
          departments by DepartmentName (a UNIQUE string), not by a
          foreign key, since Catalog.Department is free text with no id.

Author  : Srikar
=========================================================
"""

from typing import Any

from database.db import execute, fetch_all, fetch_one
from services.image_service import (
    delete_department_image_file,
    department_image_path,
    save_department_image,
)
from werkzeug.datastructures import FileStorage

_PLACEHOLDER_IMAGE = "images/placeholder.png"


def _normalise_department_name(name: str) -> str:
    """
    Canonical comparison key for department names: case-insensitive,
    leading/trailing whitespace ignored.

    This is the single normalization point every DepartmentImages lookup
    and write goes through - a plain Python string comparison (unlike a SQL
    `WHERE DepartmentName = %s`) can't accidentally depend on the column's
    collation, and centralizing it here means future edits, spacing
    differences, or case changes in either Catalog.Department or
    DepartmentImages.DepartmentName can never silently break a match.
    Compare normalized keys only - never compare raw names directly.
    """

    return name.strip().lower()


def get_catalog_department_names() -> list[str]:
    """Return DISTINCT non-empty Department values from Catalog - the source of truth."""

    rows = fetch_all("""
        SELECT DISTINCT Department FROM Catalog
        WHERE Department IS NOT NULL AND TRIM(Department) <> ''
        ORDER BY Department;
    """)
    return [row["Department"] for row in rows]


def _get_canonical_department_names() -> dict[str, str]:
    """Return {normalised_name: canonical Catalog.Department string} for every catalog department."""

    return {_normalise_department_name(name): name for name in get_catalog_department_names()}


def get_department_product_counts(active_only: bool = False) -> dict[str, int]:
    """
    Return {Department: product_count} for every non-empty department in Catalog.

    v1.0 Sprint 7 (Product Lifecycle Management): active_only defaults to
    False, so the Employee Departments module (get_departments_for_management()
    below) keeps showing true total counts, deactivated products included -
    unchanged from before this sprint. get_active_department_cards() below
    explicitly passes active_only=True, since a customer-facing department
    card must never count a product the customer can't actually see.
    """

    active_clause = "AND IsActive = 1" if active_only else ""
    rows = fetch_all(f"""
        SELECT Department, COUNT(*) AS total FROM Catalog
        WHERE Department IS NOT NULL AND TRIM(Department) <> '' {active_clause}
        GROUP BY Department;
    """)
    return {row["Department"]: row["total"] for row in rows}


def _get_department_image_rows() -> list[dict[str, Any]]:
    """Return every DepartmentImages row - the one query every lookup below is built from."""

    return fetch_all("""
        SELECT DepartmentID, DepartmentName, ImageFilename, DisplayOrder, IsActive
        FROM DepartmentImages;
    """)


def _find_department_image_row(department_name: str) -> dict[str, Any] | None:
    """
    Return the DepartmentImages row matching department_name, compared via
    the canonical normalized key rather than an exact SQL `=` (which would
    depend on the column's collation and wouldn't ignore whitespace at all).
    """

    target = _normalise_department_name(department_name)
    for row in _get_department_image_rows():
        if _normalise_department_name(row["DepartmentName"]) == target:
            return row
    return None


def get_departments_for_management() -> list[dict[str, Any]]:
    """
    Return every Catalog department combined with its DepartmentImages row
    if one exists, for the Employee Departments module. A department with
    no configured image yet still appears (with is_configured=False) so
    employees can see, and fill in, every department that needs one.
    """

    department_names = get_catalog_department_names()
    counts = get_department_product_counts()
    configured = {
        _normalise_department_name(row["DepartmentName"]): row
        for row in _get_department_image_rows()
    }

    departments = []
    for name in department_names:
        row = configured.get(_normalise_department_name(name))
        departments.append({
            "department_id": row["DepartmentID"] if row else None,
            "department_name": name,
            "image_path": department_image_path(row["ImageFilename"]) if row else _PLACEHOLDER_IMAGE,
            "display_order": row["DisplayOrder"] if row else 0,
            "is_active": bool(row["IsActive"]) if row else False,
            "is_configured": row is not None,
            "total_products": counts.get(name, 0),
        })

    return departments


def get_department_for_edit(department_name: str) -> dict[str, Any] | None:
    """
    Return one department's current configuration for the Add/Edit Department
    form. Returns None if department_name doesn't normalize-match a real
    Catalog department - the route treats that as 404, since departments
    aren't freely nameable.

    The returned `department_name` is always the canonical Catalog.Department
    string (not whatever casing/spacing the caller passed in), so callers
    that go on to write to DepartmentImages - see upsert_department_image()
    below - never store a non-canonical variant.
    """

    canonical_name = _get_canonical_department_names().get(_normalise_department_name(department_name))
    if canonical_name is None:
        return None

    row = _find_department_image_row(canonical_name)
    counts = get_department_product_counts()

    return {
        "department_id": row["DepartmentID"] if row else None,
        "department_name": canonical_name,
        "image_path": department_image_path(row["ImageFilename"]) if row else _PLACEHOLDER_IMAGE,
        "display_order": row["DisplayOrder"] if row else 0,
        "is_active": bool(row["IsActive"]) if row else False,
        "is_configured": row is not None,
        "total_products": counts.get(canonical_name, 0),
    }


def upsert_department_image(
    department_name: str, display_order: int, is_active: bool, image_file: FileStorage | None
) -> None:
    """
    Create or update the DepartmentImages row for one Catalog department.

    Standard write-operation pattern (see AI_CONTEXT.md), scaled to a single
    table: save the new file first (if one was submitted), write the DB row,
    and only delete the old file afterwards, on success - matching
    update_product()'s established refinement so a mid-write failure can
    never destroy a still-referenced image.

    DepartmentName is UNIQUE at the database level and this function only
    ever targets an existing Catalog department name (validated by the
    caller via get_department_for_edit()/get_catalog_department_names()),
    so this can never create a duplicate department entry. The "existing
    row" lookup is normalized (see _find_department_image_row()) so a
    pre-existing row with slightly different casing/spacing is still found
    and updated in place, rather than a second, effectively-duplicate row
    being inserted.
    """

    existing = _find_department_image_row(department_name)

    if existing is None and image_file is None:
        raise ValueError("An image is required to set up a new department.")

    new_filename = save_department_image(image_file) if image_file else None

    try:
        if existing:
            if new_filename:
                execute("""
                    UPDATE DepartmentImages SET ImageFilename = %s, DisplayOrder = %s, IsActive = %s
                    WHERE DepartmentID = %s;
                """, (new_filename, display_order, is_active, existing["DepartmentID"]))
            else:
                execute("""
                    UPDATE DepartmentImages SET DisplayOrder = %s, IsActive = %s WHERE DepartmentID = %s;
                """, (display_order, is_active, existing["DepartmentID"]))
        else:
            execute("""
                INSERT INTO DepartmentImages (DepartmentName, ImageFilename, DisplayOrder, IsActive)
                VALUES (%s, %s, %s, %s);
            """, (department_name, new_filename, display_order, is_active))
    except Exception:
        if new_filename:
            delete_department_image_file(new_filename)
        raise

    if existing and new_filename and existing["ImageFilename"]:
        delete_department_image_file(existing["ImageFilename"])


def get_active_department_cards() -> list[dict[str, Any]]:
    """
    Return configured, active departments for the customer website, ordered
    for display - the permanent replacement for the old hardcoded
    _CATEGORY_IMAGES lookup. A department only appears once an employee has
    uploaded an image and enabled it (see Employee Departments module) -
    deliberate: the Enable/disable control has to mean something.

    Returns the same shape (`Department`, `total_products`, `image_path`)
    the old get_home_departments() returned, so its two customer-facing
    templates (the homepage slider and the standalone /categories page)
    needed no structural changes.

    `Department` is always resolved to the canonical Catalog.Department
    string via normalized matching, never DepartmentImages.DepartmentName
    verbatim - this matters because that value flows straight into the
    "Browse" link's `?department=` query param, which the Products page
    filters with an exact match against Catalog.Department.
    """

    rows = fetch_all("""
        SELECT DepartmentName, ImageFilename FROM DepartmentImages
        WHERE IsActive = TRUE
        ORDER BY DisplayOrder, DepartmentName;
    """)

    canonical_names = _get_canonical_department_names()
    counts = get_department_product_counts(active_only=True)

    cards = []
    for row in rows:
        key = _normalise_department_name(row["DepartmentName"])
        canonical_name = canonical_names.get(key, row["DepartmentName"])
        cards.append({
            "Department": canonical_name,
            "total_products": counts.get(canonical_name, 0),
            "image_path": department_image_path(row["ImageFilename"]),
        })

    return cards
