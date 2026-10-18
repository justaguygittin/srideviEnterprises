import logging
import sys

from flask import Flask, abort, jsonify, make_response, render_template, request, session, url_for
from werkzeug.middleware.proxy_fix import ProxyFix

from config import Config
from routes.customer import customer_bp
from routes.employee import employee_bp
from routes.admin import admin_bp
from routes.api import api_bp
from routes.receipts import receipts_bp
from services.maintenance_service import is_maintenance_enabled, verify_maintenance_key

_LOG_FORMAT = "%(asctime)s %(levelname)-8s [%(name)s:%(process)d] %(message)s"


def configure_logging():
    """
    Send application logs to stderr in a consistent, timestamped format.

    v1.0 Sprint 11 (RC-5). Before this, the application logged nothing at
    all: several write paths caught exceptions, showed the user a generic
    "please try again" message, and discarded the actual error. On shared
    hosting that left no way to find out why anything failed.

    Why stderr: Passenger captures a Python app's stderr into the error log
    reachable from cPanel's "Setup Python App" page, which DEPLOYMENT.md
    already tells operators to check when something goes wrong. That makes
    stderr the one destination that needs no new configuration, no writable
    log directory, and no log-rotation story on a shared host.

    Configured on the ROOT logger, so the module-level
    logging.getLogger(__name__) loggers in routes/ and services/ propagate
    into the same stream and format. This runs before anything touches
    app.logger, which matters: Flask only attaches its own default handler
    when it finds no handler anywhere up the hierarchy, so configuring the
    root first is what prevents every record being emitted twice.

    Level comes from Config.LOG_LEVEL (default INFO). An unrecognised value
    falls back to INFO rather than raising - a typo in .env must never stop
    the site from booting.
    """

    level = getattr(logging, Config.LOG_LEVEL, None)
    if not isinstance(level, int):
        level = logging.INFO

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Passenger may import this module more than once per process; adding a
    # second identical handler would double every line.
    if not any(getattr(h, "_sridevi_handler", False) for h in root_logger.handlers):
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter(_LOG_FORMAT))
        handler._sridevi_handler = True
        root_logger.addHandler(handler)

    return root_logger


configure_logging()

app = Flask(__name__)

# HostyCare's Apache terminates TLS and proxies plain HTTP to Passenger, so
# Flask must trust the proxy's X-Forwarded-Proto/Host headers to know a
# request was actually served over HTTPS (needed for secure cookies/redirects).
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

app.secret_key = Config.SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = Config.MAX_CONTENT_LENGTH

# Session cookie hardening (v1.0 Sprint 11) - see config.py for the reasoning
# behind each value. ProxyFix above is what makes SESSION_COOKIE_SECURE work
# behind HostyCare's TLS-terminating proxy: without it Flask would only ever
# see plain HTTP and would refuse to set a secure cookie at all.
app.config["SESSION_COOKIE_HTTPONLY"] = Config.SESSION_COOKIE_HTTPONLY
app.config["SESSION_COOKIE_SAMESITE"] = Config.SESSION_COOKIE_SAMESITE
app.config["SESSION_COOKIE_SECURE"] = Config.SESSION_COOKIE_SECURE

