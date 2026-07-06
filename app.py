from flask import Flask, render_template
from database.db import get_connection

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/products")
def products():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT product_id,
               product_name,
               brand,
               category,
               offer_price
        FROM Catalog
        ORDER BY product_name
    """)

    products = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "products.html",
        products=products
    )

if __name__ == "__main__":
    app.run(debug=True)