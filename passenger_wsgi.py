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
from urllib.parse import unquote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app as flask_app


class PassengerPathFix:
    """
    HostyCare / Passenger workaround.

    Passenger passes PATH_INFO still percent-encoded
    (e.g. "Computer%20&%20IT") instead of the decoded
    string required by PEP 3333.

    This middleware decodes PATH_INFO once before Flask
    processes the request.

    Local development (python app.py / flask run)
    never executes this file.
    """

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "")

        if "%" in path:
            environ["PATH_INFO"] = unquote(path)

        return self.app(environ, start_response)


application = PassengerPathFix(flask_app)
