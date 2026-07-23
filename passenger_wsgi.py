"""
=========================================================
Project : Sridevi Enterprises
File    : passenger_wsgi.py
Purpose : Phusion Passenger (HostCare) WSGI entry point.

          Passenger imports this file and looks for a module-level
          `application` callable. It does not run app.py's
          `if __name__ == "__main__"` block, so debug mode and the
          Werkzeug dev server are never used in this path.

Author  : Srikar
=========================================================
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app as application
