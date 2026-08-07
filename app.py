from flask import Flask, abort, jsonify, make_response, render_template, request, session
from werkzeug.middleware.proxy_fix import ProxyFix

from config import Config
from routes.customer import customer_bp
from routes.employee import employee_bp
from routes.admin import admin_bp
from routes.api import api_bp
from services.maintenance_service import is_maintenance_enabled, verify_maintenance_key

app = Flask(__name__)

# HostyCare's Apache terminates TLS and proxies plain HTTP to Passenger, so
# Flask must trust the proxy's X-Forwarded-Proto/Host headers to know a
# request was actually served over HTTPS (needed for secure cookies/redirects).
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

app.secret_key = Config.SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = Config.MAX_CONTENT_LENGTH

app.register_blueprint(customer_bp)
app.register_blueprint(employee_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(api_bp)


@app.before_request
def enforce_maintenance_mode():
    """
    Gate every customer-facing page behind Maintenance Mode
    (config/maintenance.json) - see AI_CONTEXT.md "Maintenance Mode".

    Only `customer_bp` routes are customer-facing, so this only fires for
    request.blueprint == "customer". That also means /health, static
    files, and the Employee/Admin Portal (blueprint None or "employee"/
    "admin") are never gated - the Employee Portal must keep working
    normally during a deploy, and customer session doesn't carry any
    Employee login info to check instead.

    A verified maintenance_key (session["maintenance_verified"]) lets the
    bypassed visitor reach the whole customer site while maintenance stays
    on for everyone else - see inject_maintenance_banner_state() below for
    how that session is surfaced back to the visitor.
    """

    if request.blueprint != "customer" or not is_maintenance_enabled():
        return None

    candidate_key = request.args.get("maintenance_key")
    if candidate_key and verify_maintenance_key(candidate_key):
        session["maintenance_verified"] = True

    if session.get("maintenance_verified"):
        return None

    abort(503)


@app.context_processor
def inject_maintenance_banner_state():
    """
    Compute whether the "Maintenance Mode Active" banner should render on
    this page, so templates never need to read `session`/`request`
    directly - matching this codebase's convention of routes (and here, a
    context processor) preparing plain values for templates.
    """

    show_banner = (
        request.blueprint == "customer"
        and is_maintenance_enabled()
        and bool(session.get("maintenance_verified"))
    )
    return {"show_maintenance_banner": show_banner}


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
