from flask import Flask, render_template

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


if __name__ == "__main__":
    app.run(debug=True)