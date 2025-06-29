from flask import Flask, render_template, request, redirect, url_for, send_file
import sqlite3
import pdfkit
from datetime import datetime
from num2words import num2words

app = Flask(__name__)

# --- DATABASE HELPER ---
def get_db_connection():
    conn = sqlite3.connect('inventory.db')
    conn.row_factory = sqlite3.Row
    return conn

# --- ROUTES ---
@app.route("/")
def home():
    return render_template("home.html")

@app.route("/inventa/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/inventa/add-stock", methods=["GET", "POST"])
def add_stock():
    if request.method == "POST":
        return render_template("demo-lock.html")
    return render_template("add-stock.html")

@app.route("/inventa/view-products")
def view_products():
    conn = get_db_connection()
    products = conn.execute("SELECT * FROM products").fetchall()
    conn.close()
    return render_template("view-products.html", products=products)

@app.route("/inventa/record-sale", methods=["GET", "POST"])
def record_sale():
    if request.method == "POST":
        return render_template("demo-lock.html")
    conn = get_db_connection()
    products = conn.execute("SELECT * FROM products").fetchall()
    conn.close()
    return render_template("record-sale.html", products=products)

@app.route("/inventa/sales-history")
def sales_history():
    conn = get_db_connection()
    sales = conn.execute("SELECT * FROM sales ORDER BY date DESC").fetchall()
    conn.close()
    return render_template("sales-history.html", sales=sales)

@app.route("/inventa/invoice/<int:sale_id>")
def download_invoice(sale_id):
    conn = get_db_connection()
    sale = conn.execute("SELECT * FROM sales WHERE id = ?", (sale_id,)).fetchone()
    items = conn.execute("SELECT * FROM sale_items WHERE sale_id = ?", (sale_id,)).fetchall()
    conn.close()

    total_in_words = num2words(sale["grand_total"], to="currency", lang="en")
    rendered = render_template("invoice.html", sale=sale, items=items, total_in_words=total_in_words)
    pdf = pdfkit.from_string(rendered, False)
    
    with open("invoice.pdf", "wb") as f:
        f.write(pdf)

    return send_file("invoice.pdf", as_attachment=True)

# --- ENTRY POINT ---
if __name__ == "__main__":
    app.run(debug=True)
