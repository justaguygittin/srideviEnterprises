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
cd ~/srideviEnterprises
pip install -r requirements.txt
```

### 1.4 Create the Database

1. In cPanel, use **MySQL® Databases** to create a new database and a database user, and
   grant that user all privileges on the database.
2. Open **phpMyAdmin**, select the new database, and import each file in
   `database/schema/` **in numeric order** (`001_create_catalog.sql` through
   `008_create_stockhistory.sql`) using phpMyAdmin's Import tab, or run them via the
   phpMyAdmin SQL tab one at a time in order.

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
```

`.env` is gitignored — it must be created directly on the server and is never committed.

### 1.6 Enable HTTPS

1. In cPanel, under **SSL/TLS Status** or **AutoSSL**, issue a certificate for the domain
   if one isn't already active.
2. Under **Domains**, enable **Force HTTPS Redirect** for the site.

### 1.7 Start the App

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

```bash
ssh USER@your-hostycare-server
cd ~/srideviEnterprises
git pull
source /home/USER/virtualenv/srideviEnterprises/3.x/bin/activate
pip install -r requirements.txt   # only if requirements.txt changed
touch tmp/restart.txt
```

Then run the smoke test below.

---

## 4. Smoke-Test Checklist

Run this after every deploy or restart:

- [ ] Homepage (`/`) loads with departments, featured products, and brands.
- [ ] Products listing (`/products`) loads; search, filters, and pagination work.
- [ ] A product details page (`/products/<id>`) loads with its images and specifications.
- [ ] Employee login (`/employee/login`) succeeds and reaches the dashboard.
- [ ] Add Product (employee) succeeds, including an image upload.
- [ ] Edit Product (employee) succeeds.
- [ ] Newly uploaded images render on the product's details page.
- [ ] Customer product enquiry form submits successfully.
- [ ] Contact form submits successfully.
- [ ] Visiting the site over plain `http://` redirects to `https://`.
- [ ] The browser shows a valid HTTPS padlock (no certificate warnings).

If anything fails, check cPanel's Python app error log (linked from the **Setup Python
App** page) before making changes.
