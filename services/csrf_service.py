"""
=========================================================
Project : Sridevi Enterprises
File    : csrf_service.py
Purpose : Session-derived CSRF tokens (Password Management cycle).

          Scope today: the login form and every password-management form
          (change password, forgot password, reset password, Admin-assisted
          reset). Each of those views is wrapped in @csrf_protect.

          Built to extend app-wide later (AI_CONTEXT.md, RC-8 "What v1.1
          should do"): the token is already available to every template as
          {{ csrf_token() }} (registered in app.py), and validate_csrf() is
          a plain function - an app-level before_request hook can call it for
          every POST once each remaining form has the hidden field. Keep
          SESSION_COOKIE_SAMESITE=Lax alongside this; the two are
          complementary.

Author  : Srikar
=========================================================
"""

import hmac
import logging
import secrets
from functools import wraps

from flask import flash, redirect, request, session, url_for

logger = logging.getLogger(__name__)

_SESSION_KEY = "_csrf_token"
FORM_FIELD = "csrf_token"


def get_csrf_token() -> str:
    """Return this session's CSRF token, creating it on first use."""

    token = session.get(_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        session[_SESSION_KEY] = token
    return token


def validate_csrf() -> bool:
    """True when the submitted form token matches this session's token."""

    expected = session.get(_SESSION_KEY)
    submitted = request.form.get(FORM_FIELD, "")
    if not expected or not submitted:
        return False
    return hmac.compare_digest(str(expected), str(submitted))


def csrf_protect(view=None, *, redirect_endpoint: str | None = None):
    """
    Reject a state-changing request whose CSRF token is missing or wrong.

    The usual innocent cause is an expired or cleared session (e.g. a login
    form left open overnight), so the response is a friendly "please try
    again" redirect rather than a bare HTTP 400: back to the same URL, or to
    `redirect_endpoint` for POST-only routes (which have no page to return to).
    Nothing the request asked for is performed.

    Usage: @csrf_protect  or  @csrf_protect(redirect_endpoint="admin.employees")
    """

    def decorate(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if request.method in ("POST", "PUT", "PATCH", "DELETE") and not validate_csrf():
                logger.warning(
                    "CSRF validation failed - endpoint=%s ip=%s", request.endpoint, request.remote_addr
                )
                flash("Your form expired or could not be verified. Please try again.", "warning")
                return redirect(url_for(redirect_endpoint) if redirect_endpoint else request.path)
            return func(*args, **kwargs)

        return wrapper

    return decorate(view) if view is not None else decorate
