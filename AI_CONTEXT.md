# AI_CONTEXT.md

# Sridevi Enterprises
Current Version: v0.8.0 — Customer Experience (in progress)

---

## How This Document Is Organized

1. **Project Overview** — what this is, scope, technology stack
2. **Implemented Features** — what is built today, and how each feature behaves
3. **Architecture & Conventions** — layered architecture, RBAC model, data conventions, coding/UI rules that apply to all future work
4. **Development Workflow** — testing policy, Git workflow
5. **Deployment Notes** — deployment target, lessons learned, what's been prepared
6. **Planned Roadmap** — v0.8.0 onward, not yet built

---

# 1. Project Overview

Sridevi Enterprises is a Flask-based showroom management system for a furniture and home appliances business.

The application consists of two major modules:

1. Customer Website
2. Employee Management Portal

The Employee Portal was the v0.7.0 development priority and is now feature-complete (see Implemented Features). The objective is to complete a fully functional demonstration build before expanding into advanced business modules.

## Current Scope

The current project is focused solely on the Sridevi Enterprises showroom application.

The application must become a complete, deployable standalone system before any integration with external projects is considered.

Receipt Generator integration and other shared-system work (shared authentication, inventory, invoices) are intentionally out of scope until after v1.0.0 — see Planned Roadmap > Future Roadmap for details.

## Technology Stack

Backend
- Python 3
- Flask
- MariaDB
- mysql-connector-python

Frontend
- HTML5
- Bootstrap 5
- CSS3
- JavaScript

Template Engine
- Jinja2

Deployment
- HostCare
- Passenger WSGI

Version Control
- Git
- GitHub

---

# 2. Implemented Features

## Customer Website

✓ Home Page (see Homepage below for section detail)
✓ Products Page (search, filters, pagination)
✓ Product Details Page
✓ Categories Page (see Categories Page below for section detail)
✓ Search
✓ Contact Page (general enquiry form)

Not yet built (see Planned Roadmap):
- Product Comparison — `/compare` is currently a placeholder route

### Homepage

The homepage no longer displays categories as a static grid — it uses a Featured Categories Slider.

Sections, in order:
- Hero
- Quick Actions
- Featured Categories Slider
- Featured Products
- Popular Brands
- About Section
- Location Map

The dedicated Categories page (`/categories`) is separate and unaffected by the slider — see Categories Page below.

The Featured Products section displays 8 products from `get_featured_products()` (`services/customer_service.py`) — a `LIMIT 8` query, randomly ordered (`ORDER BY RAND()`) for variety on each page load, not a fixed "first 8 by id". It uses the homepage's own `.product-card` markup/styling (distinct from the Products page's `.catalog-product-card`) and ends with a centered "View All Products" button linking to `/products`. No backend changes were needed — the query already returned exactly 8 products.

Regression tested: Homepage, Products page, Categories navigation, Mobile, Desktop, no JS console errors, no route changes.

### Categories Page

`/categories` is a premium, standalone category browsing page — not a variant of the homepage slider. It reuses `get_home_departments()` (`services/customer_service.py`), the same data source as the homepage Featured Categories slider, so category names, product counts, and images stay consistent across both. No new service function or API endpoint was introduced.

Sections, in order:
- Hero (heading, description, category search input)
- Category Grid — large image cards showing department name, product count, and an Explore button

Category search is client-side only (`initCategorySearch()` in `static/js/main.js`): it filters the already-rendered `.category-grid-card` elements by name as the user types, and toggles an empty-state message when nothing matches. No page reload, no new route.

Each card's Explore button links to `/products?department=<Department>` — the same existing product-listing route and query parameter the homepage slider already uses, so no new listing template was needed.

Styling lives in `static/css/categories.css` (new `.categories-page-hero`, `.categories-search`, `.category-grid`, `.category-grid-card` rules), appended alongside the existing homepage slider rules in the same file without modifying them. Grid is mobile-first: 1 column by default, expanding to 2 / 3 / 4 columns at wider breakpoints. Cards use a hover lift (shadow + translateY), an image zoom, and a gradient overlay on hover.

Both the navbar's and footer's "Categories" links now point to `url_for('customer.categories')`.

#### Navbar Active-Page Highlighting

`templates/components/navbar.html` now sets the `active` class per link by comparing `request.endpoint` against each route's endpoint (e.g. `request.endpoint == 'customer.categories'`), instead of hardcoding `active` on Home. This was a pre-existing gap (previously Home always showed active, regardless of the current page) surfaced while verifying the Categories page's active nav state, and is now correct on every customer page (Home, Products, Categories, Contact). Compare has no route yet, so it never highlights.

