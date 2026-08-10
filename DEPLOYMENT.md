# Deployment — Sridevi Enterprises on HostyCare

This document covers deploying and redeploying Sridevi Enterprises on HostyCare shared
hosting (cPanel + Passenger). For local development setup, see [README.md](README.md).

---

## 1. First-Time Setup

### 1.1 Create the Python App (cPanel)

1. In cPanel, open **Setup Python App**.
2. Click **Create Application**.
3. Set:
   - **Python version** — match the version used in your local `venv`.
   - **Application root** — the directory this repo will live in (e.g. `srideviEnterprises`).
   - **Application URL** — the domain/subdomain for the site.
   - **Application startup file** — `passenger_wsgi.py` (cPanel usually fills this in).
   - **Application Entry point** — `application` (matches `passenger_wsgi.py`'s
     `from app import app as application`).
4. Create the app. cPanel generates a dedicated virtualenv and shows you its activation
   command (e.g. `source /home/USER/virtualenv/srideviEnterprises/3.x/bin/activate`) —
   note it down, you'll need it below.

### 1.2 Get the Code onto the Server

Using cPanel's **Git Version Control** feature, or over SSH:

```bash
ssh USER@your-hostycare-server
cd ~/srideviEnterprises   # the application root from step 1.1
git clone <repository-url> .
```

For redeploys later, this becomes a `git pull` (see §3).

### 1.3 Install Dependencies

