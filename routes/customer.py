"""
=========================================================
Project : Sridevi Enterprises
File    : customer.py
Purpose : Customer-facing routes.

Author  : Srikar
=========================================================
"""

import re
from math import ceil

from flask import Blueprint, abort, redirect, render_template, request, url_for
from markupsafe import Markup, escape
from services.customer_service import (
    get_featured_products,
    get_home_departments,
    get_popular_brands,
)
from services.enquiry_service import create_enquiry, get_enquiry_product, validate_enquiry
from services.product_service import (
    get_product,
    get_product_count,
    get_product_filters,
    get_products,
    get_related_products,
)
from services.whatsapp_service import (
    build_product_enquiry_url,
    build_whatsapp_url,
    whatsapp_enabled,
)
from config import Config

customer_bp = Blueprint("customer", __name__)

_AVAILABILITY_LABELS = {"in_stock": "In Stock", "on_request": "Available on Request"}
_CHIP_FIELDS = ("department", "category", "brand", "availability")


def _build_active_filter_chips(filters: dict) -> list[dict]:
    """Build removable filter-chip data for the currently active narrowing filters."""

    chips = []
    for field in _CHIP_FIELDS:
        value = filters.get(field)
        if not value:
            continue
        label = _AVAILABILITY_LABELS.get(value, value) if field == "availability" else value
        cleared_filters = dict(filters, **{field: ""})
        chips.append({
            "label": label,
            "remove_url": url_for("customer.products", **cleared_filters),
        })
    return chips


@customer_bp.app_template_filter("highlight_search")
def highlight_search(text, term):
    """Wrap case-insensitive matches of `term` in <mark> tags for the Products page search."""

    if not text or not term:
        return text

    text = str(text)
    pattern = re.compile(re.escape(term), re.IGNORECASE)
    pieces = []
    cursor = 0
    for match in pattern.finditer(text):
        pieces.append(escape(text[cursor:match.start()]))
        pieces.append(Markup("<mark class='search-highlight'>"))
        pieces.append(escape(match.group(0)))
        pieces.append(Markup("</mark>"))
        cursor = match.end()
    pieces.append(escape(text[cursor:]))

    return Markup("").join(pieces)


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
    }
    # v1.0 Sprint 7 (Product Lifecycle Management): a deactivated product
    # must never appear in the customer-facing listing, filters, or search
    # (see AI_CONTEXT.md "Customer Site (IsActive Filtering)"). Kept out of
    # `filters` itself - that dict is also spread into every url_for(...)
    # call below (pagination, sort, chip removal, clear-search) via
    # **filters, and "active" isn't a real user-facing filter choice, so it
    # has no business showing up as a query parameter in those URLs.
    query_filters = dict(filters, status="active")
    per_page = 24
    total_products = get_product_count(query_filters)
    total_pages = max(ceil(total_products / per_page), 1)
    requested_page = request.args.get("page", 1, type=int) or 1
    page = min(max(requested_page, 1), total_pages)
    page_start = max(page - 2, 1)
    page_end = min(page_start + 4, total_pages)
    page_start = max(page_end - 4, 1)
    range_start = (page - 1) * per_page + 1 if total_products else 0
    range_end = min(page * per_page, total_products)

    return render_template(
        "customer/products.html",
        products=get_products(query_filters, page, per_page),
        filter_options=get_product_filters(),
        filters=filters,
        active_filters=_build_active_filter_chips(filters),
        clear_search_url=url_for("customer.products", **dict(filters, search="")),
        page=page,
        page_numbers=range(page_start, page_end + 1),
        total_pages=total_pages,
        total_products=total_products,
        range_start=range_start,
        range_end=range_end,
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
        # "" when no WhatsApp number is configured - the template then
        # renders no WhatsApp button. Points at this site's own redirect
        # route, not wa.me, so the number never appears in the page.
        whatsapp_product_url=(
            url_for("customer.product_whatsapp", product_id=product["id"])
            if whatsapp_enabled() else ""
        ),
    )


def _whatsapp_redirect(target: str):
    """
    Redirect to a wa.me URL, or 404 when WhatsApp is not configured.

    The buttons link here instead of to wa.me directly, so the configured
    number appears only in this redirect's Location header after a click,
    never in page HTML. noindex/nofollow keeps search engines from
    recording the destination; no-store means a changed number takes
    effect on the very next click instead of a cached redirect.
    """

    if not target:
        abort(404)

    response = redirect(target, code=302)
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    response.headers["Cache-Control"] = "no-store"
    return response


@customer_bp.route("/whatsapp")
def whatsapp_chat():
    """Floating WhatsApp button: open a chat prefilled with the default message."""

    return _whatsapp_redirect(build_whatsapp_url(Config.WHATSAPP_DEFAULT_MESSAGE))


@customer_bp.route("/products/<int:product_id>/whatsapp")
def product_whatsapp(product_id):
    """
    Product Details WhatsApp button: open a chat prefilled with this
    product's public name and public page URL only - never price, stock,
    or GST (see services/whatsapp_service.py). Inactive or unknown
    products 404, exactly like product_details().
    """

    if not whatsapp_enabled():
        abort(404)

    product = get_product(product_id)
    if product is None:
        abort(404)

    return _whatsapp_redirect(build_product_enquiry_url(
        product["product_name"],
        url_for("customer.product_details", product_id=product["id"], _external=True),
    ))


@customer_bp.route("/products/<int:product_id>/enquiry", methods=["GET", "POST"])
def product_enquiry(product_id):
    """Display and submit a customer enquiry for a catalog product."""

    product = get_enquiry_product(product_id)
    if product is None:
        return render_template(
            "customer/enquiry_form.html",
            product=None,
            form_data={},
            errors={"form": "This product is no longer available."},
        ), 404

    form_data = {}
    errors = {}
    if request.method == "POST":
        form_data, errors = validate_enquiry(request.form)
        if not errors:
            saved, failure_message = create_enquiry(product_id, form_data)
            if saved:
                return render_template("customer/enquiry_success.html", product=product)
            errors["form"] = failure_message

    return render_template(
        "customer/enquiry_form.html",
        product=product,
        form_data=form_data,
        errors=errors,
    )


@customer_bp.route("/categories")
def categories():
    """Render the premium category browsing page."""

    return render_template(
        "customer/categories.html",
        departments=get_home_departments(),
    )


@customer_bp.route("/contact", methods=["GET", "POST"])
def contact():
    """Display and submit general customer enquiries."""

    form_data = {}
    errors = {}
    if request.method == "POST":
        form_data, errors = validate_enquiry(request.form, require_subject=True)
        if not errors:
            saved, failure_message = create_enquiry(None, form_data)
            if saved:
                return render_template("customer/enquiry_success.html", product=None)
            errors["form"] = failure_message

    return render_template(
        "customer/contact.html",
        form_data=form_data,
        errors=errors,
    )
