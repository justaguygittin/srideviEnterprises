# Changelog

All notable changes to Sridevi Enterprises are recorded here.

This project uses [Semantic Versioning](https://semver.org/). The authoritative
version string is `Config.APP_VERSION` in `config.py`, surfaced at runtime via
`GET /health` and on the Employee Dashboard's System Status panel.

---

## [Unreleased]

`Config.APP_VERSION` unchanged (`v1.1.0`).

### Added

- **WhatsApp click-to-chat** — a floating WhatsApp button on customer-facing
  pages and an "Enquire on WhatsApp" button on the Product Details page, both
  plain `wa.me` links. No API, database change, or new dependency. See
  `AI_CONTEXT.md` → "WhatsApp Click-to-Chat (Stage 1 + Stage 2)".
- `WHATSAPP_BUSINESS_NUMBER` / `WHATSAPP_DEFAULT_MESSAGE` in `.env`
  (`config.py`). A missing or invalid number hides every WhatsApp element.
- `services/whatsapp_service.py`, `templates/components/whatsapp_button.html`,
  `static/css/components/whatsapp_button.css`.
- `/whatsapp` and `/products/<id>/whatsapp` redirect routes — the buttons link
  to these instead of `wa.me`, so the configured number never appears in page
  HTML; it is revealed only by the redirect when a customer clicks.

- **Product price on Add/Edit Product** — required "Price (₹, incl. GST)" field
  saved to the existing `Catalog.offer_price` (per model), so newly created
  products no longer bill at ₹0. Never shown on the public site.
- **GST rate on Add/Edit Product** — required "GST Rate (%)" field saved to the
  existing `Catalog.gst_percent` (0–100, no default), so new products no
  longer bill at 0% GST. Existing rates are preloaded when editing.
- **Editable invoice row prices** — the Invoice Generator's Price column is
  pre-filled from the catalog but can be overridden per row; totals, GST and
  amount in words use the row price. The catalog price is never changed.
- **"Consignee details same as buyer"** checkbox on the Invoice Generator.

### Fixed

- **Multi-model products can be edited again** — the Add/Edit Product duplicate
  check compared the product name alone, so the 32 rows that share a name with
  another model could not be saved. A duplicate is now the same name + brand +
  model; editing without changing those is never blocked.

### Changed

- `.env.example` — the `SELLER_GSTIN` / `SELLER_BANK_*` / `SELLER_IFSC` lines
  held real-looking values; replaced with clearly fake placeholders.

---

## [v1.1.0] — 2026-09-13

Two change-sets, released together: a stabilization pass (Sprint 12) and the
Invoice Generator Module merge. `Config.APP_VERSION` bumped from `v1.0.0`.

### Invoice Generator Module (Merge)

Reverses the Sprint 12 entry immediately below, which scoped the Invoice
Generator module out. It is now in: the standalone Receipt Generator project
has been merged into this application as `routes/receipts.py`, mounted at
`/employee/invoices`. See `AI_CONTEXT.md` → "Invoice Generator Module (Merge)"
for the full detail.

#### Added

- **Invoice Generator module** — Buyer/Consignee entry, multi-product GST
  invoices (CGST+SGST for intra-state, IGST for inter-state), PDF generation,
  and invoice history, generated from and validated against the existing
  `Catalog` table, behind the existing employee session/auth.
- `services/gst_service.py`, `services/invoice_service.py`,
  `services/pdf_service.py`, `routes/receipts.py`.
- `Invoices` / `InvoiceItems` tables (`database/schema/013_create_invoices.sql`,
  `014_create_invoiceitems.sql`).
- `templates/employee/invoice_history.html`, `invoice_form.html`,
  `invoice_view.html`, `templates/invoice_pdf.html`.
- `Config.SELLER_GSTIN` / `SELLER_BANK_ACCOUNT` / `SELLER_BANK_NAME` /
  `SELLER_IFSC` — printed on the generated invoice; reuses the existing
  `Config.BUSINESS_ADDRESS`/`BUSINESS_PHONE` rather than duplicating them.
- `num2words` and `playwright` added to `requirements.txt` — PDF generation
  uses Playwright's headless Chromium, not the standalone project's xhtml2pdf.

#### Removed

- The Employee Portal's launch-only external bridge to the standalone Receipt
  Generator project (`templates/employee/invoices.html`, the old
  `routes/employee.py:invoices()` view). `Config.INVOICE_GENERATOR_URL` /
  `RECEIPT_GENERATOR_URL` are left defined but deprecated - nothing reads them
  any more.

### Sprint 12: Production Stabilization

First sprint on the `v1.1-development` branch, after the v1.0.0 release. A
stabilization/hardening pass, not a feature sprint — CSRF implementation and
Admin Settings remain explicitly out of scope. (The Invoice Generator module
was scoped out here too, at the time this sprint was written; see the entry
above this one — that decision was later revisited.)
See `AI_CONTEXT.md` → "Sprint 12 — Production Stabilization (v1.1)" for full detail.

#### Added

- **Branded 413 (Payload Too Large) error page**, matching the existing
  403/404/500/503 visual language. 400 and 405 remain deferred (unbranded).
- **Favicon**, reusing the existing brand logo — closes a TODO open since
  `base.html` was first written.
- **`database/schema/012_add_performance_indexes.sql`** — indexes on
  `Catalog.Department`/`category`/`brand` and
  `ProductImages`/`ProductDetails.ProductID`, the columns behind every product
  listing/filter/detail query, which had only primary keys before this file.

#### Fixed

- **`.env.example` no longer carries real-looking business details.** The
  v1.0.0 RC commit had replaced the generic placeholder address/phone/email
  with what read as the actual showroom's contact information, which silently
  broke DEPLOYMENT.md §7.1's own placeholder-search verification step (it was
  searching for strings that no longer existed anywhere in the template).
  Reverted to generic placeholders; the real `.env` was never affected.

