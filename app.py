from flask import Flask, render_template, request, redirect, url_for, send_file, abort, make_response, jsonify
import sqlite3
from datetime import datetime
import pdfkit
import qrcode
import os

app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect('inventory.db')
    conn.row_factory = sqlite3.Row
    return conn

def is_tenant_active(tenant):
    if tenant in ["testclient", "inventa"]:  # Demo tenants are always active
        return True
    conn = get_db_connection()
    result = conn.execute('SELECT is_active FROM tenants WHERE name = ?', (tenant,)).fetchone()
    conn.close()
    return result and result['is_active'] == 1

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/<tenant>/dashboard')
def dashboard(tenant):
    if not is_tenant_active(tenant):
        return render_template('billing-lock.html', tenant=tenant)
    conn = get_db_connection()
    total_products = conn.execute('SELECT COUNT(*) FROM products').fetchone()[0]
    total_sales = conn.execute('SELECT SUM(total_amount) FROM sales').fetchone()[0] or 0
    conn.close()
    return render_template('dashboard.html', tenant=tenant, total_products=total_products, total_sales=total_sales)

@app.route('/<tenant>/dashboard-data')
def dashboard_data(tenant):
    if not is_tenant_active(tenant):
        return jsonify({})
    conn = get_db_connection()

    sales_rows = conn.execute("""
        SELECT DATE(date) as sale_date, SUM(grand_total) as total
        FROM sales
        GROUP BY DATE(date)
        ORDER BY DATE(date)
    """).fetchall()

    top_rows = conn.execute("""
        SELECT p.name, SUM(si.quantity) as qty
        FROM sale_items si
        JOIN products p ON p.id = si.product_id
        GROUP BY si.product_id
        ORDER BY qty DESC
        LIMIT 5
    """).fetchall()

    stock_rows = conn.execute("SELECT name, quantity FROM products").fetchall()

    conn.close()
    return jsonify({
        "sales": {
            "labels": [row["sale_date"] for row in sales_rows],
            "values": [row["total"] for row in sales_rows]
        },
        "top_products": {
            "labels": [row["name"] for row in top_rows],
            "values": [row["qty"] for row in top_rows]
        },
        "stock": {
            "labels": [row["name"] for row in stock_rows],
            "values": [row["quantity"] for row in stock_rows]
        }
    })

@app.route('/<tenant>/add-stock', methods=['GET', 'POST'])
def add_stock(tenant):
    if not is_tenant_active(tenant):
        return render_template('billing-lock.html', tenant=tenant)
    if request.method == 'POST':
        return render_template('demo-lock.html', tenant=tenant)
    return render_template('add-stock.html', tenant=tenant)

@app.route('/<tenant>/products')
def view_products(tenant):
    if not is_tenant_active(tenant):
        return render_template('billing-lock.html', tenant=tenant)
    conn = get_db_connection()
    products = conn.execute('SELECT * FROM products').fetchall()
    conn.close()
    return render_template('view-products.html', tenant=tenant, products=products)

@app.route('/<tenant>/record-sale', methods=['GET', 'POST'])
def record_sale(tenant):
    if not is_tenant_active(tenant):
        return render_template('billing-lock.html', tenant=tenant)

    conn = get_db_connection()
    products = conn.execute('SELECT * FROM products').fetchall()

    if request.method == 'POST':
        return render_template('demo-lock.html', tenant=tenant)

    return render_template('record-sale.html', tenant=tenant, products=products)

@app.route('/<tenant>/sales-history')
def sales_history(tenant):
    if not is_tenant_active(tenant):
        return render_template('billing-lock.html', tenant=tenant)
    conn = get_db_connection()
    sales = conn.execute('SELECT * FROM sales ORDER BY date DESC').fetchall()
    conn.close()
    return render_template('sales-history.html', tenant=tenant, sales=sales)

@app.route('/<tenant>/invoice/<int:sale_id>')
def download_invoice(tenant, sale_id):
    if not is_tenant_active(tenant):
        return render_template('billing-lock.html', tenant=tenant)
    
    conn = get_db_connection()
    sale = conn.execute('SELECT * FROM sales WHERE id = ?', (sale_id,)).fetchone()
    items = conn.execute('''
        SELECT si.quantity, si.price, p.name 
        FROM sale_items si
        JOIN products p ON si.product_id = p.id
        WHERE si.sale_id = ?
    ''', (sale_id,)).fetchall()
    conn.close()

    qr_data = f"Inventa Invoice\nTenant: {tenant}\nInvoice #: {sale_id}\nCustomer: {sale['customer']}"
    qr_file = f'static/qr_{sale_id}.png'
    if not os.path.exists(qr_file):
        qr = qrcode.make(qr_data)
        qr.save(qr_file)

    rendered = render_template('invoice.html', tenant=tenant, sale=sale, items=items,
                               qr_file=os.path.abspath(qr_file).replace('\\\\', '/'))

    config = pdfkit.configuration(wkhtmltopdf='C:/Program Files/wkhtmltopdf/bin/wkhtmltopdf.exe')
    pdf = pdfkit.from_string(rendered, False, configuration=config, options={
        'enable-local-file-access': ''
    })

    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=invoice_{sale_id}.pdf'
    return response

if __name__ == '__main__':
    app.run(debug=True)
