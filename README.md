# Sridevi Enterprises

> **Furniture • Electronics • Home Appliances**

A modern customer-facing showroom website for **Sridevi Enterprises**, built using Flask and MariaDB.

The project allows customers to browse products, search inventory, compare products, view detailed specifications, and send enquiries. It also provides an employee portal for inventory management, customer enquiries, reports, and integration with the existing Receipt Generator.

---

# Current Status

**Version:** v0.2.0

## Completed

- ✅ Project architecture
- ✅ Flask application setup
- ✅ MariaDB integration
- ✅ Blueprint routing
- ✅ Homepage
- ✅ Hero video
- ✅ Responsive navigation
- ✅ Footer
- ✅ Search bar
- ✅ Department-based product organization
- ✅ HostyCare-compatible deployment architecture

---

# Technology Stack

- Python 3
- Flask
- MariaDB
- Bootstrap 5
- HTML5
- CSS3
- JavaScript
- Jinja2

---

# Project Structure

```text
SrideviEnterprises/

app.py
config.py
passenger_wsgi.py
requirements.txt

database/
schema/

routes/
services/
scripts/

templates/
static/

.devkit/
```

---

# Database

Development Database

```
MariaDB
Host : 127.0.0.1
Port : 3307
Database :
gsrikari_Sridevi_Enterprises
```

Current Tables

- Catalog
- Customers
- Employees
- Enquiries
- ProductDetails
- ProductImages
- StockHistory
- Users

> **Note**
>
> The **Catalog** table is shared with the Receipt Generator project and acts as the single source of truth for products.

---

# Installation

## Clone Repository

```bash
git clone <repository-url>
cd SrideviEnterprises
```

## Create Virtual Environment

```bash
python -m venv venv
```

Activate

Windows

```bash
venv\Scripts\activate
```

---

## Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Configure Environment

Create a `.env` file.

Example

```env
DB_HOST=127.0.0.1
DB_PORT=3307
DB_NAME=gsrikari_Sridevi_Enterprises
DB_USER=root
DB_PASSWORD=YOUR_PASSWORD
```

---

# Run Project

```bash
python app.py
```

Open

```
http://127.0.0.1:5000
```

---

# Homepage Features

- Hero Video
- Responsive Navigation
- Quick Actions
- Shop by Department
- Featured Products
- Popular Brands
- About Section
- Contact Section
- Google Maps (Placeholder)

---

# Roadmap

## Phase 0

- ✅ Project Foundation

## Phase 1

- ✅ UI Framework

## Phase 2

- ✅ Homepage

## Phase 3

- 🔄 Product Module

- Product Listing
- Product Details
- Search
- Filters
- Compare Products

## Phase 4

- Employee Portal

## Phase 5

- Admin Portal

## Phase 6

- Production Deployment

## Future Enhancements

- GeM Integration
- IndiaMART Integration
- Marketplace Synchronization
- AI Product Search
- Analytics Dashboard

---

# Development Standards

- Blueprint architecture
- Service layer architecture
- Database helper layer
- Responsive-first design
- Component-based Jinja templates
- Environment-based configuration
- Frozen project architecture (no structural changes without version update)

---

# Deployment

Production target

- HostyCare
- Passenger WSGI
- MariaDB

Development Workflow

```
Local Development
        ↓
Git Commit
        ↓
Git Push
        ↓
HostyCare Deployment
```

---

# Author

**Srikar**

Sridevi Enterprises Development Project

---
