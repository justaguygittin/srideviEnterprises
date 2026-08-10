# Changelog

All notable changes to Sridevi Enterprises are recorded here.

This project uses [Semantic Versioning](https://semver.org/). The authoritative
version string is `Config.APP_VERSION` in `config.py`, surfaced at runtime via
`GET /health` and on the Employee Dashboard's System Status panel.

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
