# Sridevi Enterprises

> **Furniture • Electronics • Home Appliances**

A Flask + MariaDB showroom management system for Sridevi Enterprises: a customer-facing
digital showroom, plus an internal employee portal for product, inventory, department,
customer, and enquiry management.

Current Version: **v1.0.0**

The website is a **digital showroom, not an e-commerce site** — it displays products and
collects enquiries. No prices, carts, or payments appear anywhere on it.

| | |
|---|---|
| Architecture, RBAC, and development rules | [AI_CONTEXT.md](AI_CONTEXT.md) |
| Deploying and operating in production | [DEPLOYMENT.md](DEPLOYMENT.md) |
| Release history and known limitations | [CHANGELOG.md](CHANGELOG.md) · [RELEASE_NOTES.md](RELEASE_NOTES.md) |
| Database tables and schema files | [database/README.md](database/README.md) |

---

## Features

### Customer Website

- **Homepage** — hero, quick actions, featured departments slider, featured products,
  popular brands, about, and location sections
- **Products** — search, filter by department / category / brand / availability, sorting,
  removable filter chips, and pagination, with a responsive filter sidebar that becomes a
  drawer on mobile
- **Product details** — image gallery with click-to-swap thumbnails, specifications,
  availability badge, and similar products
- **Departments** — a browsable department landing page with live client-side search
- **Enquiries** — per-product enquiry form and a general contact form, both validated
- **Branded error pages** — 403, 404, and 500
- **Maintenance Mode screen** — a dedicated, link-free 503 page

### Employee Portal

- **Authentication** — session-based login/logout with hashed passwords and role-based
  access control (Employee / Admin)
- **Dashboard** — live product, enquiry, customer, and inventory counts; recent enquiries;
  quick actions; and a System Status panel reporting version, database, health, and
  Maintenance Mode state
- **Products** — list with search, filters, status tabs, and pagination; add and edit
  products; manage specifications
- **Product images** — upload, add, and replace images; delete images *(Admin)*; a product
  can never be left with no image
- **Product lifecycle** — deactivate and restore products *(Admin)*. This is a **soft
  delete**: deactivated products vanish from the customer site but keep their images,
  specifications, stock history, and enquiries. There is no hard `DELETE` anywhere in the
  codebase
- **Inventory** — summary dashboard with per-department and per-category breakdowns, plus
  low-stock and out-of-stock lists
- **Inventory transactions** — Stock In, Stock Out, and Adjustment, each writing an audit
  row to `StockHistory` atomically with the stock change, with server-side guards against
  negative stock
- **Departments** — manage the images and display order shown on the customer site
- **Enquiries and Customers** — read-only lists with search, pagination, and detail views
- **Maintenance Mode control** *(Admin)* — take the customer site offline and bring it back
  from the dashboard, with no SSH or file editing
- **Invoice Generator bridge** — a configurable launch link to the separately hosted
  invoice-generation project

### Operations

- `GET /health` — liveness endpoint reporting status, Maintenance Mode state, and version
- **Maintenance Mode** — config-file based, with a bypass key so staff can verify the live
  site while the public sees HTTP 503
- **Application logging** — timestamped, levelled logs to stderr; every write and every
  failure is recorded, and no customer personal data is ever logged
- **Hardened sessions** — `HttpOnly`, `SameSite=Lax`, and HTTPS-only cookies by default
- **Mobile responsive** — verified from 320px upward across both portals

---

## Requirements

- Python 3.x
- MariaDB
- See [requirements.txt](requirements.txt) for pinned Python packages

---

## Installation

### Clone the repository

```bash
git clone <repository-url>
cd srideviEnterprises
```

### Create and activate a virtual environment

```bash
python -m venv venv
```

Windows:

```bash
venv\Scripts\activate
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Create the database

Import **every** file in `database/schema/`, in numeric order, from
`001_create_catalog.sql` through `011_alter_catalog_add_soft_delete.sql`.

Order matters — later files add foreign keys and columns to tables the earlier ones
create. **Do not stop early or skip a file:** a partial import produces a database the
application cannot run against. Verify with `SHOW TABLES;` (expect 9) and confirm
`Catalog` has the `IsActive`, `DeletedAt`, and `DeletedBy` columns.

### Configure environment variables

```bash
cp .env.example .env
```

Then edit `.env`:

| Variable | Purpose |
|---|---|
| `DB_HOST` · `DB_PORT` · `DB_NAME` · `DB_USER` · `DB_PASSWORD` | MariaDB connection |
| `SECRET_KEY` | Session signing secret — generate a long random value |
| `FLASK_DEBUG` | `False` everywhere except deliberate local debugging |
| `SESSION_COOKIE_SECURE` | `False` for local HTTP development; **`True` in production** |
| `LOG_LEVEL` | `DEBUG` / `INFO` / `WARNING` / `ERROR` (default `INFO`) |
| `BUSINESS_ADDRESS` · `BUSINESS_PHONE` · `BUSINESS_EMAIL` · `BUSINESS_WEBSITE` · `BUSINESS_HOURS` | Public contact details shown in the footer, Contact page, and Maintenance screen |
| `INVOICE_GENERATOR_URL` | Optional link to the external invoice project |

The values in `.env.example` are **development placeholders**. Production values are
supplied in the server's own `.env` — see [DEPLOYMENT.md](DEPLOYMENT.md) § 1.5. Any
business detail left blank is omitted from the page rather than shown as a placeholder.

### Configure Maintenance Mode

```bash
cp config/maintenance.example.json config/maintenance.json
```

Set a real `maintenance_key`. Both `.env` and `config/maintenance.json` are gitignored and
never committed.

---

## Running Locally

```bash
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000). The Employee Portal is at
`/employee/login`.

> **Note:** `FLASK_DEBUG=False` disables Jinja template auto-reload, so template and route
> edits require restarting the server — a browser refresh alone will silently serve the
> previously compiled template.

---

## Project Structure

```
app.py                  Application entry point, logging, error handlers, Maintenance gate
config.py               Configuration loaded from .env
passenger_wsgi.py       Production WSGI entry point (Passenger)
routes/                 Request handling only — never contains SQL
services/               Business logic, validation, and SQL
database/               Connection helpers and the canonical schema files
templates/              Jinja2 templates (customer, employee, components, errors, layout)
static/                 CSS, JavaScript, images, and uploads
```

The layering is **Routes → Services → Database Helper → MariaDB**, and is never bypassed.
See [AI_CONTEXT.md](AI_CONTEXT.md) before making changes.

---

## Known Limitations (v1.0.0)

- **CSRF tokens are not implemented.** `SameSite=Lax` session cookies mitigate the common
  cross-site POST vector; full token-based protection is deferred to v1.1 — see
  [RELEASE_NOTES.md](RELEASE_NOTES.md)
- Enquiry status is displayed but cannot yet be updated from the portal
- Employee accounts are managed directly in the database; there is no Employee CRUD screen
- The `Customers` table exists but has no write path — the Customers module is derived from
  `Enquiries`
- Product Comparison is not implemented
- No automated test suite ships with the application

---

## Author

**Srikar**

Sridevi Enterprises Development Project