Activate the virtualenv cPanel created (the exact command is shown on the app's page in
cPanel — it's specific to your app and Python version), then install:

```bash
source /home/USER/virtualenv/srideviEnterprises/3.x/bin/activate
cd ~/SE/srideviEnterprises
pip install -r requirements.txt
```

### 1.4 Create the Database

1. In cPanel, use **MySQL® Databases** to create a new database and a database user, and
   grant that user all privileges on the database.
2. Open **phpMyAdmin**, select the new database, and import **every** file in
   `database/schema/` **in numeric order**, from `001_create_catalog.sql` through
   `011_alter_catalog_add_soft_delete.sql`, using phpMyAdmin's Import tab, or run them
   via the phpMyAdmin SQL tab one at a time in order.

   Import the whole directory — do not stop at any particular file. Order is not
   optional: `003` adds a foreign key to `Users`, `009` adds one to `Employees` and
   alters the table `008` creates, and `011` alters the table `001` creates. As of
   v1.0 the directory contains these 11 files:

   | File | Creates / changes |
   |---|---|
   | `001_create_catalog.sql` | `Catalog` — products (shared with the Receipt Generator project) |
   | `002_create_users.sql` | `Users` — authentication |
   | `003_create_employees.sql` | `Employees` (FK → `Users`) |
   | `004_create_customers.sql` | `Customers` — reserved; no write path yet |
   | `005_create_enquiries.sql` | `Enquiries` — customer enquiries |
   | `006_create_productdetails.sql` | `ProductDetails` — specifications |
   | `007_create_productimages.sql` | `ProductImages` — product gallery |
   | `008_create_stockhistory.sql` | `StockHistory` — inventory audit trail |
   | `009_alter_stockhistory_add_transaction_columns.sql` | Adds transaction columns, 3 indexes, FK → `Employees` |
   | `010_create_departmentimages.sql` | `DepartmentImages` — Department Image Management |
   | `011_alter_catalog_add_soft_delete.sql` | Adds `Catalog.IsActive` / `DeletedAt` / `DeletedBy` |

   **Skipping `010` or `011` produces a database the v1.0 application cannot run
   against** — without `010` the homepage and Departments module fail, and without
   `011` every product query fails on the missing `IsActive` column. Verify with
   step 3 below before moving on.

3. **Verify the import** before continuing. In phpMyAdmin's SQL tab:

   ```sql
   SHOW TABLES;                  -- expect 9: Catalog, Customers, DepartmentImages,
                                 -- Employees, Enquiries, ProductDetails,
                                 -- ProductImages, StockHistory, Users
   SHOW COLUMNS FROM Catalog;    -- must include IsActive, DeletedAt, DeletedBy (011)
   ```

   If either check comes up short, re-run the missing file(s) rather than continuing —
   the application will not start correctly against a partial schema.

### 1.5 Configure Environment Variables

Copy `.env.example` to `.env` inside the application root (via SSH or cPanel's File
Manager) and fill in real values:

```bash
cp .env.example .env
```

```env
DB_HOST=localhost
DB_PORT=3306
DB_NAME=<your cPanel database name>
DB_USER=<your cPanel database user>
DB_PASSWORD=<your cPanel database password>
SECRET_KEY=<a long random value — see the comment in .env.example>
FLASK_DEBUG=False
SESSION_COOKIE_SECURE=True
LOG_LEVEL=INFO
```

`.env` is gitignored — it must be created directly on the server and is never committed.

> **`SESSION_COOKIE_SECURE` must be `True` in production.** `.env.example` ships it as
> `False` because local development runs over plain HTTP, where a secure cookie is
> refused by the browser and login would not work. It is the one value in that template
> that is deliberately *less* safe than the application's own default — if you copied
> `.env.example` to the server, change it. Leaving it out entirely is also correct, since
> `True` is the default. The app logs a `WARNING` on every startup while it is `False`,
> so check the error log (§4.1) after your first deploy.

#### Public business details

**This is where the showroom's real contact information is configured.** These five
values are the single source of truth for every public surface that displays contact
details — the sitewide footer, the Contact page, and the standalone Maintenance Mode
(503) screen. They are not hardcoded in any template.

```env
BUSINESS_ADDRESS=<full showroom address, one line>
BUSINESS_PHONE=<phone, written for display — e.g. +91 98765 43210>
BUSINESS_EMAIL=<public enquiry email>
BUSINESS_WEBSITE=<public website, e.g. www.example.com>
BUSINESS_HOURS=<opening hours, free text>
```

- `.env.example` ships **development placeholders** for these (`123 Business Road`,
  `info@sridevienterprises.example`, …) so a fresh local checkout renders a complete
  page. **Every one of them must be replaced with real values on the server** — the
  same rule as `SECRET_KEY` and the maintenance key.
- The dialable `tel:` link and the absolute website URL are derived automatically from
  the display values (`config.py`), so each detail is configured exactly once.
- **A blank value is safe, not an error.** Any detail left unset is omitted from every
  page — no placeholder text, no empty row. If none are set, the footer's Contact
  column and the 503 page's contact block do not render at all, and the Contact page
  shows a short "use the enquiry form" note instead of an empty card. This is
  deliberate: an unconfigured deployment shows nothing rather than plausible-looking
  fake contact details.
- Changing any of these requires a Passenger restart (§2), since `.env` is read at
  process start — unlike `config/maintenance.json`, which is read fresh per request.

### 1.6 Configure Maintenance Mode

Copy the template and set a real bypass key (never leave the example's
`development-change-me` value in production):

```bash
cp config/maintenance.example.json config/maintenance.json
```

```json
{
    "enabled": false,
    "maintenance_key": "<a long random value, same idea as SECRET_KEY above>"
}
```

`config/maintenance.json` is gitignored, same as `.env` — see §5 for how this is used
during a deploy.

### 1.7 Enable HTTPS

1. In cPanel, under **SSL/TLS Status** or **AutoSSL**, issue a certificate for the domain
   if one isn't already active.
2. Under **Domains**, enable **Force HTTPS Redirect** for the site.

### 1.8 Start the App

In **Setup Python App**, click **Restart** on the application (equivalent to running
`touch tmp/restart.txt` in the app root, which Passenger watches for). Visit the site URL
and confirm it loads.

---

## 2. Restart Procedure

Passenger only picks up code/config changes after a restart. After **any** deploy:

```bash
touch ~/srideviEnterprises/tmp/restart.txt
```

or use the **Restart** button on the app's page in cPanel's **Setup Python App**.

---

## 3. Redeploying After Changes

Sprint 7 exposed a real deployment gap: new templates land on disk as soon as `git pull`
runs, but Passenger keeps the old Flask process (and its old routes) alive until it is
explicitly restarted. In that window, customers could be served a half-deployed site —
new templates against old routes, or a page referencing a column a pending migration
hasn't added yet. **Maintenance Mode (see §5) exists specifically to close this window.**
Use it for any deploy that changes templates, routes, or the database schema — not just
migrations.

### 3.1 Official Deployment Workflow

```
Enable Maintenance
        |
        v
Backup Database
        |
        v
     git pull
        |
        v
Run SQL Migration (if required)
        |
        v
Restart Passenger
        |
        v
Employee Smoke Test
        |
        v
Customer Smoke Test (using maintenance bypass)
        |
        v
     Bug Found?
      /      \
   Yes        No
    |          |
   Fix    Disable Maintenance
    |          |
  Retest   Website Live
    |
    +---> (back to Employee/Customer Smoke Test)
```

### 3.2 Commands

```bash
# 1. Enable Maintenance (on the server)
ssh USER@your-hostycare-server
cd ~/srideviEnterprises
nano config/maintenance.json     # set "enabled": true
touch tmp/restart.txt            # not strictly required (maintenance.json is read
                                  # fresh on every request), but keep this step so the
                                  # workflow always restarts before touching the DB —
                                  # see the Sprint 8 lesson in §8.

# 2. Backup Database
# In cPanel: phpMyAdmin -> Export (or mysqldump over SSH), before touching any schema.

# 3. git pull
git pull
source /home/USER/virtualenv/srideviEnterprises/3.x/bin/activate
pip install -r requirements.txt  # only if requirements.txt changed

# 4. Run SQL Migration (only if this deploy adds one — see §6)
# Via phpMyAdmin's Import/SQL tab, one new database/schema/0NN_*.sql file, in order.

# 5. Restart Passenger
touch tmp/restart.txt

# 6. Employee Smoke Test - log in and click through the Employee Portal (see §4)

# 7. Customer Smoke Test - open the site with the bypass key appended once:
#      https://your-domain/?maintenance_key=<the real key from config/maintenance.json>
#    then click through the Customer Website (see §4) - the bypass session persists
#    across every subsequent page, so you only need to append the key one time.

# 8a. Bug found -> fix, git pull again, re-run step 6/7 until clean.
# 8b. No bug -> Disable Maintenance:
nano config/maintenance.json     # set "enabled": false
touch tmp/restart.txt
```

Never skip the Employee Smoke Test even for a customer-facing change — the Employee
Portal is never gated by Maintenance Mode (see §5), so it is reachable, and breakable,
throughout the entire deploy window.

---

## 4. Smoke-Test Checklist

Run this after every deploy or restart.

### Customer Website

- [*] Homepage (`/`) loads with departments, featured products, and brands.
- [*] Products listing (`/products`) loads; search, filters, and pagination work.
- [*] A product details page (`/products/<id>`) loads with its images and specifications.
- [*] Departments page (`/categories`) loads.
- [ ] Search returns results from the navbar search bar.
- [*] Contact form (`/contact`) submits successfully.
- [*] Customer product enquiry form submits successfully.
- [*] Visiting the site over plain `http://` redirects to `https://`.
- [*] The browser shows a valid HTTPS padlock (no certificate warnings).
- [ ] Footer and Contact page show the **real** business address, phone, email,
      website, and hours — not `.env.example`'s placeholders (`123 Business Road`,
      `info@sridevienterprises.example`). See §1.5 "Public business details".

