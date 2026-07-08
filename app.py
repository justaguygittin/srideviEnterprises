from database.db import get_connection
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


@app.route("/db-test")
def db_test():

    try:
        conn = get_connection()

        return "✅ Connected Successfully"

    except Exception as e:

        return str(e)

    finally:

        try:
            conn.close()
        except:
            pass


if __name__ == "__main__":
    app.run(debug=True)
