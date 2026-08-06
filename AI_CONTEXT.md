# AI_CONTEXT.md

# Sridevi Enterprises
Current Version: v0.9.0 — Employee Portal (Complete)

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

**Update:** a launch-only integration bridge to the Invoice Generator now exists (see Employee Invoice Generator Bridge) — the Employee Portal can link out to it, nothing more. Deeper shared-system work (shared authentication, shared invoice/inventory data, an API between the two projects) remains intentionally out of scope until after v1.0.0 — see Planned Roadmap > Future Roadmap for details.

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
✓ Departments Page (customer-facing label; internal route/template still `/categories` — see Categories Page below and Department Image Management)
✓ Search
✓ Contact Page (general enquiry form)

Not yet built (see Planned Roadmap):
- Product Comparison — `/compare` is currently a placeholder route, and as of the Customer Experience Audit is intentionally not linked from the navbar or footer (see Customer Experience Audit — Sitewide Consistency Pass) since a hidden feature is a better experience than a visible link that does nothing

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

**Bug fix (Department Image Management sprint): Featured Products images were never real.** `home.html` hardcoded every card to `images/placeholder.png` with a `<!-- TODO: Replace with product-specific images when image data is available -->` comment — stale even at the time, since Add Product/ProductImages had already shipped. `get_featured_products()` never called the shared image-attaching helper any other product listing uses. Fixed by calling `product_service.add_primary_images()` (see below) after the query and rendering `product.image_path` instead of the hardcoded path. Products that genuinely have no uploaded images still correctly show the placeholder — this is not a bug, most of the current demo catalog has zero `ProductImages` rows (verified via `SELECT COUNT(*) FROM ProductImages` during this fix).

### Categories Page

`/categories` is a premium, standalone category browsing page — not a variant of the homepage slider. It reuses `get_home_departments()` (`services/customer_service.py`), the same data source as the homepage Featured Categories slider, so category names, product counts, and images stay consistent across both. No new service function or API endpoint was introduced.

Sections, in order:
- Hero (heading, description, category search input)
- Category Grid — large image cards showing department name, product count, and an Explore button

Category search is client-side only (`initCategorySearch()` in `static/js/main.js`): it filters the already-rendered `.category-grid-card` elements by name as the user types, and toggles an empty-state message when nothing matches. No page reload, no new route.

Each card's Explore button links to `/products?department=<Department>` — the same existing product-listing route and query parameter the homepage slider already uses, so no new listing template was needed.

Styling lives in `static/css/categories.css` (new `.categories-page-hero`, `.categories-search`, `.category-grid`, `.category-grid-card` rules), appended alongside the existing homepage slider rules in the same file without modifying them. Grid is mobile-first: 1 column by default, expanding to 2 / 3 / 4 columns at wider breakpoints. Cards use a hover lift (shadow + translateY), an image zoom, and a gradient overlay on hover.

Both the navbar's and footer's "Categories" links now point to `url_for('customer.categories')`.

**Update (Department Image Management sprint) — "Category" deprecated in favor of "Department" as the customer-facing browsing concept**, per explicit user clarification mid-sprint. Renamed everywhere a customer sees the word: navbar link, footer link, this page's `<title>`, `<h1>` ("Shop by Category" → "Shop by Department"), the homepage slider's heading, both pages' search label/placeholder/empty-state text, the Explore button ("Explore" → "Browse", matching the sprint's literal wording), and the Products page empty-state's "Browse Categories" suggestion link. **Deliberately NOT renamed**: the `/categories` URL and the `customer.categories` endpoint name (left as-is to avoid a breaking route/bookmark/SEO change without more explicit instruction), the internal CSS classes (`.category-grid`, `.categories-page-hero`, etc.) and JS (`initCategorySearch()` in `main.js`, keyed off unchanged `#category-search`/`#category-grid`/`#category-empty-state` ids) — all of which are implementation details invisible to a customer, not the thing that was asked to change. **Also NOT touched**: the Products page's separate "Category" filter dropdown (`Catalog.category`, the finer-grained field, distinct from `Catalog.Department`) — the deprecation is about the *browsing/navigation* concept this page and the homepage slider represent, not a mandate to remove the existing, working `category` field filter, which is out of scope here and would be a separate, larger change if ever needed.

#### Navbar Active-Page Highlighting

`templates/components/navbar.html` now sets the `active` class per link by comparing `request.endpoint` against each route's endpoint (e.g. `request.endpoint == 'customer.categories'`), instead of hardcoding `active` on Home. This was a pre-existing gap (previously Home always showed active, regardless of the current page) surfaced while verifying the Categories page's active nav state, and is now correct on every customer page (Home, Products, Categories, Contact). Compare has no route yet, so it never highlights.

#### Category Image Fallback

`_resolve_category_image()` in `services/customer_service.py` now checks that a mapped category image file actually exists **and is non-empty** before using it; otherwise it falls back to the placeholder. This fixed a real bug found while verifying image fallbacks: `electronics.jpg`, `furniture.jpg`, and `miscellaneous.jpg` under `static/images/categories/` are committed as 0-byte stub files, which the browser can't decode — they rendered as broken images instead of the placeholder. Since `get_home_departments()` is shared, this fix also corrects the homepage Featured Categories slider, which had the same broken images. The underlying stub image files still need to be replaced with real photography; until then, all categories correctly show the placeholder.