### Employee Portal

- [*] Employee login (`/employee/login`) succeeds and reaches the dashboard.
- [ ] Dashboard stats (Products / Enquiries / Customers / Inventory) load without error.
- [*] Products list, search, and filters load.
- [*] Add Product (employee) succeeds, including an image upload.
- [*] Edit Product (employee) succeeds.
- [ ] Newly uploaded images render on the product's details page.
- [ ] Product Details page loads for both an active and (if any) an inactive product.
- [ ] Inventory Summary and Inventory Transactions pages load.
- [ ] Departments module loads.
- [ ] Customers and Enquiries lists load.

### Maintenance Mode (Sprint 8 / Sprint 8 Review)

- [ ] With `config/maintenance.json` `"enabled": false` — the site behaves exactly as
      the two checklists above describe; the maintenance banner never appears; the
      Employee Dashboard's Maintenance Mode notice never appears.
- [ ] With `"enabled": true` — any customer-facing URL returns HTTP 503 with the
      **standalone** maintenance page (no navbar links, no search bar, no footer —
      see §5.2), and the Employee Portal still passes every item in the Employee
      Portal checklist above unaffected.
- [ ] The 503 response carries `Cache-Control: no-store`, `Pragma: no-cache`,
      `Expires: 0` (check via browser dev tools' Network tab, or
      `fetch('/').then(r => r.headers.get('Cache-Control'))` in the console).
