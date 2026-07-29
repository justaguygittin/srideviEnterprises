# AI_CONTEXT.md

# Sridevi Enterprises
Current Version: v0.7.0 — Employee Product Management (complete)

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

□ Product Details Improvements
□ Product Image Gallery
✓ Category Landing Pages — premium `/categories` browsing page, see Categories Page above
□ Search Improvements
□ Homepage Improvements
□ Responsive UI Polish

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