**Update — superseded:** `_resolve_category_image()` and the hardcoded `_CATEGORY_IMAGES` dict it read from (only 4 of the catalog's 10 departments, ever) were fully removed and replaced by Department Image Management (see below) — `get_home_departments()` now delegates to `department_service.get_active_department_cards()`, which reads real, employee-uploaded images from the `DepartmentImages` table instead. The 0-byte stub files under `static/images/categories/` are no longer read by any code path; they can be deleted in a future cleanup pass (left alone here since deleting unrelated dead files wasn't this sprint's scope).

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

### Customer Experience Audit — Sitewide Consistency Pass

A holistic UX audit across the full customer journey (Homepage → Categories → Products → Product Details → Enquiry) found and fixed four cross-page inconsistencies, plus a documented-but-deferred button-styling review. No new routes, services, or SQL — every fix reuses templates/CSS/data that already existed.

**Navbar search is now wired to the real Products search.** `templates/components/searchbar.html` previously posted to `action="#"` and did nothing on any page. It now submits `GET` to `customer.products` reusing the existing `search` query parameter — identical to the Products page's own search form, no new route/service/backend logic. It also now reuses the same `.search-bar`/`.search-bar-field`/`.search-bar-icon`/`.search-bar-input`/`.search-bar-submit` classes as the Products page's own search form, so the navbar search looks and behaves identically to it everywhere. `navbar.css` keeps only a `.navbar-search-bar` width rule (320px desktop / 100% below 992px) — no icon/height/padding/radius/focus CSS is duplicated.

**New shared component stylesheet: `static/css/components/search.css`.** The `.search-bar*` rules (input, icon, clear button, submit button — the whole reusable search widget) were extracted out of `products.css` into this new file, which is loaded globally in `templates/layout/base.html` alongside `base.css`/`navbar.css`/`footer.css`. This was an explicit architectural cleanup: the navbar renders on every page, so it must not depend on a page-specific stylesheet like `products.css` for a component it uses sitewide. `.search-highlight` (the `<mark>` styling for matched search terms in product listings) stayed in `products.css` — it's a Products-page search-*results* concern, not part of the shared input widget. **Convention going forward:** `static/css/components/` is where sitewide-reusable UI pieces belong (loaded globally from `base.html`); `products.css` goes back to holding only Products/Product Details/Enquiry/Contact-page-specific styling and is loaded per-page via each template's `page_css` block — including `home.html`, which now links it directly (not globally) purely to reuse `.availability-badge`/`.catalog-product-pricing` for Featured Products, the same way Contact/Enquiry already reused it for their own styling.

**Homepage Featured Products cards** (`templates/customer/home.html`, `static/css/home.css`) reuse the `.availability-badge` component (green in-stock / amber on-request) and the `.catalog-product-pricing` class for "Contact for Pricing," replacing two `<p>` tags that both carried the same `.product-availability` class — a real bug where `home.css` defined that class twice with different styles, so the cascade made the pricing note and the actual stock status render identically (both blue/bold/1.2rem), impossible to tell apart. `.product-brand` was also updated to the same uppercase/bold/letter-spaced treatment already used for the brand line on Products cards and Product Details, for typographic consistency. Card layout/image handling was not touched (still the homepage's own placeholder image, per the existing TODO — no backend/data change).

**Similar Products cards on Product Details** (`templates/customer/product_details.html`) previously hardcoded `Available on Request` for every related product regardless of actual stock, and had no availability badge. Confirmed `get_related_products()` already returns real `availability` data, so this was template-only: added the same `.availability-badge` markup used elsewhere and corrected the pricing line to the sitewide "Contact for Pricing" wording. A small scoped rule, `.related-products-section .availability-badge { margin-bottom: 12px; }`, was added to `products.css` for spacing — confirmed via grep that the Employee Portal (which shares `.catalog-product-card`/`.related-products-section`) never uses `.availability-badge`, so this cannot bleed into the employee product details page.

**Category slider arrows** (`.slider-arrow` in `categories.css`) gained a `:focus-visible` outline matching the same pattern already used on pagination links, the search-clear button, and gallery thumbnails (`outline: 3px solid #1E4FA3; outline-offset: 2px;`) — closes a keyboard-accessibility gap where this was the only circular icon-button in the codebase without one.

**Compare is temporarily removed from customer navigation** (navbar and footer) rather than left as a dead `href="#"` link. The `/compare` route itself is untouched (still returns its placeholder response) — only the two nav entries pointing to it were removed, each replaced with an HTML comment noting it's deferred to v0.9. Reversing this when Compare ships is a two-line change.

**Button consistency review (documented, not changed):** searched for duplicated primary-button CSS across the customer site. Nearly all buttons already reuse plain Bootstrap `btn-primary`/`btn-outline-primary` with no custom per-instance styling (Enquiry/Contact submit buttons, Product Details CTAs, empty-state actions). The few custom treatments found — `.category-slide-body .btn` (Homepage slider "Explore") vs. `.category-grid-card-body .btn` (Categories page "Explore", which has an icon hover-translate micro-interaction the slider version lacks) — style the same conceptual action differently, but consolidating them would mean editing CSS shared by two already-shipped, previously-approved sections outside this pass's scope, for a cosmetic micro-interaction difference. Left unchanged per the audit's own risk rule ("if consolidation would introduce risk, leave unchanged and document"). Also noted: `.hero-buttons` in `home.css` is unused dead CSS (`hero.html` has no buttons in the hero itself; the homepage's buttons live in `quick_actions.html`) — not a duplication case, just unused code, left alone as out of scope for this pass.

## Employee Portal

✓ Employee Login
✓ Session Management
✓ Logout
✓ Protected Routes
✓ RBAC (see Architecture & Conventions)
✓ Employee Dashboard
✓ Employee Enquiries (read-only)
✓ Employee Customers (read-only, derived from Enquiries)
✓ Invoice Generator Integration Bridge (launch-only, see Employee Invoice Generator Bridge)
✓ Product Listing (search, filters, pagination)
✓ Product Details
✓ Add Product
✓ Upload Product Images
✓ Edit Product
✓ Replace Product Images
✓ Delete Product Images (Admin)
✓ Delete Product (Admin)
✓ Inventory Summary (read-only, v1.0 Sprint 1, see Employee Inventory Summary Module)
✓ Inventory Transactions — Stock In / Stock Out / Adjustment (v1.0 Sprint 5.1, see Employee Inventory Summary Module)
✓ Departments — Department Image Management (see Department Image Management)

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

**Entry points (v0.9 Milestone 5):** Edit was previously only reachable from Product Details or a direct URL. The Products list (`templates/employee/products.html`) now also has an "Edit" `.action-link` next to "View" on every row, linking to the same `employee.edit_product` route — no new route, no new backend logic, purely an additional entry point using the page's existing action-link styling. `product_form.html` also gained an explicit "Cancel" button (`btn-outline-secondary`, next to Save Changes/Create Product) that returns to Product Details when editing or the Products list when adding — previously the only way back was the "Back to..." link at the top of the page. Both Add and Edit already shared 100% of their validation, image-handling, and transaction logic before this milestone (see Write Operation Pattern) — this sprint found nothing left to extract at the service layer, only these two UI entry-point gaps.

**Note:** as of this milestone, Delete Product and Delete Product Image (Admin-only, see below) already exist and are unaffected by this sprint — Product Management (Add/Edit/Delete/Image management) is now a complete lifecycle end-to-end, not a future dependency.

### Product Form UX & Validation (v1.0 Sprint 4)

**Phase 3 binding review (done first, per the sprint's own instruction):** before making any UX changes, the reported "Department field displays an incorrect value" bug was investigated exhaustively — `get_product_for_edit()`'s SQL alias (`Department AS department`), the route's `form_data` dict, and the rendered `<input value="...">` were all compared against the raw `Catalog.Department` column for **all 315 products** via an automated end-to-end check (real DB value vs. actual rendered HTML). Zero mismatches were found. **No binding bug exists in the current code** — Department, Category, Brand, Model, and Stock Quantity all bind correctly on Edit. This is recorded here rather than silently skipped so a future reader doesn't re-open a non-issue; if the symptom recurs, suspect a stale `flask-dev` process first (see the recurring `FLASK_DEBUG=False`/no-autoreload dev note elsewhere in this doc) before assuming a code regression.

**Searchable Department/Category dropdowns (Phase 1).** Both fields changed from a free-text `<input list="...">` (HTML `<datalist>`) to a custom combobox: the same `.form-control` input, plus a Bootstrap `.list-group` suggestion menu that appears on focus/typing, filters as-you-type, and supports Arrow/Enter/Escape keyboard navigation. **Deliberately still allows free text** (not a locked `<select>`) — the datalist it replaces already allowed typing a brand-new department/category, and the catalog's 152-category taxonomy is clearly still growing organically; locking the field to a fixed list would have silently removed that capability, which the sprint brief never asked for. "Searchable dropdown" here means better UX (filtering, keyboard nav, cascading) layered on the same open-text semantics, not a hard constraint.

**Cascading filter**: `services/product_service.py:_get_department_category_map()` (called from `get_product_filters()`, whose existing `departments`/`categories`/`brands` keys are unchanged — this is purely an additive `department_category_map` key, since `get_product_filters()` is also shared by the customer Products page filter via `routes/customer.py`) groups categories by department in one query. The whole map is embedded as JSON in `product_form.html` and filtered client-side in JS — no AJAX endpoint, no per-keystroke server round-trip. Changing Department clears whatever Category was previously typed, since it's very unlikely to still apply.

**Live duplicate Product Name validation (Phase 2).** Two distinct duplicate checks now exist and must not be confused:
- `find_similar_product()` (pre-existing) compares name+brand+model together and only produces a **soft warning** flash message after saving — unchanged.
- `find_duplicate_product_name()` / `get_all_product_names()` (new) compare product name **alone**, case-insensitively with whitespace collapsed (multiple internal spaces included), and **block the save** with an error under the Product Name field. Add blocks any match; Edit passes `exclude_id=product_id` so keeping the current name is explicitly allowed, while renaming to another existing product's name is blocked. Both the client-side live check (an inline `<script>` in `product_form.html`, using the same `existing_product_names` list — normalisation logic duplicated intentionally in JS since it must run without a round-trip) and the server-side check share one `get_all_product_names()` query, so they can never disagree about what "duplicate" means. **The server-side check is authoritative** — verified by testing all three cases end-to-end (Add duplicate blocked, Edit-keep-own-name allowed, Edit-rename-to-existing blocked) via direct POST requests bypassing the client-side JS entirely.

**Form polish (Phase 4).** `autofocus` on Product Name; a red `<span class="text-danger">*</span>` on every truly-required label (Product Name, Department, Category, and Product Images — but only in Add mode, since Edit doesn't require a new image upload); Save is disabled whenever `form.checkValidity()` fails or the live duplicate check fails, and again on submit (with a Bootstrap `spinner-border-sm` + "Saving..." text) to block double-submission. `novalidate` stays on the `<form>` (suppresses the browser's own validation popups in favor of the existing Bootstrap `.invalid-feedback` styling) but native HTML5 constraint validation still runs via `checkValidity()` — if JS fails to load, the button simply never disables and the pre-existing server-side validation remains the real backstop, per progressive enhancement.

**No shared JS file was introduced** — the combobox/duplicate-check/button-state logic lives in one inline `<script>` at the bottom of `product_form.html`'s content block, following this codebase's established "each page keeps its own styles/logic inline" convention (previously CSS-only; this is the first employee page to extend that convention to page-specific JS). Reuse this pattern (inline `<script>` in the owning template, not a new shared file) for any future page-specific interactive behavior that isn't reusable elsewhere.

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

**Planned (roadmap only, not implemented — see Planned Roadmap > Soft Delete Product):** this hard-delete behavior (`DELETE FROM ProductDetails/ProductImages/Catalog`, folder removed from disk) is intended to be replaced by an archive/deactivate flow in a future sprint, so `StockHistory`, `Enquiries`, and any future invoice references to a product survive its removal from active listings. No hard `DELETE` should be introduced anywhere else in the meantime, and this existing one should be revisited when that sprint lands, not extended.

### Employee Dashboard — Command Center

The dashboard (`templates/employee/dashboard.html`, `routes/employee.py:dashboard()`) was restructured into three sections — Welcome Card, Statistics, Quick Actions — without touching `employee_nav.html` or any other employee page. Grep-confirmed the dashboard's CSS classes (`.dashboard-header`, `.dashboard-card`, `.coming-soon`, etc.) are used only in this one template, so all styling was edited in place rather than isolated behind new modifier classes.

**Welcome Card**: greeting ("Good morning/afternoon/evening") and the formatted current date are computed server-side in `dashboard()` from `datetime.now()` — no JavaScript, no new dependency. Designation/role and username were already in the session and template context.

**Statistics**: Products reuses the existing `get_product_count({})` (`services/product_service.py`, already used by the Products list page) for a real catalog count — no new query. Customers and Enquiries show "Coming Soon" and Invoice Generator shows "Available Soon" since none of those modules exist yet; no numbers are fabricated.

**Quick Actions**: five cards — View Products, Add Product, View Enquiries, Customers (all link to existing routes), plus Invoice Generator, which is a static, non-link, visually "disabled" card (`.dashboard-card.is-disabled`) since no Invoice Generator route exists in this app (it remains a separate future project per Future Roadmap). Enquiries/Customers keep a "Coming Soon" badge since those routes currently render only a placeholder message, not the real module.

No new routes, no schema changes, no auth changes. `coming_soon_message` branch (used by the placeholder `/employee/enquiries` and `/employee/customers` routes) is untouched.

#### Dashboard Polish (Milestone 2)

**"Pending module" convention**: any Quick Action card whose underlying module isn't built yet gets `.is-pending`, which mutes the icon, title, and description color (not just the "Coming Soon" badge), so unavailable actions read as visually secondary at a glance. `.is-disabled` is layered on top only for cards with no real route (currently just Invoice Generator) to drop the pointer cursor/hover lift, since it's a plain `<div>`, not an `<a>`. **When Enquiries or Customers gets built in a future milestone, remove `is-pending` from that card** (and update its stat card out of "Coming Soon") — that's the intended flip point for this convention.

**Equal card heights**: `.dashboard-card` is now a flex column (`height: 100%`, so it fills its stretched CSS Grid row) with a reserved min-height on the title and a 2-line `-webkit-line-clamp` on the description, and `margin-top: auto` on the optional `.coming-soon` badge. This keeps all Quick Action cards the same height/alignment regardless of whether a card has a badge — reuse this pattern for any future card grid on this page instead of relying on padding alone.

**Role badge**: `.role-badge` still displays the real `designation` (falling back to `role`) — no designation-to-category mapping was invented, since collapsing real job titles (e.g. "Warehouse Staff") into a fixed Manager/Sales/Admin enum would fabricate data not backed by `Employees.Designation`. Instead it was restyled as a pill, with a `role-badge-admin` accent variant driven by the session's authoritative `Role` (Employee/Admin) — the one designation-adjacent field RBAC already treats as ground truth.

**System Status panel**: `db_connected`/`catalog_loaded` in `dashboard()` are set `True` directly after `get_product_count()` returns — no new health-check query. Reaching that line already proves the DB call succeeded, so this is a free-standing implication of an existing call, not fabricated status. If a real health-check becomes necessary later, replace this inline logic rather than assuming it already checks anything beyond that one query.

**Recent Enquiries empty state**: intentionally static markup ("No enquiries available yet...") — does not query the `Enquiries` table. Wiring it to real data is Enquiry Management (v0.9.5), out of scope here. **Update (Milestone 3):** the Overview stat and Quick Actions card below now DO show real data (see Employee Enquiries Module) — only this Operations panel remains static. This is a known, flagged inconsistency (the dashboard can show "14" in Overview while this panel still says "No enquiries available yet"); reconciling it is deferred to a future milestone rather than done as an unscoped fix here. **Update (v1.0 Sprint 2 — Inventory Management Foundation):** resolved. See "Recent Enquiries wiring" under Employee Inventory Summary Module below — this panel now shows the 5 most recent enquiries, closing the inconsistency described above.

### Employee Enquiries Module

Foundation (read-only) employee-facing view of the `Enquiries` table, replacing the `/employee/enquiries` placeholder that used to render `dashboard.html`'s `coming_soon_message` branch. **Update (Milestone 5):** `employee.customers()` was later rewired the same way — see Employee Customers Module below. Neither route uses the `coming_soon_message` branch anymore.

**Database**: no schema changes. `Enquiries` (`database/schema/005_create_enquiries.sql`) already existed and was already being written to by the customer site's product-enquiry and Contact forms (`services/enquiry_service.py:create_enquiry()`, used by `routes/customer.py`). This module only adds read queries.

**Service layer**: `get_enquiries(filters, page, per_page)` and `get_enquiry_count(filters)` were added to `services/enquiry_service.py`, mirroring `product_service.py`'s `get_products()`/`get_product_count()` pattern exactly (same `_build_*_filters()` helper shape, same `fetch_all`/`fetch_one` reuse from `database/db.py`). `get_enquiries()` `LEFT JOIN`s `Catalog` to resolve `ProductID` to a product name for display (`ProductID` is nullable — general Contact-form enquiries have none, shown as "General Enquiry"). Search matches Customer Name, Email, Phone, or the joined product name.

**Route/template**: `routes/employee.py:enquiries()` follows the exact same pagination shape as `products()` (`per_page = 20`, `start_page`/`end_page` window, clamped `page`). `templates/employee/enquiries.html` is a new, self-contained page (own `page_css` block, own scoped class names — `.enquiries-table`, not `.products-table`) that structurally follows `products.html`'s list-page pattern (search bar → table → pagination → empty state), while reusing the Dashboard's *visual language*: card shadows/radii, the pill-badge convention, and the Operations panel's exact `.empty-state` CSS, copied in per the sprint's explicit instruction to reuse it (each employee page keeps its own inline styles — no shared CSS file was introduced, consistent with how `dashboard.html`/`products.html` already do this independently).

**Dashboard integration**: `dashboard()` now also calls `get_enquiry_count({})` and passes `enquiry_count` to the template. The Overview stat card shows the real number instead of "Coming Soon", and the "View Enquiries" Quick Action card lost its `is-pending`/`.coming-soon` treatment — it now looks and behaves exactly like "View Products"/"Add Product". (The Customers stat/card were still pending at the time this module shipped; see Employee Customers Module for when that changed.)

#### UI Polish (Milestone 4)

**Detail view is now a read-only Bootstrap modal, not `<details>`.** Each row's "View Details" is a `.btn.btn-primary.btn-sm` (the same primary-button convention already used elsewhere in the portal, e.g. Add Product) that opens `#enquiryModal{{ EnquiryID }}` — one modal per row, rendered in its own loop right after the table (not nested inside `<td>`, to keep the table markup simple and avoid any interaction between the table's `overflow-x: auto` scroll container and the modal). **This is the first Bootstrap modal used anywhere in the app** — it works because `bootstrap.bundle.min.js` is already loaded globally in `layout/base.html`; no new script was added. The modal is strictly read-only: header + a `<dl>` of Customer Name/Phone/Email/Product/Date/Status/Message + a single Close button in the footer — no edit, status-update, or delete controls, matching the module's read-only scope.

**Status badge palette expanded for future values.** `.status-badge` now has distinct styles for `status-pending` (amber), `status-in-progress` (blue), `status-resolved` (green), `status-closed` (gray), and `status-other` (neutral fallback) — only `status-pending` can appear today since nothing writes any other value to `Enquiries.Status` yet, but the CSS and the Jinja `status_class` selection logic (duplicated identically in the table row and the modal, both driven by the same `Status` string) already handle `Resolved`/`Closed`/`In Progress` so a future status-update feature can start writing those values without touching this page's CSS.

**Convention for future employee list pages needing a read-only detail view**: reuse this per-row-modal pattern (loop after the table, `id="{{ prefix }}{{ row.PrimaryKey }}"`, `<dl>` body, Close-only footer) rather than inventing a new disclosure mechanism.

### Employee Customers Module

Foundation (read-only) employee-facing customer list, replacing the `/employee/customers` placeholder the same way Milestone 3 replaced Enquiries.

**Data source — deliberately not the `Customers` table.** A `Customers` table exists in schema (`database/schema/004_create_customers.sql`: `CustomerID, Name, Phone, Email, Address, CreatedDate`), but a full-codebase grep confirmed **nothing writes to it** — no route, form, or service creates a row there. It is dead schema. Real, existing customer data lives entirely in `Enquiries` (`CustomerName`, `Phone`, `Email` on every row — both `Phone` and `Email` are mandatory per `enquiry_service.py:validate_enquiry()`). This module derives customers by grouping `Enquiries` by `Email`, not by querying `Customers`. **If a future milestone starts actually writing to the `Customers` table** (e.g. a real signup/account flow), this module should be revisited to read from it instead — grouping by `Email` was a deliberate stand-in for a data source that doesn't exist yet, not a permanent architectural choice.

**Service layer** (`services/enquiry_service.py`, alongside the Enquiries functions — kept in the same file since the underlying data is Enquiries, not a separate concern): `get_customers(filters, page, per_page)` and `get_customer_count(filters)` treat one distinct `Email` as one customer. For each `Email`, the representative row (`CustomerName`, `Phone`) is the row with that email's `MAX(EnquiryDate)` — joined back via `agg.LastEnquiryDate = e.EnquiryDate` rather than a window function, to stay consistent with the rest of the codebase's plain-SQL style. This was verified against real data where the same person submitted under two different names ("Srikar" then later "Ravi", same email/phone): the customer correctly shows as one row using the more recent name. **Known edge case, intentionally unhandled**: if the same email has two enquiries with the exact same `EnquiryDate` to the second, both would match the join and the customer could appear twice; considered acceptable given realistic submission timing and the read-only, low-traffic nature of this admin page — flag if this becomes a real problem.

**Search scope**: matches the representative (most recent) row's `CustomerName`/`Phone`/`Email` only, not every historical name/enquiry a customer ever used. In the "Srikar"/"Ravi" example above, searching "Ravi" matches the *other* still-separate "Ravi Kumar" customer but not "Srikar" (whose older enquiry happened to use "Ravi" as the name) — a deliberate simplification over re-deriving from full history on every search, consistent with keeping this a small read-only page rather than a bigger reporting feature.

**Recent Products / Recent Messages (customer detail modal)**: `_add_recent_enquiries()` fetches all matching enquiries for the current page's customers in **one batched query** (`WHERE Email IN (...)`, same `IN (placeholders)` pattern as `product_service.py:_add_primary_images()`), then slices the newest 5 per customer in Python — not N+1 per-row queries, and not a SQL "top N per group" query, matching the codebase's existing preference for simple SQL plus a small Python grouping step.

**Template**: `templates/employee/customers.html` follows the same structural/visual pattern as `enquiries.html` exactly (search bar → table → per-row Bootstrap modal → pagination → empty state, all in an inline `page_css` block with page-scoped class names). The customer modal's `id` is keyed by `loop.index` (not a `CustomerID`, since none exists) rather than `Email`, since raw emails aren't safe to embed directly as HTML `id` attribute values.

**Dashboard integration**: `dashboard()` now also calls `get_customer_count({})` and passes `customer_count`. The Overview stat card shows the real distinct-customer count instead of "Coming Soon", and the "Customers" Quick Action card lost its `is-pending`/`.coming-soon` treatment — it now behaves exactly like the other fully-active cards.

**Future extension points**: `Customers.Address` (unused, since the page is Enquiries-derived and Enquiries has no address field) and any real `Customers` table usage are natural follow-ups if a genuine customer-accounts feature is ever built. No customer status was introduced, per this sprint's explicit constraint.

**Future extension points**: the table has plain `<th>` columns (Customer, Product, Date, Status, Actions) with no colspan/rowspan tricks, so future columns (Priority, Assigned Employee, Last Updated) can be appended without restructuring. `Status` currently only ever contains `'Pending'` (no UI writes to it yet — this module is read-only); `.status-badge`'s color mapping already handles `Resolved`/`Closed` and an "other" fallback so a future status-update feature can start writing new values without any CSS changes here.

### Employee Invoice Generator Bridge

**Renamed in v1.0 Sprint 3** (Invoice Terminology Update): this module was originally shipped in v0.9.0 as "Employee Receipt Generator Bridge" — every Employee Portal reference (route, template, config var, nav label, dashboard copy) was renamed from "Receipt Generator"/"Receipts" to "Invoice Generator"/"Invoices". **The external project itself was NOT renamed** — it remains a separate codebase actually named "Receipt Generator" (see below); only how the Employee Portal *displays* it changed. Route: `GET /employee/invoices` (`routes/employee.py:invoices()`, was `receipts()`/`/employee/receipts`). Template: `templates/employee/invoices.html` (was `receipts.html`, including its `.invoices-*` CSS classes, was `.receipts-*`). Config: `Config.INVOICE_GENERATOR_URL` (was `RECEIPT_GENERATOR_URL` — the old env var name is still read as a fallback for backward compatibility, see config.py).

The underlying external project is a **completely separate Flask project**, still actually named "Receipt Generator" (its own repo, `app.py`, dependencies, and process — found locally at a sibling directory outside this repo). It shares only the `Catalog` table in the same MariaDB database (already documented in `database/README.md`: "Catalog is the shared table with the Receipt Generator" — that note was deliberately left unrenamed, since it correctly names the real external project) and is deployed independently (it has its own `passenger_wsgi.py`/`render.yaml`, and even hardcodes its own local DB connection rather than reading this project's `.env`). This bridge adds only the **integration bridge** on the Employee Portal side — nothing in the external project was read into memory for reuse, copied, or modified.

**Why duplication/merging was rejected**: reverse-proxying, iframing, or re-implementing any invoice/GST logic here would (a) require running two Flask processes that already conflict on the same default port in local dev, (b) duplicate business logic (GST math, PDF generation) that already exists and works in the other project, and (c) blur a deployment boundary the two projects don't currently share (different hosting config, no shared session/auth). The external project also has **no authentication of its own** — its routes are open once reached — so the only safe integration from the Portal side is a plain outbound link, never an embed that would imply it's protected by this app's login.

**Launch method — configurable external link**: `Config.INVOICE_GENERATOR_URL` (`config.py`, read from `INVOICE_GENERATOR_URL`, falling back to the deprecated `RECEIPT_GENERATOR_URL` if unset, documented in `.env.example`) holds the deployed invoice-generation project's base URL. `routes/employee.py:invoices()` (`GET /employee/invoices`) passes it straight through to `templates/employee/invoices.html`:
- **If set**: renders a primary "Launch Invoice Generator" button (`target="_blank" rel="noopener noreferrer"`) — opens in a new tab since it's a genuinely separate application/origin, not something to embed.
- **If unset (the default, since no real deployment URL exists yet)**: renders a plain Bootstrap-styled "Invoice Generator Unavailable" info card — no stack trace, no technical detail exposed to the employee, just a professional "check back later or contact your administrator" message. This is the actual out-of-the-box state of this repo today.

**Dashboard integration**: the Invoice Generator Quick Action card is a normal active link to `employee.invoices` (no `is-pending`/`.coming-soon` — the module is real, exactly like Enquiries/Customers). The Overview stat card shows `"Ready"` or `"Not Configured"` (computed from whether the URL is set) instead of a static label — this mirrors the System Status panel's existing convention of reporting real boolean state rather than fabricating a number; there is no meaningful count to show here since invoices are created and stored entirely inside the other project's own database, which this app deliberately does not query.

**Navigation**: `employee_nav.html` has one `<li>` for this module ("Invoices", between Customers and Logout) — the same list-item pattern used by every other module link, not a nav redesign.

**Future integration roadmap**: if the two systems are ever meant to feel more integrated (e.g. showing recent invoice counts on the Dashboard, or single sign-on into the invoice-generation project), that requires the external project to expose either an API or shared authentication — neither exists today. Until then, this launch-link bridge is the intended integration boundary; do not add direct queries against the external project's own tables (e.g. its `invoices` table) from this codebase, since that would silently couple the two projects' schemas without either project agreeing to the contract.

### Employee Portal Release Audit (v0.9.0)

A polish/cleanup pass across every Employee Portal page — no new features, no redesign. Kept brief since nothing architectural changed:

- **Pagination**: `products()`, `enquiries()`, and `customers()` in `routes/employee.py` had identical page-clamping/window arithmetic copy-pasted three times; extracted into `_paginate(page, total_items, per_page)`. Behavior is unchanged — verified identical output before/after.
- **Accessibility**: added `scope="col"` to every list-table `<th>`, `aria-current="page"` to the active nav link and the current pagination page, visually-hidden `<label>`s on the Enquiries/Customers search inputs (Products already had visible labels — search inputs elsewhere didn't), and `aria-label`s on the previously-unlabeled spec-row inputs, per-image replace inputs, and the Admin-only delete-image button. Modal accessibility (`aria-labelledby`, `aria-hidden`, close button `aria-label`) was already correct.
- **Fixed a real bug**: `customers.html` defined a `.customer-contact` class (muted icon + text, matching Enquiries' styling) but never applied it to the Phone/Email table cells — they were rendering as unstyled default text. Now applied; visually matches Enquiries.
- **Removed dead files**: `templates/employee/inventory.html` and `templates/employee/reports.html` were 0-byte stub files from an early one-time `restructure_project.py` scaffolding run, never referenced by any route. Deleted. (`restructure_project.py` itself is a historical "run once only" migration script, left alone.)
- **Not changed, deliberately**: the per-page inline `<style>` block duplication across `products.html`/`enquiries.html`/`customers.html`/`invoices.html` (search-section, empty-state, pagination CSS repeated per page) is real duplication but is the established, documented convention in this codebase (page isolation over a shared stylesheet) — extracting it would be a structural change out of scope for a polish sprint. The repeated `if not session.get("UserID")` / role-check guard at the top of every route was also left as-is rather than wrapped in a decorator, for the same reason.

---

### Employee Inventory Summary Module (v1.0 Sprint 1 — Inventory Dashboard Foundation)

A read-only "inventory intelligence" layer over the existing `Catalog` table — not inventory management. No schema changes, no stock movement, no suppliers, no Invoice Generator integration changes; this sprint only adds read queries and two new views over data that already existed.

**Temporary global threshold.** `_LOW_STOCK_THRESHOLD = 5` (`services/product_service.py`) classifies every product into Healthy (`stock_quantity > 5`), Low Stock (`1–5`), or Out of Stock (`0` or `NULL`) — a module-level constant, not a database column. **This is intentionally temporary**: a future sprint will add a per-product `MinimumStock` column to `Catalog` (schema change, deliberately out of scope here) and replace this constant with a real per-product comparison. **Update (v1.0 Sprint 2):** this constant is now private and only ever read through `get_low_stock_threshold()` — see "Threshold wrapper" below for the single-change-point convention this enables.

**Service layer** (`services/product_service.py`, alongside the existing product-read functions — no new file, per the sprint's "reuse the Product Service" constraint): `get_inventory_summary()` (one aggregate query for the five headline counts), `get_inventory_by_department()` / `get_inventory_by_category()` (thin wrappers around one shared `_get_inventory_group_summary(column)` helper, since Department and Category needed identical aggregation SQL — avoids the duplicate-SQL trap explicitly called out in this sprint's brief), and `get_stock_status_count(status)` / `get_products_by_stock_status(status, page, per_page)`, both built on one shared `_stock_status_filter(status)` WHERE-clause helper (`"low_stock"` / `"out_of_stock"`) so the count and list queries can never drift out of sync with each other.

**Dashboard integration**: `dashboard()` now also calls `get_inventory_summary()` and passes it to the template. A new "Inventory Overview" `.stats-grid` section (identical `.stat-card` markup/styling to the existing "Overview" section — no new card design) sits between Overview and Quick Actions, showing Total Products / Total Stock Units / Healthy / Low Stock / Out of Stock. A new "Inventory Summary" Quick Action card was added alongside the existing five, linking to the new page.

**New page**: `GET /employee/inventory` (`routes/employee.py:inventory()`, `templates/employee/inventory.html`) follows the same structural pattern as Products/Enquiries/Customers (own inline `page_css` block, page-scoped class names, `.empty-state`/`.pagination` copied from the established convention) — page heading, Inventory Overview cards, Department Summary table, Category Summary table, Low Stock list, Out of Stock list.

**New convention: two independently paginated lists on one page.** The Low Stock and Out of Stock lists each paginate via their own query parameter (`low_stock_page`, `out_of_stock_page`) rather than sharing one `page` param, so paging through one list never resets the other. Every pagination link on the page carries both current values (mirroring how existing single-list pages already carry `search` through every pagination link). `per_page = 10` for both lists — smaller than the usual 20, a deliberate choice to keep two tables plus two summary tables readable on one page. Department Summary and Category Summary are rendered as full (unpaginated) tables — at the current catalog scale (10 departments, ~150 categories) this is appropriate per the existing "Future Scalability Improvements" convention; revisit if the category count grows substantially. **Reuse this dual-pagination pattern for any future page that needs two independent lists together**, rather than inventing a different mechanism.

**Status badge**: `.stock-status-badge` (page-scoped to `inventory.html`) extends the existing pill+dot visual language already established by `.availability-badge` (Product Cards/Details) and `.status-badge` (Enquiries) — reusing the exact same green/amber colors for Healthy/Low Stock, adding one new red variant for Out of Stock (`#FEF3F2`/`#B42318`) since no 3-state badge existed yet. Per the Component Isolation convention, this is a new page-scoped class, not a modification of `.availability-badge` or `.status-badge`.

**Not built, deliberately** (explicitly out of scope for this sprint): inventory movement, stock history, suppliers, purchase orders, goods receipt notes, stock reservations, any `MinimumStock` column, and no changes to Invoice Generator integration, Product Editing, the customer website, or employee authentication.

#### v1.0 Sprint 2 — Inventory Management Foundation

Builds usability on top of Sprint 1's read-only foundation. Still no stock movement, purchase orders, suppliers, receipts, or schema changes.

**Threshold wrapper (Phase 4).** `get_low_stock_threshold()` (`services/product_service.py`) is now the single point of access for the low-stock cutoff — `_get_inventory_group_summary()`, `_stock_status_filter()`, and `get_inventory_summary()` all call it instead of touching `_LOW_STOCK_THRESHOLD` directly, and `routes/employee.py` imports the function, not the constant. **This is the one place to change** when a per-product `MinimumStock` column ships: swap what this function returns/how callers use it, and every query and the Inventory Summary page's threshold note update automatically. See the function's docstring for the exact migration shape.

**Recent Enquiries wiring (Phase 2).** `dashboard()` now calls `get_enquiries({}, 1, 5)` — the exact same function and query the Enquiries page and its search already use, just capped to 5 rows, newest first (the function already orders `ORDER BY e.EnquiryDate DESC`). No new query was written. Each item shows Customer Name, Product (or "General Enquiry"), a status badge, and the submitted date. **Chosen interaction**: rather than duplicating the Enquiries page's per-row Bootstrap modal markup onto the Dashboard (which the sprint's own instructions flagged as an acceptable but non-mandatory option — "open the existing enquiry modal **or** navigate to the Enquiries page"), each item links to `employee.enquiries` with `?search=<CustomerName>` — reusing the existing `_build_enquiry_filters()` search match with zero new code, and giving each item a more useful destination than the plain "View All Enquiries" button next to it (which links to the unfiltered list). This closes the long-flagged Dashboard/Operations-panel inconsistency noted under Employee Dashboard — Command Center above.

**New template filter: `status_class`.** Registered via `@employee_bp.app_template_filter("status_class")` in `routes/employee.py`, mapping an `Enquiries.Status` value to its `.status-badge` CSS modifier class. This replaces three previously-duplicated copies of the same 5-line Jinja `{% set %}` chain (the Enquiries table row, the Enquiries detail modal, and now the Dashboard's Recent Enquiries) with `{{ enquiry.Status|status_class }}` everywhere. Pure refactor of `enquiries.html` — verified byte-for-byte equivalent output before/after. **Reuse this filter for any future badge keyed off `Enquiries.Status`** instead of re-deriving the status→class mapping inline.

**Inventory UI polish (Phase 3), same visual language, no redesign.** The Inventory Overview cards' Healthy/Low Stock/Out of Stock icons now use `.stat-card-icon--healthy`/`--low`/`--out` (green/amber/red, identical colors to `.stock-status-badge`) on both `dashboard.html` and `inventory.html` — Total Products/Total Stock Units stay the default blue, per the sprint's "totals remain neutral" rule. The Department Summary and Category Summary tables' Low Stock/Out of Stock number cells get the same amber/red treatment (`.inventory-figure--low`/`--out`) **only when the count is greater than 0** — a zero in red/amber would read as a false alarm, so this was a deliberate judgment call, not a literal "always color it" reading of the brief. **CSS specificity gotcha found and fixed**: the color modifier classes must be written as `.inventory-table td.inventory-figure--low` (not `.inventory-figure--low` alone) — the existing `.inventory-table td { color: #333; }` rule has higher specificity (0,1,1) than a single class selector (0,1,0) and was silently winning, leaving every cell neutral gray despite the class being applied. Caught via computed-style verification in-browser, not visually.

**Regression bug found and fixed**: adding the Recent Enquiries list caused a real horizontal-scroll overflow on the Dashboard at mobile width (375px). Root cause: `.info-panel` is a CSS Grid item inside `.info-grid` (`grid-template-columns: repeat(auto-fit, minmax(280px, 1fr))`) with no `min-width` override, so its default `min-width: auto` let a long `white-space: nowrap` product name (used for the ellipsis-truncation effect) force the whole card — and the page — wider than the viewport instead of truncating. Fixed by adding `min-width: 0` to `.info-panel`. **Convention for future grid items that contain nowrap/ellipsis text**: the grid item itself needs `min-width: 0`, not just the truncating element — `min-width: 0` on a descendant does nothing if an ancestor grid/flex item is still sized to content.

**Dev workflow note**: this project's `FLASK_DEBUG=False` disables Jinja template auto-reload (see the existing Dev note under Products Page — Filtering Experience), so every template/CSS edit during this sprint's verification required restarting the `flask-dev` process before the browser would see it — a plain page reload was not enough and silently served the stale compiled template.

#### v1.0 Sprint 3 — Inventory UX Refinement & Invoice Terminology

UI/UX-only sprint: no schema changes, no stock movement, no CRUD, and no changes to the standalone (externally-named) Receipt Generator project itself.

**Section reorder, same SQL/pagination.** On `templates/employee/inventory.html`, real employee use surfaced that Low Stock and Out of Stock — the two sections used most often day-to-day — sat below a 150+ row Category Summary table, forcing a long scroll past it every visit. The page order is now: Inventory Overview → Department Summary → Low Stock Products → Out of Stock Products → Category Summary. This was a pure `{% block content %}` reordering in the template — no route, service, query, or pagination logic changed; `low_stock_page`/`out_of_stock_page` still paginate independently exactly as in Sprint 2.

**Category Summary collapsed by default.** Now wrapped in a Bootstrap `.collapse` (`id="categorySummaryCollapse"`), toggled by a plain `btn-outline-primary` button reading "Show Category Summary ({{ category_summary|length }} Categories)" — reuses Bootstrap's existing collapse plugin (already loaded via `bootstrap.bundle.min.js`, same as the Enquiries/Customers detail modals use its modal plugin) rather than adding any custom JavaScript. The chevron icon flips via a pure-CSS rule keyed off the `aria-expanded` attribute Bootstrap already manages on the toggle button (`[aria-expanded="true"] { transform: rotate(180deg) }`) — no click handler was written. The table markup/columns inside are byte-for-byte unchanged from Sprint 2.

**Invoice terminology rename (Phase 2).** See Employee Invoice Generator Bridge above for the full before/after — in short, every Employee-Portal-facing "Receipt Generator"/"Receipts" string became "Invoice Generator"/"Invoices" (nav, dashboard card + stat label, page heading/buttons/empty states, route, template file, CSS class prefix, config var), while the actual external project keeps its real name, "Receipt Generator", unchanged. **Convention going forward**: when this codebase's prose or comments need to refer to the external invoice-generation project by its real name (e.g. explaining *why* two systems are separate), say so explicitly — don't assume "Invoice Generator" always means the external project, since inside this codebase it now means the Employee Portal's own display label for the bridge to it.

#### v1.0 Sprint 5.1 — Inventory Transactions (Stock In / Stock Out / Adjustment)

The first write-capable inventory module. Every transaction updates `Catalog.stock_quantity` and inserts exactly one `StockHistory` row atomically (see Write Operation Pattern) — there is no code path that touches one without the other.

**Schema-drift discovery (found before writing any transaction logic).** The previous sprint's `009_alter_stockhistory_add_transaction_columns.sql` added `TransactionType`/`QuantityChanged`/`ReferenceType` as nullable with `DEFAULT NULL`. Live-schema verification at the start of this sprint found the actual database already had all three hardened to `NOT NULL` with specific defaults (`'ADJUSTMENT'`, `0`, `'MANUAL'`) — a deliberate-looking change made directly against the database, outside that file, between sprints. Per this project's own documented rule ("never manually modify schema without reflecting the change back into version control" — see Deployment Lessons), **the migration file was updated to match the verified live schema** rather than the drift being silently reverted or ignored. Two concrete consequences for any code touching this table:
- `StockHistory.TransactionType` values are `'STOCK_IN'` / `'STOCK_OUT'` / `'ADJUSTMENT'` (ALL_CAPS, matching the column's own default) — not the Title Case labels (`"Stock In"` etc.) used for on-screen text. `services/product_service.py` keeps these as two separate maps (`_TRANSACTION_TYPE_LABELS` for display, `_TRANSACTION_TYPE_DB_VALUES` for storage) — don't collapse them into one.
- `StockHistory.ReferenceType` is always explicitly written as `'MANUAL'` for every Sprint 5.1 transaction (matching the column's default, but written explicitly rather than relied on implicitly, since "populate all available fields" was an explicit requirement) — `ReferenceID` stays `NULL`, since none of these transactions have a Purchase Order/Goods Receipt/Sales Invoice to point back to yet (see Out of Scope below).

**One reusable form, not three pages.** `GET/POST /employee/inventory/transaction` (`routes/employee.py:inventory_transaction()`, `templates/employee/inventory_transaction.html`) handles Stock In, Stock Out, and Adjustment through one route/template, switched by a `transaction_type` radio group (Bootstrap `.btn-check`/`.btn-outline-primary`, not a redesign — same button-group pattern Bootstrap already ships). A `?type=stock_in`/`stock_out`/`adjustment` query param pre-selects the radio so each of the Inventory Summary page's three new entry-point cards still feels distinct, without three separate implementations existing underneath. The same numeric `quantity_input` field is reinterpreted per type: an amount to add/remove for Stock In/Stock Out, or the new absolute stock level for Adjustment — its label and `min` attribute swap via JS depending on the selected type.

**New shared JS component: `static/js/components/searchable_select.js`.** The Department/Category combobox built in v1.0 Sprint 4 was extracted out of `product_form.html`'s inline `<script>` into this file (generalized to accept `{value, label}` option objects instead of plain strings, so the submitted value can differ from the displayed text) and reused as-is for this form's Product selector — "reuse the searchable product selector already used throughout the Employee module, do not build another product search component" was taken literally. **Convention going forward**: this is the first entry in `static/js/components/`, mirroring the existing `static/css/components/` convention (sitewide-reusable pieces get their own file, loaded via `<script src="...">` per page that needs them) — extract any future interactive widget here the moment a second page needs it, rather than copy-pasting.

**Product/current-stock data embedded, not fetched via AJAX.** `get_products_for_transaction()` (new, `product_service.py`) returns every product's id/name/department/category/stock_quantity in one query, embedded as JSON in the page (`{{ products | tojson }}`) — same pattern as Sprint 4's `existing_product_names`. This is what lets the confirmation modal compute and display "Current Stock"/"New Stock" instantly without a round-trip. The server never trusts this client-side snapshot for the actual write: `apply_stock_transaction()` re-reads `Catalog.stock_quantity` with `SELECT ... FOR UPDATE` inside the write transaction, so two concurrent Stock Out requests for the same product can never both succeed and push stock negative — the page-load snapshot is a UI convenience only.

**Confirmation modal, populated client-side.** Follows the existing per-page-modal convention (see Employee Enquiries Module) but is populated from the form's current values via JS immediately before showing it, rather than server-rendered per row (there's only one transaction being composed, not a list). "Confirm" is a real `<button type="submit" form="inventory-transaction-form">` outside the `<form>` tag (HTML5's `form` attribute) — clicking it submits the actual form with no extra JS required for the submission itself, only for populating and showing the modal beforehand.

**EmployeeID mapping.** `StockHistory.EmployeeID` has a foreign key to `Employees.EmployeeID` (added last sprint) — a *different* id than the session's `Users.UserID`. `services/auth_service.py:get_employee_id_for_user(user_id)` (new) does the lookup; if a logged-in account has no linked `Employees` row, the route shows a clear error and writes nothing, rather than letting the FK constraint fail as a raw 500.

**Validation, client-side hint + server-side authority.** `validate_stock_transaction_form()` (pure field-shape checks, no DB access — same split as `validate_product_form()`) plus `apply_stock_transaction()`'s own checks (product exists, Stock Out can't go negative) together guarantee **no invalid request can ever modify `Catalog` or `StockHistory`** — verified by direct POST testing seven invalid-input cases (missing product, missing reason, zero quantity, negative adjustment, non-numeric quantity, unknown transaction type, nonexistent product id) and confirming stock and history row counts were byte-for-byte unchanged after all seven. The client-side live preview (same "Cannot stock out N units — only M in stock" message shown in both places) is a UX hint only; it can be bypassed and the server still catches everything.

**Out of scope, deliberately not built** (per the sprint's explicit list): Purchase Orders, Goods Receipts, Supplier Management, Barcode Scanning, multi-location inventory, batch/serial numbers, CSV import/export, undo transaction, inventory reports. `ReferenceType`/`ReferenceID` exist on the table specifically so a future sprint building any of these can link a `StockHistory` row back to its originating record without another migration.

### Department Image Management

New feature (one new table, `DepartmentImages` — see Data & Storage Conventions below for the full column list and the "why no FK to Catalog" reasoning, same pattern already established for `StockHistory.EmployeeID`). **Permanently replaces** the old hardcoded `_CATEGORY_IMAGES` dict in `customer_service.py`, which only covered 4 of the catalog's 10 departments and silently fell back to a placeholder for the rest. `Catalog.Department` remains the sole source of truth for product classification — `DepartmentImages` is presentation-only, matched to a real Catalog department by `DepartmentName` (a UNIQUE string), never a foreign key, since `Catalog.Department` is free text with no id of its own.

**New service file: `services/department_service.py`** — the first new employee-facing service file since `image_service.py`. Houses everything Department Image Management needs: `get_catalog_department_names()` / `get_department_product_counts()` (the two small queries every other function here is built from), `get_departments_for_management()` (every Catalog department, joined with its `DepartmentImages` row if one exists — departments with no row yet still appear, so employees can see what still needs an image), `get_department_for_edit()`, `upsert_department_image()` (single-table Write Operation Pattern: save new file → write DB row → delete old file only after success, mirroring `update_product()`'s established refinement), and `get_active_department_cards()` (the customer-facing read, active+configured only).

**Employee Departments module** (`GET /employee/departments`, `GET/POST /employee/departments/<department_name>/edit`) — new nav entry (between Products and Inventory) and Dashboard Quick Action card, matching every other module. The list table (`templates/employee/departments.html`) mirrors `products.html`'s table conventions; the edit form (`templates/employee/department_form.html`) mirrors `product_form.html`'s card/label conventions. **Departments are never freely nameable**: `department_name` in the edit route is validated against `get_catalog_department_names()` (404 if it isn't a real Catalog department), so there is no code path that can create a `DepartmentImages` row for a name that doesn't exist in `Catalog.Department` — this, plus the column's own `UNIQUE` constraint, is what satisfies "do not allow duplicate department entries" without needing extra duplicate-checking logic. Image upload is optional when editing an already-configured department (keeps its current image if none is chosen) and required when configuring one for the first time (enforced both client-side via `required` and server-side, verified by direct POST bypassing the client check).

**Image storage**: a new `static/uploads/departments/` folder (parallel to the existing `static/uploads/products/<id>/`), added to `services/image_service.py` (`save_department_image()`, `delete_department_image_file()`, `department_image_path()`). Unlike `ProductImages.ImageURL` (a full relative path, since products have per-product subfolders), `DepartmentImages.ImageFilename` stores a bare filename only — matching the sprint's own schema field name literally, since every department image lives flat in one shared folder rather than a per-department folder (one department = one image, no gallery, so a subfolder per department would be unnecessary structure).

**Customer-facing behavior change, deliberate**: a department only appears on the homepage slider / `/categories` page once an employee has uploaded an image **and** enabled it — previously every Catalog department showed unconditionally (falling back to a placeholder if unmapped). This is intentional: it's what makes the Enable/disable control in the Employee Departments module actually mean something. Until employees configure departments, the customer-facing section may legitimately be empty — both templates already have an existing empty state ("No categories available yet.") for this, no new one was needed. `get_home_departments()` (`customer_service.py`) keeps its exact old return shape (`Department`, `total_products`, `image_path`) so neither customer template needed structural changes — see "Explore→Browse" scoping note under Categories Page above for what *was* and wasn't renamed.

**Seed data**: the four sample images the user supplied mid-sprint (Office Supplies, Computer & IT, Kitchen & Dining, Home Appliances) were saved via the real `upsert_department_image()` path (not a raw SQL insert), exercising the actual write path end-to-end. The other 6 catalog departments (Electrical, Electronics, Furniture, Miscellaneous, Safety & Industrial, Sports & Fitness) remain unconfigured — an employee needs to add images for them through the new module before they'll appear on the customer site.

**Public helper promoted**: `product_service._add_primary_images()` was renamed to `add_primary_images()` (dropped the leading underscore) so `customer_service.py` could reuse it for the Featured Products bug fix above, instead of duplicating the batched-image-lookup query a second time.

#### Pre-Commit Fix — Lookup Normalization

Every `Catalog.Department` ↔ `DepartmentImages.DepartmentName` comparison originally used exact string matching. Two different mechanisms were involved and only one was actually safe: SQL `WHERE DepartmentName = %s` happened to ride on the column's case-insensitive collation (`utf8mb4_uca1400_ai_ci`), but every **Python-side** comparison (`get_departments_for_management()`'s dict join, `get_active_department_cards()`'s `counts.get(row["DepartmentName"])`) was a plain case-sensitive, whitespace-sensitive `dict`/`==` lookup — silently dependent on a DB collation setting that nothing enforces will stay that way, and that never accounted for leading/trailing whitespace either way (collation doesn't trim). A `DepartmentImages` row saved with different casing or stray whitespace than the live `Catalog.Department` string would join correctly in the SQL layer but silently fail to join in the Python layer — showing as "Not Configured" in the Employee module, or a `0` product count on the customer site, despite a real row existing.

**Fixed by centralizing normalization in one place**: `department_service._normalise_department_name(name)` (`.strip().lower()`) is now the single comparison key every lookup and write goes through — nowhere else in the codebase does its own case/whitespace handling for department names. Concretely:
- `_find_department_image_row(department_name)` (new, replaces the old exact-match `SELECT ... WHERE DepartmentName = %s`) fetches all `DepartmentImages` rows (a handful of rows — this table will never be large, since it's one row per Catalog department) and matches in Python via the normalized key. Used by both `get_department_for_edit()` and `upsert_department_image()`, so there's one lookup implementation, not two.
- `_get_canonical_department_names()` (new) returns `{normalised_name: real Catalog.Department string}`. Every function that needs to resolve a `DepartmentImages` row back to a real Catalog department — `get_department_for_edit()`, `get_active_department_cards()` — goes through this, so the value that ends up in a `?department=` filter link or gets stored in a new `DepartmentImages` row is always the canonical Catalog casing, never a normalized (lowercased) or otherwise-drifted variant.
- `routes/employee.py:edit_department()` was updated to pass `department["department_name"]` (the canonical name `get_department_for_edit()` already resolved) to `upsert_department_image()`, instead of the raw URL segment — so a newly-created row is always stored with clean Catalog casing regardless of what casing/spacing appeared in the URL.

**No schema change, no new table, no FK, no route/URL change** — exactly as constrained. `DepartmentImages.DepartmentName` itself is still stored verbatim (whatever was canonical at write time); this fix is entirely about how it's *looked up*, not what's stored.

**Verified**: a row was deliberately inserted with mismatched casing and stray whitespace (`'  ELECTRICAL  '` against the real `'Electrical'`) and confirmed to correctly join in the management list, resolve via both canonical and mismatched-case URL input in `get_department_for_edit()` (including live through the actual route, not just the service function), resolve to the canonical name with the correct product count in the customer-facing cards, and get updated in place (not duplicated) by `upsert_department_image()` — then removed before finishing, so the four real seeded departments remain the only rows.

### Sprint 7 — Mobile Responsive Polish (v1.0)

UI-only sprint: no schema changes, no new routes, no backend logic changes, **no new JavaScript files**. Scope was a full mobile responsive audit of the Employee Portal (Dashboard, Products, Product Details, Add/Edit Product, Departments, Department Edit, Inventory Summary, Inventory Transactions, Customers, Enquiries, Invoices, Login), tested at 320/360/375/390/425/768px in a real browser (navigated, not just inspected in DevTools), plus regression at 768/769/992/1280px.

**Highest priority — mobile navigation redesign, zero custom JS.** `templates/components/employee_nav.html` previously rendered its `<ul>` of 8 links as a permanently-visible vertical stack on mobile (`flex-direction: column`, no toggle). Combined with the nav's pre-existing `position: sticky; top: 0`, the full 8-item list stayed pinned to the top of the viewport while scrolling — roughly half the screen on a typical phone — pushing page content below the fold.

**Fix reuses the codebase's existing toggle convention instead of adding a script.** This app already has three working examples of `data-bs-toggle="collapse"` doing exactly this kind of show/hide (the customer navbar's own mobile toggle in `navbar.html`, the Products page's filter-group accordions, and `inventory.html`'s Category Summary toggle, including its `[aria-expanded="true"] i { transform: rotate(...) }` CSS-only icon technique). `employee_nav.html` now follows the same pattern: a compact `.employee-nav-bar` (current-section icon+label, plus a `.employee-nav-toggle` button carrying `data-bs-toggle="collapse" data-bs-target="#employeeNavMenu"`) sits above the `<ul class="employee-nav-list collapse" id="employeeNavMenu">`. Bootstrap's already-loaded Collapse plugin (bundled JS, no new script tag) handles the show/hide, the height transition, and keeps `aria-expanded` in sync on the trigger button — **no `employee_nav.js` was written**; an earlier draft of this fix did add one and it was deliberately removed in favor of this approach once it was clear the architecture didn't need it.

What's still CSS-only, mirroring the same `.category-summary-toggle[aria-expanded="true"]` pattern:
- Hamburger icon rotates 90° when open, keyed off `[aria-expanded="true"]` — no click handler.
- Panel is capped at `max-height: 75vh; overflow-y: auto` so it can never exceed the viewport even if a future item is added (verified at a 320px-tall viewport: correctly clamps to 240px and scrolls internally).
- "Auto-close after navigating" needed no code at all: every nav link is a normal `<a href>` in this server-rendered Flask app, so clicking one is a full page load — the freshly-rendered page always starts with the panel closed.
- **No body-scroll-lock.** Considered and deliberately left out: the panel expands in-flow (see below), not as an overlay, so scrolling the page while it's open is normal and expected, not a bug to prevent. Locking the body would only be justified by a demonstrated problem an overlay-style menu has and this one doesn't.

**Positioning is unchanged from the existing pattern**: the panel expands **in-flow** (pushes subsequent content down, exactly like `navbar.html`'s and `inventory.html`'s own collapses) rather than as an absolutely/fixed-positioned overlay — there is no `position: absolute/fixed`, `z-index`, or backdrop element anywhere in this component. An earlier draft used `position: absolute` for an overlay-style dropdown; it was replaced with this in-flow approach specifically to avoid introducing positioning/z-index behavior that doesn't already exist elsewhere in the codebase.

**Real desktop regression caught during verification, fixed before shipping**: giving the `<ul>` Bootstrap's `collapse` class means it also inherits Bootstrap's own `.collapse:not(.show) { display: none }` rule, which has higher CSS specificity (two classes + `:not()`) than a plain `.employee-nav-list { display: flex }` class rule. Left alone, that would hide the entire nav on desktop too, any time the panel wasn't in its (irrelevant-on-desktop) "open" state. Fixed **without introducing a new breakpoint number**: `#employeeNavMenu { display: flex; }` (outside any media query) uses the element's existing `id` — an id selector always outranks Bootstrap's class-only rule, regardless of source order, so the nav is unconditionally visible by default. The existing `max-width: 768px` query (the one breakpoint this entire file, and every other employee page, already standardizes on) then reinstates the real closed state on mobile only, via `#employeeNavMenu.collapse:not(.show) { display: none; }` — three selector parts including the id, which outranks the unconditional rule within that same query. No `min-width` query, no `769`, no `!important` anywhere in the file. This also sidesteps a boundary bug a naive `min-width: 768px` companion query would have caused (double-matching at exactly 768px against the existing `max-width: 768px` block). Confirmed via computed-style checks at 768/769/992/1280px and a visual screenshot diff against the pre-sprint desktop layout (pixel-identical) before considering this done.

**Touch targets.** Every real `<button>`/`.btn`/pagination control across the portal now has an explicit `min-height: 44px` (`width`/`height: 44px` for square icon buttons) inside each page's own existing mobile media query — nav links and toggle, all four pages' pagination controls, search/reset/refresh buttons, `Add Product`, Save/Cancel and Review Transaction/Cancel button rows, the searchable-select suggestion list items, modal Close buttons (text and `.btn-close` icon), the Category Summary toggle, Edit/Delete Product, and the Departments "Show on customer website" checkbox row (checkbox itself enlarged to `1.3em`, its full row padded to a 48px tap target). This is scoped to actual buttons/toggles, not text `<input>`/`<select>` fields, which keep Bootstrap's default control height — resizing every form field was judged a much larger, unrequested visual change for a requirement that specifically named buttons. One deliberate, documented exception: the per-thumbnail gallery delete button on Product Details (Admin only) was bumped from 22px to 30px rather than 44px — at 44px it would cover most of a compact thumbnail and increase the risk of deleting the wrong image; the trade-off is called out inline in `product_details.html`'s CSS.

**One-handed forms.** Add/Edit Product's Save/Cancel, Department Edit's Save/Cancel, and Inventory Transaction's Review Transaction/Cancel now stack to full-width, one-per-row on mobile (`flex-direction: column` + `width: 100%` on each `.btn`), matching the Products page search form's own pre-existing full-width-stacked convention rather than inventing a new one. The Inventory Transaction type selector (Stock In/Stock Out/Adjust Stock) already stacked full-width from an earlier sprint; it now also meets the 44px minimum.

**Mobile spacing/typography consistency.** Every other employee list/detail page already shrinks its `h1` to `1.3rem` under 768px (Products, Departments, Customers, Enquiries, Inventory); the three form-card pages (`product_form.html`, `department_form.html`, `inventory_transaction.html`) had been missed and still showed a full `1.6rem` desktop heading on mobile. Now consistent at `1.3rem` across all three. Content padding (`1rem` on mobile) was already uniform across every page and needed no change.

**Full responsive audit findings, beyond the nav.**
- **Pagination didn't wrap.** `.pagination` in `products.html`, `customers.html`, `enquiries.html`, and `inventory.html` (both of its independently-paginated Low Stock / Out of Stock lists share the class) used `display: flex` with no `flex-wrap`, producing genuine page-level horizontal overflow on a list with enough pages (confirmed via `scrollWidth`: 326px of content in a 320px viewport). Fixed with `flex-wrap: wrap` plus explicit 44px pagination buttons (superseding an initial pass that shrank them to 36px to fit more per row — reverted once the 44px touch-target requirement made that the wrong trade-off; wrapping to an extra row is the correct fix, not shrinking below 44px). Desktop pagination sizing is untouched.
- **A second, pre-existing horizontal-overflow source, in scope once "no horizontal scrolling anywhere" was made explicit**: at exactly 320px, Bootstrap's own `.navbar-brand { white-space: nowrap }` (inherited by the tagline text) made the sitewide customer navbar's brand lockup a few pixels wider than the viewport, on every page including all Employee Portal pages. Fixed with a minimal, mobile-only addition to `navbar.css` (`@media (max-width: 350px)`) letting the tagline wrap and the text column shrink — engages only below 350px, verified to change nothing at 360px and up.
- **Everything else already handled itself correctly**: every data table already sits inside an `overflow-x: auto` container; spec rows, image uploads, and the transaction form already stacked to one column; card grids already collapsed to one column. The real gaps were specifically the nav, pagination wrap, touch targets, and the three form pages' missed mobile heading/button rules — not a systemic problem with the per-page CSS convention.

**Regression tested**: Dashboard, Products (incl. deep pagination), Customers, Enquiries, Inventory Summary (incl. Category Summary collapse, both independent paginations), Inventory Transaction, Departments, Department Edit, Add/Edit Product, Product Details, Invoices, Login — at 320/360/375/390/425/768/769/992/1280px. No console or server errors at any width. Desktop confirmed pixel-identical to pre-sprint (including the collapse-specificity bug caught and fixed before it could ship).

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

Users, Catalog, ProductImages, Enquiries, StockHistory, DepartmentImages. Additional tables should follow existing naming conventions.

### Product-to-Image Relationship

Images are NOT stored inside Catalog.

Catalog.ProductID → ProductImages (ImageID, ProductID, ImageURL, UploadDate). One Product → Many Images.

### Inventory Audit Table (StockHistory)

`StockHistory` (`database/schema/008_create_stockhistory.sql`) is the **permanent** inventory audit/history table for v1.0 — do not create a separate inventory log table, and do not rename it. It existed since v0.9 but had never been written to or read from by any route or service (verified by grep before extending it) - it was pure unused schema until v1.0 Sprint 5.

**Extended in `009_alter_stockhistory_add_transaction_columns.sql`** (v1.0 Sprint 5 foundation, applied before any Stock In/Stock Out logic was written) with four new columns, added additively - no existing column, data, or the table's name was touched:
- `TransactionType` (`VARCHAR(50)`, nullable) - the kind of movement (e.g. Stock In / Stock Out / Adjustment); exact values are a future sprint's decision, not fixed here.
- `QuantityChanged` (`INT`, nullable) - signed net change, complementing the existing `OldStock`/`NewStock` snapshot pair. **Not backfilled** for any historical row (there were none - table was empty) and won't be computed retroactively from `OldStock`/`NewStock` either, per "do not modify existing data."
- `ReferenceType` / `ReferenceID` (`VARCHAR(50)` / `INT`, both nullable) - a polymorphic pointer back to whatever business event caused the change (e.g. a future PurchaseOrder or SalesInvoice row). Deliberately has no foreign key, since which table `ReferenceID` points to depends on `ReferenceType` - a single FK constraint can't target more than one table.

**Indexes added**: `idx_stockhistory_productid` (ProductID), `idx_stockhistory_employeeid` (EmployeeID), `idx_stockhistory_reference` (ReferenceType, ReferenceID) - one for each query shape future Stock In/Stock Out screens will need (history for one product, one employee, or one originating reference). Verified none of these existed before adding them (the table only had its PRIMARY KEY).

**Foreign key added on EmployeeID only, deliberately NOT on ProductID.** `StockHistory.EmployeeID` now has `FOREIGN KEY ... REFERENCES Employees (EmployeeID)`. `ProductID` intentionally does **not** get a foreign key to `Catalog.id`, to stay consistent with an existing, deliberate pattern already followed by `ProductImages`, `ProductDetails`, and `Enquiries`: none of those reference `Catalog.id` with a real constraint either, because `Catalog` is shared with the independently-deployed Receipt Generator project (see Employee Invoice Generator Bridge) and this project doesn't own it exclusively. Employees is fully internal, and `Employees.UserID → Users.UserID` already establishes FK usage as the norm for internal-only relationships, so the new `EmployeeID` FK extends that convention rather than introducing a new one. **Follow this same asymmetry (FK to internal-only tables, no FK to Catalog) for any future table that also references both.**

Migration convention used: a new numbered file appended to `database/schema/` (`009_...`), following the same sequential-file convention as `001`-`008`, applied directly against the target database (same process already used for the original schema - see Deployment Lessons above) rather than introducing a new migration-runner tool. `README.md`/`DEPLOYMENT.md`'s "import 001 through NNN" instructions were updated to reference `009`.

**Update (v1.0 Sprint 5.1):** implemented. `StockHistory` is now actively written to by `services/product_service.py:apply_stock_transaction()` (Stock In/Stock Out/Adjustment) — see the Sprint 5.1 write-up under Employee Inventory Summary Module below for the full detail, including a schema-drift discovery (the live column defaults for `TransactionType`/`QuantityChanged`/`ReferenceType` no longer matched this migration file, and the file was updated to match reality rather than the drift being reverted).

### Category Images

Categories should never have dedicated images. Instead, each category automatically displays one representative image from a product belonging to that category. No CategoryImages table should be created.

**Still true, and distinct from Department Images below — do not conflate the two.** This rule is about `Catalog.category` (the finer-grained field, e.g. "Counter Chair (Bar / Pub)") and remains unimplemented/unneeded as stated. `DepartmentImages` (Department Image Management, new) is about the coarser `Catalog.Department` field (e.g. "Furniture") and is a deliberate exception created for the customer site's department showcase section - the two fields, and their image conventions, are independent decisions.

### Department Images

`DepartmentImages` (`database/schema/010_create_departmentimages.sql`, Department Image Management) is presentation-only data for `Catalog.Department` values — one row per department, matched by `DepartmentName` (`UNIQUE`), never a foreign key (`Catalog.Department` is free text with no id of its own).

```
DepartmentImages
----------------
DepartmentID      INT AUTO_INCREMENT PRIMARY KEY
DepartmentName    VARCHAR(100) NOT NULL UNIQUE
ImageFilename     VARCHAR(255) NOT NULL
DisplayOrder      INT NOT NULL DEFAULT 0
IsActive          BOOLEAN NOT NULL DEFAULT TRUE
```

One table only — no separate `Departments` table, no per-department image history. `Catalog.Department` remains the sole source of truth for product classification; a department can exist in `Catalog` with no `DepartmentImages` row (shows as "Not Configured" in the Employee Departments module, not shown at all on the customer site), but a `DepartmentImages` row can never exist for a department that isn't in `Catalog` (enforced by the edit route validating against `get_catalog_department_names()`, not by a DB constraint). See Department Image Management above for the full service/route/template detail.

### Image Storage

Images should be stored inside `static/uploads/products/`.

Recommended structure: `static/uploads/products/<ProductID>/image1.jpg`, `image2.jpg`, ...

**Department images are the one exception**: `static/uploads/departments/<filename>` — flat, not per-department subfolders, since each department has exactly one image (no gallery), and `DepartmentImages.ImageFilename` stores a bare filename rather than a relative path (unlike `ProductImages.ImageURL`).

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

## Customer Module Data Source

Current implementation intentionally derives customers from the Enquiries
table because the Customers table exists in schema but has no write path.

Current flow:

Customer Enquiry
        │
        ▼
 Enquiries Table
        │
        ▼
 Employee Customers Module

Future milestone:

When customer registration/account creation or automatic customer creation
is implemented, migrate the Employee Customers Module to use the Customers
table as the authoritative data source.

Future architecture:

Customers
    │
    ├── Employee Customers Module
    ├── Customer Login
    └── Enquiries (linked via CustomerID)

This migration should only affect the service layer.
Dashboard, UI, pagination, search, and modal should remain unchanged.


## HostyCare Compatibility

Passenger on HostyCare passes PATH_INFO still percent-encoded.
passenger_wsgi.py contains a small middleware that decodes PATH_INFO
before Flask routing.

This workaround is production-only and does not affect local
development.

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

HostyCare's Passenger/LiteSpeed hands Flask a still percent-encoded `PATH_INFO` (e.g. `Computer%20&%20IT` instead of `Computer & IT`) instead of decoding it first, as WSGI/PEP 3333 requires (a known Passenger bug, [phusion/passenger#1828](https://github.com/phusion/passenger/issues/1828)). Route segments containing spaces or other percent-encoded characters therefore arrive at view functions still encoded, breaking lookups like `get_department_for_edit()`. `passenger_wsgi.py` wraps the app in a small `PassengerPathFix` middleware that decodes `PATH_INFO` once before Flask routing runs. This is production-only: `passenger_wsgi.py` is never executed by the Flask development server, which already receives correctly-decoded paths.

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

✓ Customer List
✓ Customer Details
✓ Customer Search
□ Customer Notes
□ Customer Management Dashboard

## v0.9.5 — Employee Enquiry Management

Customer:
✓ Submit Product Enquiry
✓ Contact Form
□ Enquiry Tracking

Employee:
✓ View Enquiries
□ Update Status
✓ Search (Filters not built — Enquiries has no dedicated filter dropdowns, only text search)
□ Dashboard Widgets (the Dashboard's Operations panel shows a static "Recent Enquiries" empty state, not real widget data — see Employee Enquiries Module)

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
✓ Inventory Dashboard Foundation (Sprints 1–3, read-only — see Employee Inventory Summary Module)
✓ Inventory Transactions (Sprint 5.1, write-capable — Stock In/Stock Out/Adjustment, see Employee Inventory Summary Module)

System:
✓ Responsive UI (Employee Portal — Sprint 7, see Sprint 7 — Mobile Responsive Polish; Customer Website responsive work was covered earlier under Phase 2 — Customer Experience)
□ Production Security
□ Automated Testing
□ Documentation
□ Stable Deployment

## Future Roadmap (Post v1.0.0)

Invoice Generator Integration — remains an independent project until after Sridevi Enterprises reaches a stable v1.0.0 release. (As of v1.0 Sprint 3, "Invoice Generator" is the Employee Portal's display name for this bridge; the external project itself is still actually named "Receipt Generator" — see Employee Invoice Generator Bridge above.)

Current state:

Employee Portal launches the independent invoice-generation project
through a configurable URL.

Future state (v1.0+):

Single Sign-On (SSO)

↓

Employee Portal authentication

↓

Trusted launch token

↓

Invoice Generator automatically authenticates
the employee.

Goal:

Employees should never have to log in twice.

Invoice Generator

## Product Management Roadmap

□ **Soft Delete Product** (added during the Department Image Management sprint, not implemented). Products should never be permanently removed from the database. A future sprint should replace `delete_product()`'s current hard `DELETE FROM ProductDetails/ProductImages/Catalog` (see Product Deletion above) with an archive/deactivate flow — likely a status flag on `Catalog` (schema change, out of scope for this note) rather than actually removing rows — that preserves:
  - Product history (the Catalog row itself)
  - Inventory history (`StockHistory` rows referencing the product — these would orphan or lose meaning if the product row disappeared)
  - Customer enquiries (`Enquiries.ProductID` rows referencing the product)
  - Invoice references (once the Invoice Generator integration deepens beyond a launch-only bridge — see Employee Invoice Generator Bridge — any future invoice line pointing at a `Catalog.id` needs that id to keep existing)

  No hard `DELETE` operation should be introduced anywhere else in the codebase in the meantime, and the existing Delete Product route should be migrated to this pattern rather than extended further as-is.

## Future Improvements

□ Recent invoices
□ Invoice search
□ Open last invoice
□ Sales summary
□ Invoice history
□ Launch with selected customer
□ Launch with selected products

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

---

#### Technical Debt (Post-v0.9)

The following are intentional architectural conventions and should be
revisited only if they become maintenance burdens:

- Per-page inline CSS for Employee modules
- Repeated authentication guards in employee routes
- Standalone Invoice Generator integration (bridge architecture)
- Customer module currently derived from Enquiries until the Customers
  table receives a write path

----

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