- [ ] `https://your-domain/?maintenance_key=<correct key>` bypasses maintenance, shows
      the (now bold, high-contrast) "Maintenance Mode" banner, and the bypass persists
      across further customer pages without needing to repeat the query parameter.
- [ ] An incorrect `?maintenance_key=` value stays on the maintenance page.
- [ ] The Employee Dashboard shows the "Maintenance Mode Enabled" notice card while
      maintenance is on, and it disappears once disabled.
- [ ] The 503 page shows the real business phone and email (from `.env`, §1.5), or no
      contact block at all if they are unset — never a placeholder number.
- [ ] `GET /health` returns `{"status": "ok", "maintenance": <true|false>, "version":
      "<Config.APP_VERSION>"}` — and `maintenance` correctly matches the current
      `config/maintenance.json` state — regardless of which customer/employee page you
      last visited.

If anything fails, check cPanel's Python app error log (linked from the **Setup Python
App** page) before making changes — see §4.1 for what the application writes there.

### 4.1 Application Logs

As of v1.0 the application logs to **stderr**, which Passenger captures into the Python
app error log linked from cPanel's **Setup Python App** page. There is no separate log
file to create, rotate, or make writable.

Each line looks like:

```
2026-08-08 07:47:03,409 ERROR    [services.enquiry_service:26592] Enquiry submission FAILED to save - product_id=1 (customer details not logged)
```

`timestamp · level · [module:process-id] · message`. The process id matters on shared
hosting, where Passenger runs several workers concurrently.

Verbosity is set by `LOG_LEVEL` in `.env` (default `INFO`; see §1.5). What each level
means here:

| Level | What appears |
|---|---|
| `INFO` | Worker startup (with version), enquiries saved, stock transactions recorded or refused, products deactivated/restored, images deleted |
| `WARNING` | Maintenance Mode enabled, `config/maintenance.json` missing, image files that could not be deleted, refused image deletions |
| `ERROR` | Every failed write — product save/update, department save, deactivate/restore — and every failed customer enquiry, each with a full traceback |

**What to grep for when something is reported broken:**

```bash
grep "FAILED" ~/logs/*.log        # every failed write operation
grep "Enquiry submission FAILED" ~/logs/*.log   # lost customer enquiries
grep "Maintenance Mode" ~/logs/*.log            # who took the site offline, and when
```

Read-only page views deliberately log nothing, so the log stays readable — anything
present in it is a write, a failure, or a state change.

**Customer personal data is never logged.** A failed enquiry records the product id and
the underlying database error, but not the customer's name, phone, email, or message.
The enquiry is genuinely lost in that case; the log tells you it happened and why, not
who it was. If lost-lead recovery ever becomes a requirement, that needs a durable
store, not the log file.

