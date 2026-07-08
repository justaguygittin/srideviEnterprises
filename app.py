from flask import Flask, render_template
from typing import Any
from database.db import get_connection

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("customer/home.html")


@app.route("/products")
def products():
    return render_template("customer/products.html")


@app.route("/contact")
def contact():
    return render_template("customer/contact.html")


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
