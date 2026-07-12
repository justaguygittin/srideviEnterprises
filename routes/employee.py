"""
=========================================================
Project : Sridevi Enterprises
File    : employee.py
Purpose : Employee routes.

Author  : Srikar
=========================================================
"""

from flask import Blueprint, render_template, request
from services.auth_service import authenticate_employee

employee_bp = Blueprint("employee", __name__)


@employee_bp.route("/employee/login", methods=["GET", "POST"])
def login():
    """Handle employee login page and authentication."""

    error = None

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            error = "Username and password are required."
        else:
            user = authenticate_employee(username, password)

            if user:
                return render_template(
                    "employee/login.html",
                    success_message=f"Login successful! Welcome, {user['Username']}.",
                )
            else:
                error = "Invalid username or password."

    return render_template("employee/login.html", error=error)
