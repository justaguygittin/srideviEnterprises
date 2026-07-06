"""
=========================================================
Project : Sridevi Enterprises
File    : restructure_project.py
Purpose : Restructure project architecture.

Run once only.

Author  : Srikar
=========================================================
"""

from pathlib import Path
import shutil

ROOT = Path(__file__).parent

# -------------------------------------------------------
# Helper Functions
# -------------------------------------------------------

def create_folder(path: Path):
    """Create folder if it doesn't exist."""
    path.mkdir(parents=True, exist_ok=True)
    print(f"[DIR ] {path.relative_to(ROOT)}")


def create_file(path: Path, content=""):
    """Create file only if it doesn't exist."""
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"[FILE] {path.relative_to(ROOT)}")


def move_file(src: Path, dst: Path):
    """Move file if source exists and destination doesn't."""
    if src.exists():
        if not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            print(f"[MOVE] {src.relative_to(ROOT)} -> {dst.relative_to(ROOT)}")
        else:
            print(f"[SKIP] {dst.relative_to(ROOT)} already exists")


# -------------------------------------------------------
# Folder Structure
# -------------------------------------------------------

folders = [
    "database",

    "routes",

    "services",

    "templates/layout",
    "templates/components",
    "templates/customer",
    "templates/employee",
    "templates/admin",

    "static/css",
    "static/js",
    "static/images/categories",
    "static/videos",
    "static/uploads",

    ".devkit",
    ".devkit/docs",
    ".devkit/snippets",
    ".devkit/boilerplates",
]

for folder in folders:
    create_folder(ROOT / folder)

# -------------------------------------------------------
# Move Existing Templates
# -------------------------------------------------------

move_map = {
    "templates/home.html":
        "templates/customer/home.html",

    "templates/products.html":
        "templates/customer/products.html",

    "templates/product_details.html":
        "templates/customer/product_details.html",

    "templates/compare.html":
        "templates/customer/compare.html",

    "templates/contact.html":
        "templates/customer/contact.html",

    "templates/dashboard.html":
        "templates/employee/dashboard.html",

    "templates/inventory.html":
        "templates/employee/inventory.html",

    "templates/customers.html":
        "templates/employee/customers.html",

    "templates/enquiries.html":
        "templates/employee/enquiries.html",

    "templates/reports.html":
        "templates/employee/reports.html",

    "templates/employees.html":
        "templates/admin/employees.html",
}

for src, dst in move_map.items():
    move_file(ROOT / src, ROOT / dst)

# -------------------------------------------------------
# Core Files
# -------------------------------------------------------

create_file(
    ROOT / "templates/layout/base.html",
    "<!-- Base Template -->\n"
)

create_file(
    ROOT / "templates/components/navbar.html",
    "<!-- Navbar Component -->\n"
)

create_file(
    ROOT / "templates/components/footer.html",
    "<!-- Footer Component -->\n"
)

create_file(
    ROOT / "templates/components/searchbar.html",
    "<!-- Search Bar Component -->\n"
)

create_file(
    ROOT / "templates/components/flash_messages.html",
    "<!-- Flash Messages -->\n"
)

# -------------------------------------------------------
# CSS
# -------------------------------------------------------

css_files = [
    "base.css",
    "navbar.css",
    "footer.css",
    "home.css",
    "products.css",
    "mobile.css",
]

for css in css_files:
    create_file(ROOT / "static/css" / css)

# -------------------------------------------------------
# JavaScript
# -------------------------------------------------------

js_files = [
    "main.js",
]

for js in js_files:
    create_file(ROOT / "static/js" / js)

# -------------------------------------------------------
# Routes
# -------------------------------------------------------

route_files = [
    "customer.py",
    "employee.py",
    "admin.py",
    "api.py",
]

for route in route_files:
    create_file(ROOT / "routes" / route)

# -------------------------------------------------------
# Services
# -------------------------------------------------------

service_files = [
    "product_service.py",
    "customer_service.py",
    "inventory_service.py",
    "enquiry_service.py",
]

for service in service_files:
    create_file(ROOT / "services" / service)

# -------------------------------------------------------
# Database
# -------------------------------------------------------

create_file(ROOT / "database/db.py")

# -------------------------------------------------------
# DevKit
# -------------------------------------------------------

create_file(ROOT / ".devkit/docs/README.md")
create_file(ROOT / ".devkit/coding-standards.md")

print("\n=====================================")
print("Project restructuring completed.")
print("=====================================")
