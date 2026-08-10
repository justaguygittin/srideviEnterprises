# Release Notes — v1.0.0

**Sridevi Enterprises** · Furniture • Electronics • Home Appliances
First public release.

A Flask + MariaDB showroom management system: a customer-facing digital showroom and an
internal employee portal for products, inventory, departments, customers, and enquiries.

The website is a **digital showroom, not an e-commerce site**. No prices, carts, or
payments appear anywhere on it — customers browse and submit enquiries.

For the itemised change list, see [CHANGELOG.md](CHANGELOG.md).

---

## What's in v1.0.0

**Customer website** — homepage with featured departments and products; product listing
with search, filters, sorting, and pagination; product details with an image gallery and
specifications; department browsing; product and general enquiry forms; branded error
pages; and a dedicated Maintenance Mode screen.

**Employee portal** — session-based login with Employee/Admin roles; a dashboard with live
counts and system status; full product management including images and specifications;
product deactivate/restore (soft delete); an inventory dashboard with low-stock and
out-of-stock tracking; Stock In/Out/Adjustment transactions with an audit trail; department
image management; read-only customers and enquiries; and Administrator control of
Maintenance Mode.

**Operations** — a `/health` liveness endpoint reporting version and Maintenance Mode
state; config-file-based Maintenance Mode with a bypass key for staff verification;
application logging; hardened session cookies; and a documented, verified deployment
workflow.

---

## Upgrading

**There is nothing to upgrade from.** v1.0.0 is the first release. Follow
[DEPLOYMENT.md](DEPLOYMENT.md) § 1 for a first-time install.

If you are creating the production database, import **every** file in `database/schema/`
in numeric order — `001` through `011` — and run the verification queries in § 1.4 before
continuing. Skipping `010` or `011` produces a database the application cannot run
against.

Before announcing the site, complete **§ 7.1 Business Configuration Verification**. The
application deliberately renders nothing where contact details are unset, so a deployment
can go live with no address or phone number and nothing will look broken.

---

## Known limitations

### CSRF protection is not implemented

**This is the most significant limitation in this release, and it was a deliberate
decision rather than an oversight.**

Every write endpoint — product create/edit, image delete, product deactivate/restore,
inventory transactions, and the Administrator Maintenance Mode toggle — could in principle
be triggered from another site using an already-authenticated Administrator's browser
session.

**What reduces the risk today:**

- Session cookies are set with `SameSite=Lax`, which causes browsers to withhold the
  session cookie on cross-site `POST`/`PUT`/`DELETE` — the exact shape such an attack
  takes.
- Every write endpoint is POST-only and requires authentication.
- All destructive actions (deactivate, restore, delete image, maintenance toggle) are
  additionally restricted to Administrators.

**Why this is a mitigation and not a fix:** it relies on the browser behaving correctly,
rather than on the application verifying that a request genuinely originated from its own
forms.

**Why it was deferred:** adding CSRF tokens touches every form in the application. Doing
that during a release-candidate freeze would have meant re-verifying every write path at
exactly the moment the sprint existed to stabilise them.

**Planned for v1.1:** a session-derived CSRF token validated in a single `before_request`
hook for state-changing methods, plus a hidden field in each form. `SameSite=Lax` stays in
place alongside it.

**Practical advice for v1.0.0:** Administrators should not remain logged into the Employee
Portal in the same browser session while browsing untrusted sites. Logging out when
finished fully removes the exposure.

### Other known limitations

| Limitation | Detail |
|---|---|
| No automated test suite | Verification was performed with purpose-built harnesses that live outside the repository |
| Enquiry status is read-only | `Enquiries.Status` is displayed but cannot be updated from the portal |
| No Employee CRUD | Employee and user accounts are managed directly in the database |
| Customers module is derived | The `Customers` table exists but has no write path; the module groups `Enquiries` by email |
| Product Comparison absent | The placeholder route was removed in this release |
| 400 / 405 / 413 pages unbranded | 403, 404, 500, and 503 are branded; these three fall through to Werkzeug's default page |
| Some touch targets are 31–38px | Below the 44px standard the project applies elsewhere; affects some customer-site buttons and the Admin maintenance toggle |
| No connection pooling | `database/db.py` opens one connection per query — appropriate at current scale |
| Minimal indexing | Only primary keys on the main tables; appropriate for a ~315-product catalog |

None of these block release. All are recorded in `AI_CONTEXT.md` under **v1.1 — Deferred
From v1.0.0**.

---

## Operational notes

- **`SESSION_COOKIE_SECURE` must be `True` in production.** `.env.example` ships it as
  `False` for local HTTP development — it is the one value in that template deliberately
  less safe than the application's own default. The app logs a warning on every startup
  while it is disabled.
- **Maintenance Mode takes effect immediately** — no restart needed, because the config
  file is read fresh on every request. Administrators can toggle it from the dashboard.
- **`.env` changes require a Passenger restart**; they are read once at process start.
- **Check the logs first.** Failed writes are logged at `ERROR` with a full traceback.
  `grep "FAILED"` in the cPanel Python app error log is the fastest first step for any
  reported problem. See DEPLOYMENT.md § 4.1.
- **Customer personal data is never logged.** A failed enquiry records that it failed and
  why, but not who submitted it. The enquiry is genuinely lost in that case.

---

## Credits

**Srikar** — Sridevi Enterprises Development Project