app.register_blueprint(customer_bp)
app.register_blueprint(employee_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(api_bp)
app.register_blueprint(receipts_bp)

# One line per worker start. After a Passenger restart this is the first thing
# in the error log, and it answers the same question GET /health answers -
# which version actually came up - without needing to make a request.
app.logger.info(
    "Sridevi Enterprises starting - version=%s debug=%s log_level=%s "
    "session_cookie(secure=%s httponly=%s samesite=%s) whatsapp=%s",
    Config.APP_VERSION,
    Config.DEBUG,
    Config.LOG_LEVEL,
    Config.SESSION_COOKIE_SECURE,
    Config.SESSION_COOKIE_HTTPONLY,
    Config.SESSION_COOKIE_SAMESITE,
    "enabled" if Config.WHATSAPP_NUMBER else "disabled",
)

if Config.WHATSAPP_NUMBER_REJECTED:
    # A value was supplied but is unusable, so every WhatsApp button is
    # hidden. Logged so that is visible rather than a silent "why is the
    # button missing". The value itself is deliberately not logged.
    app.logger.warning(
        "WHATSAPP_BUSINESS_NUMBER is set but is not a valid international number - "
        "WhatsApp buttons are disabled. Write it with a leading + and country code, "
        "e.g. +91 followed by the 10-digit number."
    )

if not Config.SESSION_COOKIE_SECURE:
    # Expected and required for local HTTP development; wrong in production.
    # Logged every worker start so an accidental opt-out on the server shows
    # up in the error log instead of going unnoticed until it matters.
    app.logger.warning(
        "SESSION_COOKIE_SECURE is False - the session cookie may be sent over plain HTTP. "
        "This is expected in local development only. Set SESSION_COOKIE_SECURE=True (or "
        "remove it from .env) on any HTTPS deployment."
    )


@app.before_request
def enforce_maintenance_mode():
    """
    Gate every customer-facing page behind Maintenance Mode
    (config/maintenance.json) - see AI_CONTEXT.md "Maintenance Mode".

    Only `customer_bp` routes are customer-facing, so this only fires for
    request.blueprint == "customer". That also means /health, static
    files, and the Employee/Admin Portal itself (blueprint None or
    "employee"/"admin") are never gated - the Employee Portal must keep
    working normally during a deploy.

    A request is let through (HTTP 503 is NOT returned) if any of:
      1. Maintenance Mode is disabled.
      2. The session has a logged-in Employee/Admin (session["UserID"]) -
         bug fix, Sprint 8 Review follow-up: an employee verifying the
         live public site right after a deploy is one of Maintenance
         Mode's primary use cases, and forcing them to also know/paste
         the separate bypass key on top of their own login defeated that.
         Their Employee login already proves who they are; RBAC on the
         Employee Portal itself is untouched by this - this only widens
         what an *already-authenticated* employee session can see on the
         customer site during maintenance.
      3. The session has a verified maintenance bypass
         (session["maintenance_verified"]), set below when a correct
         ?maintenance_key= is supplied - this is what lets an anonymous
         visitor (e.g. a client without an Employee account) reach the
         site too.

    Only a fully anonymous visitor - no Employee session, no verified
    bypass session - ever receives HTTP 503. See
    inject_maintenance_banner_state() below for how either bypass path is
    surfaced back to the visitor via the banner.
    """

    if request.blueprint != "customer" or not is_maintenance_enabled():
        return None

    candidate_key = request.args.get("maintenance_key")
    if candidate_key and verify_maintenance_key(candidate_key):
        session["maintenance_verified"] = True

    if session.get("maintenance_verified") or session.get("UserID"):
        return None

    abort(503)


@app.context_processor
def inject_maintenance_banner_state():
    """
    Compute whether the "Maintenance Mode" banner should render on this
    page, so templates never need to read `session`/`request` directly -
    matching this codebase's convention of routes (and here, a context
    processor) preparing plain values for templates.

    Mirrors enforce_maintenance_mode()'s two ways through the gate (a
    logged-in Employee/Admin, or a verified bypass session) - either one
    means this visitor is seeing the live customer site while the public
    is not, so either should see the reminder.
    """

    show_banner = (
        request.blueprint == "customer"
        and is_maintenance_enabled()
        and bool(session.get("maintenance_verified") or session.get("UserID"))
    )
    return {"show_maintenance_banner": show_banner}


@app.context_processor
def inject_business_details():
    """
    Expose the showroom's configured contact details (Config.BUSINESS_*)
    to every template as a single `business` dict - v1.0 Sprint 11.

    A context processor rather than per-route context, for one concrete
    reason: the standalone Maintenance Mode screen (templates/errors/
    503.html) is rendered by @app.errorhandler(503) below, which has no
    route and therefore no place to pass context through. The sitewide
    footer has the same problem in reverse - it is included by
    layout/base.html on every page, so passing these values explicitly
    would mean touching every single route. This mirrors
    inject_maintenance_banner_state() above: values are prepared in
    Python and handed to templates as plain data, so no template ever
    reads configuration itself.

    Every value may legitimately be an empty string (see config.py) -
    templates must render each line only when its value is set, so an
    unconfigured deployment shows nothing rather than fake contact
    details.
    """

    return {
        "business": {
            "address": Config.BUSINESS_ADDRESS,
            "phone": Config.BUSINESS_PHONE,
            "phone_href": Config.BUSINESS_PHONE_HREF,
            "email": Config.BUSINESS_EMAIL,
            "website": Config.BUSINESS_WEBSITE,
            "website_href": Config.BUSINESS_WEBSITE_HREF,
            "hours": Config.BUSINESS_HOURS,
        }
    }


@app.context_processor
def inject_whatsapp():
    """
    Expose the floating WhatsApp button's state to every template as a
    `whatsapp` dict, mirroring inject_business_details() above.

    `show_floating` is True only when a valid number is configured AND the
    request is for a customer-facing page. The blueprint check matters
    because layout/base.html is shared with the Employee Portal, the
    Invoice Generator, and the login page - none of which should carry a
    customer contact button. `url` is "" whenever `show_floating` is False.

    `url` is this site's own /whatsapp redirect route, not wa.me itself,
    so the configured number never appears in any page's HTML - it is
    only revealed by the redirect when a customer actually clicks.
    """

    show_floating = bool(Config.WHATSAPP_NUMBER) and request.blueprint == "customer"
    return {
        "whatsapp": {
            "show_floating": show_floating,
            "url": url_for("customer.whatsapp_chat") if show_floating else "",
        }
    }


@app.route("/health")
def health():
    """
    Liveness check used after a Passenger restart - see DEPLOYMENT.md.

    Includes the live `maintenance` state and `version` (Config.APP_VERSION)
    so a deploy can confirm both "the process is up" and "it's actually
    running Maintenance Mode / the code I expect" from one request, instead
    of needing a second request against a customer page to check the first
    and a code read to check the second.
    """

    return jsonify(
        status="ok",
        maintenance=is_maintenance_enabled(),
        version=Config.APP_VERSION,
    )


@app.errorhandler(403)
def forbidden(error):
    return render_template("errors/403.html"), 403


@app.errorhandler(404)
def not_found(error):
    return render_template("errors/404.html"), 404


@app.errorhandler(500)
def server_error(error):
    return render_template("errors/500.html"), 500


@app.errorhandler(413)
def payload_too_large(error):
    """
    Branded page for a request exceeding Config.MAX_CONTENT_LENGTH - most
    likely a product/department image upload past the configured limit
    (v1.1 Sprint 12). 400/405 remain unbranded (deferred, see AI_CONTEXT.md).
    """

    return render_template("errors/413.html"), 413


@app.errorhandler(503)
def maintenance(error):
    """
    Render the Maintenance Mode page with explicit no-cache headers, so a
    browser or intermediate proxy can never keep serving this page from
    cache after maintenance has been disabled - the next request after
    disabling must always reach the live app and get a fresh answer.
    """

    response = make_response(render_template("errors/503.html"), 503)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


if Config.DEBUG:
    @app.route("/routes")
    def routes():
        return "<br>".join(str(r) for r in app.url_map.iter_rules())


if __name__ == "__main__":
    app.run(debug=Config.DEBUG)
