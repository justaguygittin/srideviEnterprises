# AI_CONTEXT.md

# Sridevi Enterprises
Current Version: v0.7.0

---

# Project Overview

Sridevi Enterprises is a Flask-based showroom management system for a furniture and home appliances business.

The application consists of two major modules:

1. Customer Website
2. Employee Management Portal

The Employee Portal is the current development priority.

The objective is to complete a fully functional demonstration build before expanding into advanced business modules.

---

# Technology Stack

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

# Project Architecture

The project follows a layered architecture.

Routes
↓
Services
↓
Database Helper
↓
MariaDB

Rules

Routes
- Handle requests
- Return responses
- Never contain SQL

Services
- Business logic
- Validation
- SQL Queries

Database
(database/db.py)
- Execute SQL
- Return results
- No business logic

Never bypass this architecture.

---

# Current Progress

Completed

Customer Website

✓ Home Page

✓ Products Page

✓ Categories Page

✓ Search

✓ Product Comparison

✓ Contact Page

Employee Portal

✓ Employee Login

✓ Session Management

✓ Dashboard

✓ Logout

✓ Protected Routes

✓ Product Listing

✓ Search

✓ Filters

✓ Pagination

---

# Development Goal

Current Goal

Complete Employee Product Management.

After that

Complete Customer Product Experience.

After that

Complete Customer Enquiry Management.

---

# Role Based Access Control (RBAC)

Three user roles exist.

1. Customer
2. Employee
3. Admin

No additional roles should be introduced unless explicitly approved.

---

# Customer Permissions

Customers can

- Browse website
- View products
- View product details
- Search products
- Compare products
- Submit enquiries

Customers cannot

- Access employee portal
- Edit products
- Manage data

---

# Employee Permissions

Employees can

- Login
- Access dashboard
- View products
- Add products
- Edit products
- Upload product images
- View customer enquiries

Employees cannot

- Delete products
- Delete product images
- Manage users
- Access admin settings

---

# Admin Permissions

Admins have unrestricted access.

Admins can

- Everything an Employee can do

Additionally

- Delete products
- Delete product images
- Manage employees
- Manage users
- Future system administration

---

# Authorization vs. Job Designation

Users.Role represents permission groups only.

Allowed values

- Customer
- Employee
- Admin

Employees.Designation represents the employee's job title.

Examples

- Administrator
- Manager
- Sales Executive
- Accountant
- Warehouse Staff

Designation is for display and business information only.

Designation must never be used for authorization.

RBAC is based solely on Users.Role.

---

# Authorization Rules

Every protected route must validate user role.

Customer Routes

Public

Employee Routes

Employee
Admin

Admin Routes

Admin only

Never rely on hidden navigation buttons for security.

Every route must verify permissions.

---

# Business Rules

Financial information must never appear in the customer website.

Financial information must never appear in the employee portal.

Do NOT expose

- Purchase Cost
- Selling Price
- GST
- Profit
- Margins
- Supplier Cost

The website is a digital showroom.

Not an e-commerce website.

---

# Database

Primary Tables

Users

Catalog

ProductImages

Enquiries

Additional tables should follow existing naming conventions.

---

# Product Images

Images are NOT stored inside Catalog.

Relationship

Catalog

ProductID

↓

ProductImages

ImageID

ProductID

ImageURL

UploadDate

One Product

↓

Many Images

---

# Category Images

Categories should never have dedicated images.

Instead

Each category automatically displays one representative image from a product belonging to that category.

No CategoryImages table should be created.

---

# Product Creation Rules

A product must never exist without an image.

Workflow

Create Product

↓

Generate ProductID

↓

Upload Minimum One Image

↓

Save

Validation

Minimum Images

1

Maximum Images

Unlimited

---

# Image Storage

Images should be stored inside

static/uploads/products/

Recommended future structure

static/uploads/products/

ProductID/

image1.jpg

image2.jpg

...

Database stores only relative paths.

---

# UI Guidelines

Theme

Primary
#1E4FA3

Secondary
#1565A0

Keep UI clean.

Keep Bootstrap consistent.

Avoid unnecessary custom CSS.

---

# Coding Standards

Keep functions small.

Reuse existing services.

Avoid duplicate SQL.

Avoid duplicate templates.

Reuse components whenever possible.

Prefer extending existing code instead of rewriting it.

Preserve backward compatibility.

Do not introduce breaking changes without approval.

---

# Testing Policy

Every feature must be fully functional before starting the next one.

Do not commit

- Placeholder pages

- Dummy buttons

- Half implemented features

Every completed milestone should be manually testable.

---

# Current Development Roadmap

v0.7.0

Employee Product Management

Current Focus

□ Product Details

□ Product Image Gallery

□ Add Product

□ Upload Product Images

□ Edit Product

□ Delete Product (Admin)

□ Delete Product Images (Admin)

Next

v0.8.0

Customer Product Experience

- Product Details
- Product Gallery
- Category Images
- Similar Products

Next

v0.9.0

Customer Enquiries

- Submit Enquiry
- Employee Enquiry Dashboard
- Status Management

Next

v1.0.0

Working Demonstration Release

- Responsive UI
- Validation
- Bug Fixes
- Final Testing
- Deployment

---

# Development Rules

Never modify the project architecture.

Never expose financial information.

Always implement RBAC before exposing a new route.

Every new feature must define

- Who can view
- Who can create
- Who can edit
- Who can delete

If a breaking change is required, obtain approval before implementation.
