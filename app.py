from flask import Flask

from routes.customer import customer_bp
from routes.employee import employee_bp
from routes.admin import admin_bp
from routes.api import api_bp

app = Flask(__name__)

app.register_blueprint(customer_bp)
app.register_blueprint(employee_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(api_bp)


@app.route("/routes")
def routes():
    return "<br>".join(str(r) for r in app.url_map.iter_rules())


if __name__ == "__main__":
    app.run(debug=True)
