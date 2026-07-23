# Sridevi Enterprises

> **Furniture • Electronics • Home Appliances**

A Flask + MariaDB showroom management system for Sridevi Enterprises: a customer-facing
digital showroom plus an internal employee portal for product management.

Current Version: **v0.8.0** (in development)

For architecture, RBAC, and development rules, see [AI_CONTEXT.md](AI_CONTEXT.md).
For deploying to production, see [DEPLOYMENT.md](DEPLOYMENT.md).

---

## Features

**Customer Website**
- Homepage with departments, featured products, and popular brands
- Product listing with search, filters, sorting, and pagination
- Product details with image gallery and specifications
- Product enquiry and contact forms
- Category landing pages and product comparison (in progress)

**Employee Portal**
- Employee login and session-based authentication
- Role-based access (Employee / Admin)
- Product listing, search, filters, and pagination
- Add, edit, and view products, including image uploads
- Delete products and product images (Admin only)

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

### Configure environment variables

Copy `.env.example` to `.env` and fill in your local database credentials and a secret key:

```bash
cp .env.example .env
```

The database schema lives in `database/schema/` — import each file in numeric order
(`001_create_catalog.sql` through `008_create_stockhistory.sql`) into your local MariaDB
instance.

---

## Running Locally

```bash
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000).

---

## Author

**Srikar**

Sridevi Enterprises Development Project
