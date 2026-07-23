from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from config import Config
from routes.customer import customer_bp
from routes.employee import employee_bp
from routes.admin import admin_bp
from routes.api import api_bp

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


if Config.DEBUG:
    @app.route("/routes")
    def routes():
        return "<br>".join(str(r) for r in app.url_map.iter_rules())


if __name__ == "__main__":
    app.run(debug=Config.DEBUG)