---

## 5. Maintenance Mode

Maintenance Mode takes the **Customer Website only** offline (HTTP 503, a dedicated
standalone maintenance screen) while a deploy or migration is in progress, without
touching the database and without blocking the Employee Portal. See `AI_CONTEXT.md` →
"Sprint 8 — Maintenance Mode & Deployment Hardening" and "Sprint 8 Review — Maintenance
Page Redesign, Banner, Cache Headers, Health Endpoint, Dashboard Notice" for the full
implementation detail; this section is the operational how-to.

### 5.1 Enabling / Disabling

Edit `config/maintenance.json` directly on the server (it is gitignored — your own
`git pull` can never overwrite or conflict with the live server's setting):

```json
{
    "enabled": true,
    "maintenance_key": "a-long-random-value-here"
}
```

Set `"enabled"` to `true` or `false` and restart Passenger (`touch tmp/restart.txt`).
**No code change, no database change, no redeploy is required to toggle this.**

If `config/maintenance.json` does not yet exist on the server (e.g. first-ever setup),
copy the template:

```bash
cp config/maintenance.example.json config/maintenance.json
```

then edit `maintenance_key` to a real secret — never leave the example's
`development-change-me` value in a production `config/maintenance.json`.

### 5.2 What Customers See

The 503 page (`templates/errors/503.html`, extending the bare `layout/minimal.html`
instead of the normal site layout) is a dedicated, standalone screen: logo, "Sridevi
Enterprises," a maintenance icon, "Scheduled Maintenance," a friendly message, and
optional contact text — **no navbar links, no search bar, no footer links**. This is
deliberate: the original version reused the full site chrome, which meant a customer
could click "Products" or use the search bar and land right back on the same page,
reading as "this one link is broken" rather than "the whole site is down." The
standalone screen makes that unambiguous at a glance. The response also always carries
`Cache-Control: no-store`, `Pragma: no-cache`, `Expires: 0`, so a browser or proxy can
never keep showing a cached maintenance page once you've disabled maintenance and
restarted.

### 5.3 Bypassing Maintenance to Test

Visit the site once with the key appended to any URL:

```
https://your-domain/?maintenance_key=<the real key>
```

This verifies the key and stores `maintenance_verified` in your browser session — every
further page on the customer site works normally for you, with a bold, high-contrast
"Maintenance Mode" banner across the top (title line + "Public visitors are currently
receiving HTTP 503." + "You are viewing the site using the maintenance bypass.")
reminding you the public still sees the maintenance page. This lasts until you close
the browser, or an employee account you're also logged into calls `/employee/logout`
(which clears the whole session, including this).

### 5.4 What Stays Up During Maintenance

- The Employee Portal (`/employee/...`) — login, dashboard, Products, Inventory,
  Inventory Transactions, Departments, Customers, Enquiries, Product Details all
  continue to work normally; none of it depends on Employee login to bypass the
  customer-facing gate, because it was never gated in the first place. The Employee
  Dashboard additionally shows a "Maintenance Mode Enabled" notice card the whole time,
  as a reminder to disable it after the deploy finishes.
- `GET /health` — always returns `{"status": "ok", "maintenance": <bool>, "version":
  "<Config.APP_VERSION>"}`, for use as a post-restart liveness check independent of
  Maintenance Mode (see §5.5).
- Static assets (`/static/...`).

Everything else under the Customer Website returns HTTP 503 with the standalone
maintenance page until disabled or bypassed.

### 5.5 Health Endpoint

`GET /health` never requires a database round-trip (reaching the route already proves
the WSGI process is up) and returns:

```json
{
    "status": "ok",
    "maintenance": false,
    "version": "<Config.APP_VERSION>"
}
```

- `maintenance` — the live `config/maintenance.json` state, so one request after a
  restart confirms both "the process is up" and "Maintenance Mode is in the state I
  expect it to be in" (e.g. still `true` right after step 5 of §3.2, or `false` again
  after step 8b).
- `version` — `Config.APP_VERSION` (`config.py`), a plain hand-maintained string bumped
  per sprint/release. Confirms the restarted process is actually serving the code you
  just deployed, not a stale worker Passenger hasn't fully cycled yet.

---

## 6. Database Migration Workflow

1. **Enable Maintenance** (§5.1) and restart Passenger before touching the database —
   this is what prevents a customer from hitting a page mid-migration that expects a
   column/table the migration hasn't added yet.
2. **Backup the database** (cPanel phpMyAdmin Export, or `mysqldump`) before running
   any new schema file.
3. **Apply the new file(s)** from `database/schema/` **in numeric order**, via
   phpMyAdmin's Import or SQL tab — the same process already used for the original
   schema (§1.4). Never hand-edit a table directly without also adding/updating the
   corresponding `database/schema/0NN_*.sql` file — see the Sprint 5.1 schema-drift
   lesson in §8; the canonical schema is always what's in version control.

   **When you add a new `0NN_*.sql` file, update §1.4's table and its stated file
   range in the same change.** That list is what a first-time installer follows, and
   it is the one piece of documentation that silently breaks a fresh install when it
   falls behind — see the v1.0 lesson in §8.
4. **Restart Passenger** (`touch tmp/restart.txt`) so the running process picks up any
   code that depends on the new schema.
5. **Run the Employee Smoke Test**, since it exercises write paths (Add/Edit Product,
   Inventory Transactions) most likely to break on a schema mismatch.
6. **Run the Customer Smoke Test using the maintenance bypass** (§5.3).
7. **Disable Maintenance** only once both smoke tests are clean.

If a migration fails partway through, restore from the backup taken in step 2 before
retrying — do not attempt to manually patch a partially-applied schema change.

---

## 7. Deployment Checklist

A condensed version of §3.1 for pinning to the terminal/notes while deploying:

- [ ] Enable Maintenance Mode, restart Passenger.
- [ ] Back up the database.
- [ ] `git pull`, `pip install -r requirements.txt` if `requirements.txt` changed.
- [ ] Apply any new `database/schema/0NN_*.sql` file(s), in order (§6).
- [ ] Restart Passenger (`touch tmp/restart.txt`).
- [ ] `GET /health` returns `{"status": "ok", "maintenance": true, "version": "..."}`
      with `maintenance` matching what you just set (§5.5).
- [ ] Employee Smoke Test passes (§4), including the Dashboard's "Maintenance Mode
      Enabled" notice being visible.
- [ ] Customer Smoke Test passes, using the maintenance bypass key (§4).
- [ ] Disable Maintenance Mode, restart Passenger.
- [ ] Re-check the homepage loads normally with Maintenance Mode off.

### 7.1 Business Configuration Verification

**Run this before the first go-live, and again after any change to `.env`.** The site
will render perfectly well with none of these set — every unset value is silently
omitted from the page (see §1.5). That safe-failure behaviour is deliberate, but it
also means a deployment can go live with **no contact information at all** and nothing
will look broken. This section is the gate that prevents that.

Confirm each value is present in the server's `.env` **and** is a real business value,
not the development placeholder shipped in `.env.example`:

```
□ BUSINESS_ADDRESS configured
□ BUSINESS_PHONE configured
□ BUSINESS_EMAIL configured
□ BUSINESS_WEBSITE configured
□ BUSINESS_HOURS configured
```

Also confirm the session cookie is hardened (§1.5). In the browser's dev tools,
Application → Cookies, the `session` cookie on the live site must show:

```
□ Secure   flag set    (SESSION_COOKIE_SECURE=True, or absent from .env)
□ HttpOnly flag set
□ SameSite = Lax
```

If `Secure` is missing, the error log will also contain a `SESSION_COOKIE_SECURE is
False` warning from startup — fix `.env` and restart Passenger.

Then verify the business details actually reached the pages (Passenger must have been
restarted after editing `.env` — these are read once at process start):

- [ ] Footer shows the real address, phone, email, and hours on the live site.
- [ ] Contact page shows all five values, and the phone/email/website links work.
- [ ] Enable Maintenance Mode briefly and confirm the 503 screen shows the real phone
      and email, then disable it again.
- [ ] Search the live pages for the placeholder strings `123 Business Road`,
      `+91 98765 43210`, `info@sridevienterprises.example`, and
      `www.sridevienterprises.example`. **Any hit means `.env.example`'s development
      values reached production** — fix before announcing the site.

---

## 8. Lessons Learned

**Sprint 7 (pre-Maintenance Mode).** Deploying new templates without restarting
Passenger left an old Flask process serving stale routes/templates against newly
deployed files, so customers could hit a broken or half-deployed page during that
window. Rule: **any** deploy that changes templates, routes, or schema must restart
Passenger (§2), and — as of Sprint 8 — should also wrap the deploy in Maintenance Mode
(§5) so that window is never customer-visible at all.

**Sprint 5.1 (schema drift).** A live-database column change was made directly against
production/dev, outside of any `database/schema/0NN_*.sql` file, and was only caught
because a later sprint verified the live schema against version control before writing
new queries against it. Rule (already in `AI_CONTEXT.md`): the canonical schema is
always what's committed under `database/schema/` — never hand-modify a live schema
without adding/updating the matching migration file in the same change.

**v0.8.0 (initial deployment).** The first production database was created from an
outdated schema snapshot, not the current `database/schema/` files. Rule: always create
a new database strictly from the current, numerically-ordered `database/schema/` files
(§1.4) — never from an old export or a partially-applied prior attempt.

**v1.0 Sprint 11 (documentation drift broke fresh installs).** §1.4 and README.md both
told installers to import `001` through `009`, but two further migrations had shipped
since that instruction was written (`010_create_departmentimages.sql`,
`011_alter_catalog_add_soft_delete.sql`). Following the documentation literally
produced a database with no `DepartmentImages` table and no `Catalog.IsActive` column —
against which essentially every page fails. Nothing in the codebase pointed at the
documentation, so the drift was invisible until it was tested. Two rules came out of
this: **(a)** adding a `0NN_*.sql` file and updating §1.4 are one change, not two
(§6 step 3); **(b)** a release must actually build a database from
`database/schema/` and boot the app against it, rather than trusting that the install
instructions still describe reality. That simulation immediately found a second,
unrelated fresh-install bug — the Employee Dashboard and Inventory Summary returned
HTTP 500 against an empty `Catalog`, because an unfiltered `SUM()` over zero rows
returns `NULL`, not `0` (fixed in `services/product_service.py:get_inventory_summary()`).
**An install is only proven by installing it.**

**Sprint 8 (Maintenance Mode design).** Maintenance state is a config file
(`config/maintenance.json`), not a database row — deliberately, so that flipping it
never depends on the database being reachable or schema-compatible, which is exactly
the condition Maintenance Mode exists to protect a migration through. See
`AI_CONTEXT.md` → "Sprint 8 — Maintenance Mode & Deployment Hardening" for the full
reasoning.

**Sprint 8 Review (maintenance page reused site chrome).** The first version of the 503
page extended the normal site layout, so it still had working navbar links and a search
bar — every one of which just re-triggered the same 503, which reads as "this link is
broken," not "the whole site is down." Rule: a full-site-outage page must never share a
layout with pages that imply partial availability; it needs its own dedicated,
link-free layout (`layout/minimal.html`) so the "everything is down" message is
unambiguous. If a future page needs the same treatment (e.g. a splash/loading screen),
extend `layout/minimal.html` rather than reusing `layout/base.html` and stripping
things back out of it.