#### Removed

- Two unreferenced placeholder image variants
  (`static/images/products/placeholde.webp`, `placeholder.webp.png`) and four
  0-byte category stub images already superseded by Department Image
  Management (`static/images/categories/*.jpg`). Confirmed unreferenced by
  grep before deletion.

---

## [v1.0.0] — 2026-08-08

First public release. The Release Candidate sprint added no features; it audited,
fixed, hardened, and documented what was already built.

### Added

- **Application logging.** Timestamped, levelled logs to stderr (captured by
  Passenger into the cPanel error log). Format: `timestamp · level · [module:pid] ·
  message`. Configurable via `LOG_LEVEL` (default `INFO`). Every write operation and
  every failure is recorded; read-only page views log nothing. Customer personal data
  is never written to the log.
- **Session cookie hardening.** `HttpOnly`, `SameSite=Lax`, and `Secure` (default
  `True`, with an explicit `SESSION_COOKIE_SECURE` opt-out for local HTTP
  development). A startup warning is logged whenever `Secure` is disabled.
- **Configurable business details.** `BUSINESS_ADDRESS`, `BUSINESS_PHONE`,
  `BUSINESS_EMAIL`, `BUSINESS_WEBSITE`, and `BUSINESS_HOURS` now drive the site
  footer, the Contact page, and the Maintenance Mode screen from one source.
- **Fresh-install verification step** in DEPLOYMENT.md § 1.4, and a **Business
  Configuration Verification** checklist in § 7.1.
- **Application Logs** operations guide, DEPLOYMENT.md § 4.1.
- `CHANGELOG.md` and `RELEASE_NOTES.md`.

### Fixed

- **A brand-new installation was broken by the documentation.** README and
  DEPLOYMENT instructed importing schema files `001`–`009`, omitting
  `010_create_departmentimages.sql` and `011_alter_catalog_add_soft_delete.sql`.
  The resulting database had no `DepartmentImages` table and no `Catalog.IsActive`
  column, against which essentially every page fails.
- **Employee Dashboard and Inventory Summary returned HTTP 500 on an empty
  catalog.** An unfiltered `SUM()` over zero rows returns `NULL`, not `0`, so
  `int(None)` raised. Every brand-new installation hit this until the first product
  was added. *(Found by the fresh-install simulation, not by code review.)*
- **`001_create_catalog.sql` created the table as `catalog`, lowercase**, while every
  query in the application uses `Catalog`. Harmless on Windows/macOS, where MariaDB
  folds table names; on Linux — the deployment target — names are case-sensitive by
  default, so a fresh install would have failed on every page. Affects newly created
  databases only.
- **Product Details page scrolled sideways on mobile** (12px horizontal overflow at
  320/375/425px), caused by Bootstrap's `.g-5` gutter exceeding its container's
  padding. Invisible to the eye, but the whole page moved.
- **Silent failures across six write paths.** Product create/update, product
  deactivate/restore, department save, and — most importantly — **customer enquiry
  submission** caught their exceptions, showed a generic message, and discarded the
  error entirely. A failed enquiry is a lost sales lead; nothing anywhere recorded
  that it had happened.
- Footer and Contact page disagreed on the business email address and the opening
  hours.

### Changed

- `Config.APP_VERSION` is now a semantic version (`v1.0.0`) instead of a per-sprint
  label (`Sprint 10`).
- `/health`'s documented example uses `<Config.APP_VERSION>` rather than a hardcoded
  version, so it cannot go stale.
- README rewritten to describe the actual v1.0 feature set, with a Known Limitations
  section.

### Removed

- **The `/compare` placeholder route.** It returned an unstyled
  `<h2>Compare - Coming Soon</h2>` at a public URL. `/compare` now serves the branded
  404 page. Product Comparison remains unimplemented.

### Security

- Session cookies are `HttpOnly`, `SameSite=Lax`, and HTTPS-only by default (see
  Added).
- **CSRF protection is NOT implemented in v1.0.0** — deliberately deferred to v1.1.
  See [RELEASE_NOTES.md](RELEASE_NOTES.md) for the full decision, what mitigates it
  today, and what v1.1 will do.

---

## Earlier development

v1.0.0 is the first released version. Development before it ran through internal
sprints, summarised below; see `AI_CONTEXT.md` for the full record of each.

| Milestone | Delivered |
|---|---|
| Sprint 10 | Administrator Maintenance Mode controls |
| Sprint 9 | UI stabilisation; SQL `LIKE` wildcard escaping; loading states |
| Sprint 8 | Maintenance Mode, `/health`, branded error pages |
| Sprint 7 | Product lifecycle (soft delete); Employee Portal mobile responsiveness |
| Sprint 5.1 | Inventory transactions (Stock In / Out / Adjustment) |
| Sprints 1–3 | Inventory dashboard foundation; invoice terminology |
| v0.9.0 | Employee Portal: customers, enquiries, invoice bridge |
| v0.8.0 | Deployment preparation; customer experience |
| v0.7.0 | Employee product management |
