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
    conn = get_db_connection()
    result = conn.execute('SELECT is_active FROM tenants WHERE name = ?', (tenant,)).fetchone()
    conn.close()
    return result and result['is_active'] == 1

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        tenant = request.form['tenant'].strip().lower()
        username = request.form['username'].strip()
        return redirect(url_for('dashboard', tenant=tenant))
    return render_template('login.html')

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/<tenant>/welcome')
def welcome(tenant):
    if not is_tenant_active(tenant):
        return render_template('billing-lock.html', tenant=tenant)
    return render_template('welcome.html', tenant=tenant)

@app.route('/<tenant>/setup-checklist')
def setup_checklist(tenant):
    if not is_tenant_active(tenant):
        return render_template('billing-lock.html', tenant=tenant)

    conn = get_db_connection()
    has_products = conn.execute('SELECT COUNT(*) FROM products').fetchone()[0] > 0
    has_sales = conn.execute('SELECT COUNT(*) FROM sales').fetchone()[0] > 0
    conn.close()

    return render_template('setup-checklist.html', tenant=tenant,
                           has_products=has_products,
                           has_sales=has_sales)

@app.route('/admin/tenants', methods=['GET', 'POST'])
def manage_tenants():
    conn = get_db_connection()

    if request.method == 'POST':
        name = request.form['name'].strip().lower()
        is_active = 1 if request.form.get('is_active') == 'on' else 0
        conn.execute('INSERT OR REPLACE INTO tenants (name, is_active) VALUES (?, ?)', (name, is_active))
        conn.commit()

    tenants = conn.execute('SELECT * FROM tenants').fetchall()
    conn.close()
    return render_template('manage-tenants.html', tenants=tenants)

@app.route('/<tenant>/dashboard')
def dashboard(tenant):
    if not is_tenant_active(tenant):
        return render_template('billing-lock.html', tenant=tenant)

    conn = get_db_connection()
    has_products = conn.execute('SELECT COUNT(*) FROM products').fetchone()[0] > 0
    has_sales = conn.execute('SELECT COUNT(*) FROM sales').fetchone()[0] > 0

    if not (has_products or has_sales):
        conn.close()
        return redirect(url_for('welcome', tenant=tenant))

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
    sales = {
        "labels": [row["sale_date"] for row in sales_rows],
        "values": [row["total"] for row in sales_rows]
    }

    top_rows = conn.execute("""
        SELECT p.name, SUM(si.quantity) as qty
        FROM sale_items si
        JOIN products p ON p.id = si.product_id
        GROUP BY si.product_id
        ORDER BY qty DESC
        LIMIT 5
    """).fetchall()
    top_products = {
        "labels": [row["name"] for row in top_rows],
        "values": [row["qty"] for row in top_rows]
    }

    stock_rows = conn.execute("SELECT name, quantity FROM products").fetchall()
    stock = {
        "labels": [row["name"] for row in stock_rows],
        "values": [row["quantity"] for row in stock_rows]
    }

    conn.close()
    return jsonify({"sales": sales, "top_products": top_products, "stock": stock})

@app.route('/<tenant>/add-stock', methods=['GET', 'POST'])
def add_stock(tenant):
    if not is_tenant_active(tenant):
        return render_template('billing-lock.html', tenant=tenant)
    if request.method == 'POST':
        name = request.form['name']
        quantity = int(request.form['quantity'])
        price = float(request.form['price'])

        conn = get_db_connection()
        conn.execute('INSERT INTO products (name, quantity, price) VALUES (?, ?, ?)', (name, quantity, price))
        conn.commit()
        conn.close()

        return redirect(url_for('view_products', tenant=tenant))

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
        customer = request.form['customer']
        product_ids = request.form.getlist('product_id')
        quantities = request.form.getlist('quantity')

        total = 0
        items = []

        for pid, qty in zip(product_ids, quantities):
            qty = int(qty)
            if qty <= 0:
                continue
            product = conn.execute('SELECT * FROM products WHERE id = ?', (pid,)).fetchone()
            subtotal = product['price'] * qty
            total += subtotal
            items.append((pid, qty, product['price']))
            conn.execute('UPDATE products SET quantity = quantity - ? WHERE id = ?', (qty, pid))

        if not items:
            conn.close()
            return redirect(url_for('record_sale', tenant=tenant))

        vat = total * 0.16
        grand_total = total + vat

        cursor = conn.cursor()
        cursor.execute('INSERT INTO sales (customer, total_amount, vat, grand_total, date) VALUES (?, ?, ?, ?, ?)',
                       (customer, total, vat, grand_total, datetime.now()))
        sale_id = cursor.lastrowid

        for pid, qty, price in items:
            cursor.execute('INSERT INTO sale_items (sale_id, product_id, quantity, price) VALUES (?, ?, ?, ?)',
                           (sale_id, pid, qty, price))

        conn.commit()
        conn.close()

        return redirect(url_for('sales_history', tenant=tenant))

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