#### Category Image Fallback

`_resolve_category_image()` in `services/customer_service.py` now checks that a mapped category image file actually exists **and is non-empty** before using it; otherwise it falls back to the placeholder. This fixed a real bug found while verifying image fallbacks: `electronics.jpg`, `furniture.jpg`, and `miscellaneous.jpg` under `static/images/categories/` are committed as 0-byte stub files, which the browser can't decode — they rendered as broken images instead of the placeholder. Since `get_home_departments()` is shared, this fix also corrects the homepage Featured Categories slider, which had the same broken images. The underlying stub image files still need to be replaced with real photography; until then, all categories correctly show the placeholder.

### Products Page — Filtering Experience

`/products` uses a single reusable filter form — `templates/customer/products.html`'s `.filter-panel` inside a Bootstrap 5 responsive off-canvas (`offcanvas-lg`) — that renders as a sticky left sidebar at the `lg` breakpoint (≥992px) and collapses into a slide-in drawer (opened via a "Filters" toggle button) below it. The same markup serves both layouts; nothing is duplicated between desktop and mobile.

Each filter (Department, Category, Brand, Availability, Sort By) is a collapsible group (Bootstrap `collapse`, expanded by default) with its native `<select>` unchanged from the prior implementation — no new filter dimensions, no new query parameters, no backend or `services/product_service.py` changes. Sort was moved from the old top-toolbar dropdown into the filter panel as its own group (per the sprint's explicit filter list); it still auto-submits on change via `onchange="this.form.submit()"`, while the other filters require "Apply Filters".

**Note:** the sprint spec listed Department/Brand/Availability/Sort as the filter set; Category was kept as a fifth group since it was already a working filter (existing `filter_options.categories` / `category` query param) — dropping it would have removed functionality that wasn't asked to be removed. Flag if this should instead be trimmed to match the spec exactly.

Active filters (Department, Category, Brand, Availability — not search or sort) render as removable chips above the product grid (e.g. "Furniture ×"). Chip removal URLs and the mobile filter-count badge are computed server-side in `routes/customer.py`'s `_build_active_filter_chips()`, reusing the same `filters` dict and `customer.products` route — no new route or API. Product cards, pagination, and the search bar are unchanged from the prior implementation.

**Implementation gotcha:** Bootstrap 5.3.7's responsive offcanvas only works with the size-scoped class alone (`offcanvas-lg`) on the container; adding the base `.offcanvas` class alongside it (as most examples show) causes the element to stay permanently hidden at all breakpoints, because the unconditional `.offcanvas` rule (visibility:hidden, transform:translateX(-100%)) is not overridden by the `.offcanvas-lg` responsive breakpoint rules in this build. Confirmed by inspecting the actual downloaded CDN stylesheet — the `@media (min-width:992px){.offcanvas-lg{...}}` block never resets `visibility`/`transform`. Use `offcanvas-lg` (or `offcanvas-{sm|md|xl|xxl}`) alone, never combined with plain `offcanvas`, for responsive sidebar/drawer patterns in this codebase.

**Dev note:** `FLASK_DEBUG=False` in `.env` means `TEMPLATES_AUTO_RELOAD` is off and the Werkzeug reloader isn't watching files — template and route edits require restarting the `flask-dev` server to take effect, they will not hot-reload.

### Products Page — Search Experience

`/products`'s search bar (`.search-bar` in `templates/customer/products.html`) was rebuilt visually only — same `GET` form, same `search` query param, same `get_products()`/`_build_product_filters()` LIKE-query backend in `services/product_service.py`. It now has an inset search icon, a larger input, and (when `filters.search` is set) an inline clear (×) link — all pure CSS/Jinja, no JavaScript added.

**Search persistence** was already correct going into this sprint (a side effect of the filter-chip work): every filter form, the sort auto-submit, pagination links, and filter-chip removal links already round-trip the full `filters` dict, including `search`. This sprint didn't need to change that — it was verified across all of those interactions (filters, sort, chip removal, pagination) rather than re-implemented.

**Search highlighting**: `routes/customer.py` registers a Jinja filter, `highlight_search(text, term)` (`@customer_bp.app_template_filter`), applied only in `products.html` to `product.product_name` and `product.brand` — so it only affects the Products page, not Product Details or anywhere else. It does a case-insensitive substring match on the existing `filters.search` term already in the template context — no new query, no DB change. Matches are wrapped in `<mark class="search-highlight">`. Each raw text segment is escaped individually via `markupsafe.escape()` before being reassembled as `Markup`, rather than escaping the whole string first and matching against escaped output — this avoids mismatches when the product text itself contains HTML-special characters (e.g. catalog entries like "Tv & Entertainment Units"). Verified against an XSS payload (`<script>...`) as the search term: Jinja's default autoescaping renders it as inert text everywhere it's echoed back (input value, empty-state heading).

**Clear-search URL**: `routes/customer.py`'s `products()` view computes `clear_search_url = url_for("customer.products", **dict(filters, search=""))` once per request and passes it to the template — reused by both the inline × button and the empty state's "Clear Search" button, so clearing search always preserves every other active filter/sort and resets pagination (no `page` param is ever carried by these links, so it naturally defaults back to page 1).

**Empty state**: replaced the one-line "No products match..." with an icon, a heading (quotes the search term when one was used), a suggestions list (spelling, filters, Categories link, clear search — each shown only when relevant), and action buttons ("Clear Search" / "Clear All Filters", each shown only when applicable). Same `{% for %}...{% else %}` block as before, no new route.

Product cards, pagination, and the filter sidebar/drawer from the previous sprint are unchanged.

### Products Page — Card Polish

**Shared-component constraint:** `.catalog-product-card` and its child classes (`.catalog-product-brand`, `.catalog-product-pricing`, `.catalog-product-card-body`, `.catalog-product-card h2/h3`, the direct-child `img` rule) are reused verbatim by the "Similar Products" section on **both** `customer/product_details.html` and `employee/product_details.html`, and `.catalog-product-brand`/`.catalog-product-pricing` are also used by the main product-info panel on those same pages. Editing those shared rules in place would have visually changed Product Details, which was explicitly out of scope for this sprint. So none of those base declarations were touched — every new/changed rule is scoped under a new additive modifier class, `product-grid-card`, added only to the `<article>` in `products.html`'s catalog loop. Verified in-browser: the Similar Products cards on Product Details still render the old flush `<img>` (no wrapper), no availability badge, and the original (non-uppercase, non-bold) brand typography — confirming zero bleed-through.

**Image presentation:** each card's `<img>` is now wrapped in `.catalog-product-image-wrap` (fixed 208px height, `overflow:hidden`, light gray background) so `.catalog-product-image` can `transform: scale(1.06)` on card hover without the zoomed image escaping the card's rounded corners. `object-fit: contain` was kept (not switched to `cover`/cropping) — deliberate: several catalog photos are furniture/appliance product shots at varying aspect ratios, and cropping risks cutting off part of the product in a showroom context where the full silhouette matters more than filling the frame edge-to-edge. `loading="lazy"` was added for smoother below-the-fold loading (no JS). When `product.image_path` is the shared placeholder (`images/placeholder.png` — same literal string `services/product_service.py`'s `_PLACEHOLDER_IMAGE` already returns), the wrapper gets a `--placeholder` modifier that dims the image slightly (`opacity: .82`) to visually de-emphasize it as "not a real photo" — a template-only check against data already in the `product` dict, no backend change.

**Availability badge:** replaces the old plain-text availability line with a colored pill + dot (`.availability-badge`, green `--in-stock` / amber `--on-request`), driven entirely by the existing two-state `product.availability` string (`"In stock"` / `"Available on request"` from `services/product_service.py`'s `CASE WHEN stock_quantity > 0...` query) — no new field, no third "Limited Stock" state invented, per the sprint's explicit constraint.

**Typography/hierarchy:** reordered to Brand (small, uppercase, bold, letter-spaced) → Product Name → Department/Category meta → Availability badge → "Contact for Pricing" → View Details button, so the badge (more actionable for a showroom than the boilerplate pricing note) reads before it. The CTA button gained a trailing arrow icon and a subtle box-shadow on card hover; its Bootstrap `.btn-primary` class and click behavior (same `href` to `customer.product_details`) are unchanged.

**Equal card heights** continue to work exactly as before (Bootstrap's `.row` flex + `.h-100` on the card + `margin-top: auto` on the button) — verified in-browser that a 4-card row with mismatched brand/name lengths still renders identical card heights.

### Products Page — Pagination & Grid Polish

**Results summary**: the toolbar's product count was replaced with a range-aware summary — "Showing 25–48 of 314 products" when there's more than one page, or "Showing N products" when everything fits on one page (avoids a redundant "1–7 of 7"). `range_start`/`range_end` are computed in `routes/customer.py`'s `products()` view as pure arithmetic from values already there (`page`, `per_page`, `total_products`) — no new query.

**Pagination controls**: restyled as individually-rounded pill buttons with a gap (overriding Bootstrap's default joined-border pagination look), themed to the site's `#1E4FA3` blue for the active page, all scoped under the existing `.product-pagination` wrapper — this page is the only place in the customer site using Bootstrap's `.pagination`/`.page-item`/`.page-link` classes (the employee portal's pagination at `templates/employee/products.html` is unrelated hand-rolled markup with its own inline styles, not Bootstrap pagination, so there was no shared-component risk here, unlike the card-polish sprint). Previous/Next gained chevron icons; their text label is hidden below the `sm` breakpoint (`d-none d-sm-inline`) so they collapse to icon-only touch targets on phones without wrapping. Touch targets are 42px (44px under 576px).

**Accessibility**: the active page link gets `aria-current="page"`; disabled Previous/Next links get `aria-disabled="true" tabindex="-1"` (their `href` is left exactly as the existing clamped `url_for(...)` value — only the reachability was fixed, not the URL) so a keyboard user can no longer Tab onto and activate a link that Bootstrap only *visually* disables via `pointer-events: none` (which doesn't block keyboard activation on its own). Verified: 6 of the 7 pagination links are keyboard-focusable on page 1 (the disabled Previous is correctly excluded).

**Scroll-to-grid anchor**: pagination links append a `#product-grid` fragment (id placed on `.product-list-toolbar`, with `scroll-margin-top: 100px` so the sticky navbar doesn't cover it) so clicking a page number lands the user back at the results toolbar instead of the very top of the page. Pure HTML fragment + CSS, no JavaScript. Only pagination links carry the fragment — normal navigation to `/products` (navbar, homepage, category cards) is unaffected. Fragments aren't sent to the server, so this doesn't change the server-visible URL/query contract.

**Out-of-range pages**: `?page=999` (or `?page=abc`, `?page=-5`) needed no backend changes — the existing `page = min(max(requested_page, 1), total_pages)` clamp in `products()` already handles all of these gracefully (Werkzeug's `type=int` on `request.args.get` also already silently falls back to the default on non-numeric input). Verified in-browser: `?page=999&department=Furniture` (only 4 valid pages) renders page 4 with a correct results summary and active pagination state, no broken layout.

No changes to `services/product_service.py`, product cards, filters, or search this sprint.

### Product Details Page — Premium Showroom Experience

`templates/customer/product_details.html` was restyled to read as a showroom hero (Brand → Name → Meta → Availability → Pricing note → Model → CTA, then Specifications, then Similar Products) instead of a flat stack of lines. No route or service changes — same `get_product()`/`get_related_products()` data, same `customer.product_enquiry` CTA destination.

**Availability badge**: the plain-text `.product-detail-availability` line was replaced with the same `.availability-badge`/`--in-stock`/`--on-request` markup introduced on Product Cards, for visual consistency across the site. Only the main hero panel changed — the Similar Products cards on this page were left untouched (still `.catalog-product-card`, no badge), per the sprint's explicit "review spacing only, do not redesign the shared cards" constraint.

**Specifications**: `.specifications-list` (inside `.product-details-page` only) is now a two-column CSS grid at `≥768px`, collapsing to one column below that — pure CSS, no template/query changes. `.product-facts` (the Model row) and the employee portal's identical `.specifications-list` markup are untouched, since the two-column rule is scoped under the customer-only `.product-details-page` ancestor.

**No Description field**: the `Catalog` table has no description column (verified against `database/schema/001_create_catalog.sql`), so the "Description" step in the requested scan order was intentionally skipped rather than fabricated. Flag if a future schema change should add one.

**Component isolation**: `product_details.html` shares several CSS classes with `templates/employee/product_details.html` (`.product-main-image`, `.product-gallery`, `.product-facts`, `.specifications-section`, `.related-products-section`, `.catalog-product-card`, `.back-link`) and, less obviously, with `templates/customer/enquiry_form.html` and `enquiry_success.html` (both also wrap their content in `.product-details-page`). Every new rule was scoped to avoid touching either: page-unique elements (main image, gallery, spec grid, section spacing) are scoped under the customer-only `.product-details-page` ancestor; elements that recur elsewhere on the *same* page (hero brand/pricing text, which also appears in this page's own Similar Products cards) are scoped under two new wrapper classes, `.product-hero-media` and `.product-hero-info`, added only around the hero columns; and the back-link (which also exists on `enquiry_form.html`, nested in the same `.product-details-page` wrapper) got its own dedicated `.pd-back-link` class rather than relying on `.product-details-page .back-link`, which would have leaked a margin change onto the enquiry page. Verified in-browser: `enquiry_form.html`'s back-link has no `pd-back-link` class and 0px margin, confirming zero bleed.

**Image gallery**: the thumbnail row is skipped entirely when a product has only its one placeholder image (`{% if product.images|length > 1 %}`) — previously it rendered a duplicate thumbnail identical to the main image. Thumbnails remain non-interactive (no click-to-swap) — that behavior is deliberately deferred to the separate "Product Image Gallery" roadmap item, not part of this sprint. The gallery row also gained `overflow-x: auto` (scoped to `.product-details-page`) so it won't overflow once products have multiple images; not yet exercised by real data — no product in the current catalog has more than one image.

**Placeholder image treatment**: the main image now gets the same `--placeholder` opacity dimming (0.82) introduced for Product Cards, plus corrected alt text ("Image not available" instead of the product name) when `product.images[0].is_placeholder` is true, and a `#F5F7FA` background (matching the card image wrap) instead of plain white.

**CTA**: the existing "Send Enquiry" button (same href, same text) was wrapped in `.product-hero-cta` with a top border and extra spacing to read as a distinct action area, and goes full-width on mobile. No new buttons were introduced.

Regression tested: Homepage, Categories, Products (search + pagination + filters), Product Details (products with/without specifications, with/without real images), Enquiry Form/Success pages, Employee Portal's shared CSS classes confirmed unaffected by grep + computed-style checks, mobile/tablet/desktop viewports, no console or server errors.

### Product Details Page — Image Gallery Experience

Thumbnail click-to-swap was implemented on `templates/customer/product_details.html`, completing the "Product Image Gallery" roadmap item. This is customer-only — `templates/employee/product_details.html` was intentionally left untouched (see below).

**Markup**: each gallery thumbnail is now a `<button type="button" class="product-gallery-thumb">` wrapping the existing thumbnail `<img>`, instead of a bare `<img>`. The button carries `data-image-src`, `data-image-alt`, and `data-is-placeholder` (mirroring the same placeholder-alt logic already used for the hero image), plus an `aria-label` ("View image N of TOTAL"). The inner `<img>` gets an empty `alt` since the button's `aria-label` already announces it — this avoids double-announcing the same information to screen readers. The hero `<img>` gained `id="product-hero-image"` as the swap target. The `{% if product.images|length > 1 %}` guard around the whole gallery strip (from the previous sprint) is unchanged, so placeholder-only and single-image products still show no thumbnail strip at all.

**Behavior**: `initProductGallery()` in `static/js/main.js` (added to the `DOMContentLoaded` init list alongside `initFeaturedCategoriesSliders()` / `initCategorySearch()`, following the same pattern) wires a click listener per thumbnail. On click: active state moves to the clicked thumbnail (`is-active` class + `aria-current="true"`, removed from the rest), the hero image briefly fades out via a CSS class, then after 150ms its `src`/`alt`/placeholder-dimming class are swapped and the fade class is removed. Because native `<button>` elements are used (not `<img>` or `<div>` with manual `tabindex`/`keydown` handling), Enter/Space activation and Tab-focusability are guaranteed by the browser for free — no custom keyboard code was written, per the "lightest solution possible" constraint.

**Styling**: new rules are `.product-gallery-thumb` (button reset: no border/background/padding, `cursor: pointer`), `.product-gallery-thumb.is-active` (blue box-shadow ring + `scale(1.05)`), `.product-gallery-thumb:hover:not(.is-active)` (neutral gray ring), and `.product-gallery-thumb:focus-visible` (blue outline) — all new classes, so the pre-existing `.product-gallery img` sizing/border rule (shared with the Employee Portal) still applies unchanged to the thumbnail images themselves. The hero's fade transition (`.product-details-page .product-main-image { transition: opacity 150ms ease }` / `.is-fading { opacity: 0 }`) is scoped under `.product-details-page`, so the Employee Portal's own `.product-main-image` (no gallery interactivity there) is unaffected.

**Component isolation**: confirmed via grep that `product-gallery-thumb` and `product-hero-image` appear only in `templates/customer/product_details.html` — the Employee Portal's product details page (which has its own image-management UI: per-thumbnail delete buttons, no click-to-swap) was not modified. Employee-side thumbnail swap was explicitly out of scope for this sprint.

**Out of scope, deliberately not built**: lightbox, fullscreen, zoom, swipe/pinch gestures, videos, 360° viewer, image downloads — per the sprint's constraints.

Regression tested against a real 4-image product: hero swap, active-thumbnail state, mobile (375px, thumbnails fit on one row, no overflow), tablet (768px), desktop, placeholder-only product, single-image product, Homepage, Categories, Products (search + filters + sort + pagination combined), Enquiry form (back-link margin isolation still holds), Employee Portal shared classes (confirmed via grep, no bleed-through). No console or server errors.

**Tooling note**: keyboard Enter/Space activation was verified structurally (native `<button>` semantics guarantee this in any real browser) rather than via the automated browser tool's synthetic key dispatch, which was confirmed unable to trigger click activation even on an unrelated pre-existing Bootstrap button (the navbar toggler) — a tool limitation, not a product defect.

## Employee Portal

✓ Employee Login
✓ Session Management
✓ Logout
✓ Protected Routes
✓ RBAC (see Architecture & Conventions)
✓ Employee Dashboard
✓ Product Listing (search, filters, pagination)
✓ Product Details
✓ Add Product
✓ Upload Product Images
✓ Edit Product
✓ Replace Product Images
✓ Delete Product Images (Admin)
✓ Delete Product (Admin)

This completes the Employee Product Management lifecycle: Add, Edit, Replace/Delete Images, and Delete Product all exist and share the same transaction and image-handling infrastructure (see Write Operation Pattern).

### Add Product

A product must never exist without an image.

Workflow: Create Product → Generate ProductID → Upload Minimum One Image → Save

Validation: Minimum Images 1, Maximum Images 10

### Edit Product

Workflow: Open Product Details → Click Edit Product (Employee or Admin) → Edit product fields and specifications → Replace or add images → Save → Return to Product Details

Routes: `GET/POST /employee/products/<id>/edit`

Reuses `product_form.html` (Add and Edit share one template), and `validate_product_form()` / `validate_specifications()` unchanged from Add Product. See Write Operation Pattern for `update_product()`'s transaction handling and its file-cleanup refinement for replaced images.

Specifications are fully replaced on every save (existing rows deleted, submitted rows re-inserted) rather than diffed row-by-row, since spec rows have no stable identity in the form.

### Product Image Management

Employee can:
- Add new images to an existing product
- Replace an existing image (same slot, new file)

Admin can additionally:
- Delete an individual product image

A product's last remaining image cannot be deleted (server-enforced in `services/product_service.py:delete_product_image`), matching the rule that a product must never exist without an image.

Routes: `POST /employee/products/<id>/images/<image_id>/delete` (Admin only)

Image validation, storage, and deletion all go through `services/image_service.py` — no upload or filesystem logic is duplicated elsewhere.

### Product Deletion

Deleting a product is Admin only. Employees never see the Delete Product control and are refused with 403 if the route is called directly.

Workflow: Product Details (Admin) → Click Delete Product (confirmation required) → Delete ProductDetails, ProductImages, and Catalog rows in one transaction → Commit → Delete the product's upload folder → Redirect to Products List

Route: `POST /employee/products/<id>/delete` (Admin only)

Confirmation is a plain browser `confirm()` dialog on the delete form — the same lightweight pattern already used for Delete Product Image, no new UI component was introduced.

Filesystem deletion (the upload folder) happens only AFTER the database transaction commits, never before or during — see Write Operation Pattern.

---

# 3. Architecture & Conventions

## Layered Architecture

The project follows a layered architecture:

Routes → Services → Database Helper → MariaDB

Rules:

Routes
- Handle requests
- Return responses
- Never contain SQL

Services
- Business logic
- Validation
- SQL Queries

Database (`database/db.py`)
- Execute SQL
- Return results
- No business logic

Never bypass this architecture.

## Write Operation Pattern

Any feature that writes to more than one table, or combines a database write with a filesystem write (e.g. product images), must follow this sequence:

Validate → Begin Transaction → Database Write → Filesystem Write → Database Metadata → Commit

On any failure: Rollback Database → Delete Uploaded Files → Return Error

Use `database/db.py`'s `transaction()` context manager (yields a connection, commits on success, rolls back on any exception). Keep all SQL and orchestration in the service layer; `database/db.py` stays mechanical only.

First applied in Add Product (`services/product_service.py:create_product`, `services/image_service.py`).

Refinement used by Edit Product (`services/product_service.py:update_product`) and Delete Product (`services/product_service.py:delete_product`): when a write replaces or removes an existing file, perform the filesystem change only AFTER the transaction commits, never before. On failure, only files newly written during this request are cleaned up; existing files are untouched, so a mid-write failure can never destroy a still-referenced image.

## Role-Based Access Control (RBAC)

### Roles

Three user roles exist: Customer, Employee, Admin. No additional roles should be introduced unless explicitly approved.

### Customer Permissions

Customers can: Browse website, View products, View product details, Search products, Compare products, Submit enquiries.

Customers cannot: Access employee portal, Edit products, Manage data.

### Employee Permissions

Employees can: Login, Access dashboard, View products, Add products, Edit products, Upload product images, View customer enquiries.

Employees cannot: Delete products, Delete product images, Manage users, Access admin settings.

### Admin Permissions

Admins have unrestricted access — everything an Employee can do, plus: Delete products, Delete product images, Manage employees, Manage users, Future system administration.

### Authorization Rules

Every protected route must validate user role.

- Customer Routes: Public
- Employee Routes: Employee, Admin
- Admin Routes: Admin only

Never rely on hidden navigation buttons for security. Every route must verify permissions.

### Authorization vs. Job Designation

`Users.Role` represents permission groups only. Allowed values: Customer, Employee, Admin.

`Employees.Designation` represents the employee's job title (examples: Administrator, Manager, Sales Executive, Accountant, Warehouse Staff) — for display and business information only. Designation must never be used for authorization. RBAC is based solely on `Users.Role`.

## Business Rules

Financial information must never appear in the customer website or the employee portal.

Do NOT expose: Purchase Cost, Selling Price, GST, Profit, Margins, Supplier Cost.

The website is a digital showroom, not an e-commerce website.

## Data & Storage Conventions

### Primary Tables

Users, Catalog, ProductImages, Enquiries. Additional tables should follow existing naming conventions.

### Product-to-Image Relationship

Images are NOT stored inside Catalog.

Catalog.ProductID → ProductImages (ImageID, ProductID, ImageURL, UploadDate). One Product → Many Images.

### Category Images

Categories should never have dedicated images. Instead, each category automatically displays one representative image from a product belonging to that category. No CategoryImages table should be created.

### Image Storage

Images should be stored inside `static/uploads/products/`.

Recommended structure: `static/uploads/products/<ProductID>/image1.jpg`, `image2.jpg`, ...

Database stores only relative paths.

## UI Guidelines

Theme: Primary `#1E4FA3`, Secondary `#1565A0`.

Keep UI clean. Keep Bootstrap consistent. Avoid unnecessary custom CSS.

## Coding Standards

Keep functions small. Reuse existing services. Avoid duplicate SQL. Avoid duplicate templates. Reuse components whenever possible. Prefer extending existing code instead of rewriting it. Preserve backward compatibility. Do not introduce breaking changes without approval.

## Component Isolation

Shared UI components must never be modified directly if they are reused across multiple pages with different design goals.

Instead:

- extend with modifier classes

- keep shared base styles stable

- scope page-specific styling to additive classes

Example:

.catalog-product-card

↓

.product-grid-card

## Implementation Note

Fragment identifiers (#product-grid) are intentionally used instead of JavaScript scrolling.

Reason:

- Works without JavaScript.
- Preserves browser behavior.
- Improves accessibility.
- Easier to maintain.

## Shared Design Language

Availability badges are the canonical visual indicator of product status.

Use the same badge component consistently across:

- Product Cards
- Product Details

Future pages should reuse this component instead of introducing new status styles.

## Gallery Pattern

Product galleries intentionally use native HTML buttons.

Reasons:

- keyboard accessibility
- browser semantics
- screen reader compatibility
- minimal JavaScript

---

# 4. Development Workflow

## Testing Policy

Every feature must be fully functional before starting the next one.

Do not commit: Placeholder pages, Dummy buttons, Half implemented features.

Every completed milestone should be manually testable.

## Git Workflow

The AI must never execute or assume Git commits.

At the end of each completed milestone:
- Summarize all changes.
- Suggest a commit title.
- Suggest a detailed commit description.
- Wait for user approval.

The user performs all Git operations manually.

---

# 5. Deployment Notes

Deployment target: HostCare, Passenger WSGI.

## Deployment Preparation (v0.8.0)

`.env.example` added, `ProxyFix` applied in `app.py` for HostyCare's TLS-terminating proxy, the unauthenticated `/routes` debug endpoint gated behind `Config.DEBUG`, and `DEPLOYMENT.md` written.

## Deployment Lessons (v0.8.0)

Production deployment uncovered schema drift between the local development database and HostyCare.

Root cause: Production database created from an outdated schema.

Resolution: Updated HostyCare database to match the canonical local schema. Verified all customer routes successfully.

Rule: The canonical database schema is the schema stored under `database/schema/`. Any deployment must create the database from these schema files. Never manually modify production schema without reflecting the changes back into version control.

---

# 6. Planned Roadmap

Current focus: deploy a fully functional standalone system to HostCare (v0.8.0 Phase 1) with both the Customer Website and Employee Portal operating reliably, then improve the customer experience and harden for production (Phases 2–3), followed by Employee Customer Management (v0.9.0) and Employee Enquiry Management (v0.9.5).

## v0.7.0 — ✅ COMPLETE

Employee Product Management. See Implemented Features for full detail.

## v0.8.0 — Deployment & Customer Website

### Phase 1 – Production Deployment

□ HostCare Deployment
□ Passenger Configuration Validation
□ Production Environment Validation
□ Static File Validation
□ Upload Directory Validation
□ HTTPS Configuration
✓ Deployment Documentation

Remaining Phase 1 items require an actual HostyCare deployment and live verification (see Milestone 1.5 in the v0.8.0 plan) before they can be checked off. See Deployment Notes for what's already been prepared.

### Phase 2 – Customer Experience

#### Homepage
✓ Featured Categories Slider
✓ Featured Products
✓ View All Products CTA
✓ Popular Brands
✓ Responsive Homepage Polish

#### Categories
✓ Premium Categories Page
✓ Live Category Search
✓ Responsive Category Grid

#### Products
✓ Filtering Experience
✓ Search Experience
✓ Product Card Polish
✓ Pagination Polish
✓ Product Details Improvements
✓ Product Image Gallery

### Phase 3 – Production Hardening

□ Logging
□ Custom 403 / 404 / 500 Pages
□ CSRF Protection
□ Session Hardening
□ Automated Test Suite
□ Deployment Verification

## v0.9.0 — Employee Customer Management

□ Customer List
□ Customer Details
□ Customer Search
□ Customer Notes
□ Customer Management Dashboard

## v0.9.5 — Employee Enquiry Management

Customer:
□ Submit Product Enquiry
□ Contact Form
□ Enquiry Tracking

Employee:
□ View Enquiries
□ Update Status
□ Search & Filters
□ Dashboard Widgets

## v1.0.0 — Sridevi Enterprises Demonstration Release

Customer Website:
□ Complete Product Experience
□ Search
□ Categories
□ Product Gallery
□ Product Details
□ Enquiry System

Employee Portal:
□ Product Management
□ Customer Management
□ Enquiry Management

System:
□ Responsive UI
□ Production Security
□ Automated Testing
□ Documentation
□ Stable Deployment

## Future Roadmap (Post v1.0.0)

Receipt Generator Integration — remains an independent project until after Sridevi Enterprises reaches a stable v1.0.0 release.

Possible future work:
- Shared Product Catalog
- Shared Authentication
- Shared Inventory
- Invoice Integration
- Analytics
- Multi-Branch Support

## Future Scalability Improvements

These enhancements are intentionally deferred until the product catalog grows significantly. The current implementation is appropriate for the existing catalog size.

### Product Discovery

#### Searchable Brand Filter

Current implementation:
- Standard dropdown containing all brands.

Future enhancement:
- Replace with a searchable filter component.
- Support type-to-filter behavior.
- Consider checkbox-based multi-select for large brand catalogs.

Reason:
Standard dropdowns become difficult to use when the catalog contains hundreds of brands.

Priority:
Post-v0.8

---

#### Searchable Category Filter

Implement only if the number of categories grows enough to justify replacing the current dropdown.

Priority:
Post-v0.8

---

#### Filter Result Counts

Examples:

- HP (42)
- Epson (18)
- Furniture (86)

Allow customers to see how many products each filter will return before selecting it.

Priority:
Post-v0.8

---

#### Advanced Search

Future enhancements:

- Live autocomplete
- Product suggestions while typing
- Highlight matching search terms
- Recent searches

Priority:
Post-v0.8

---

#### Performance

Evaluate when the catalog exceeds approximately 1,000–1,500 products.

Potential improvements:

- Lazy image loading
- Filter caching
- Query optimization
- Optional infinite scrolling

Priority:
Post-v0.8

#### Search Ranking

Future enhancement:

Improve result ordering by relevance.

Possible ranking:

1. Exact product name
2. Product name prefix
3. Brand
4. Partial match

Reason:

Simple LIKE searches become less useful as the catalog grows.

Priority:
Post-v1.0
