import sqlite3

conn = sqlite3.connect('inventory.db')
cursor = conn.cursor()

# Products table
cursor.execute('''
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    price REAL NOT NULL
)
''')

# Sales table
cursor.execute('''
CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer TEXT NOT NULL,
    total_amount REAL NOT NULL,
    vat REAL NOT NULL,
    grand_total REAL NOT NULL,
    date TEXT NOT NULL
)
''')

# Sale items table
cursor.execute('''
CREATE TABLE IF NOT EXISTS sale_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_id INTEGER,
    product_id INTEGER,
    quantity INTEGER,
    price REAL,
    FOREIGN KEY(sale_id) REFERENCES sales(id),
    FOREIGN KEY(product_id) REFERENCES products(id)
)
''')

# Tenants table
cursor.execute('''
CREATE TABLE IF NOT EXISTS tenants (
    name TEXT PRIMARY KEY,
    is_active INTEGER DEFAULT 1
)
''')

# Insert demo tenants
cursor.execute("INSERT OR REPLACE INTO tenants (name, is_active) VALUES ('alamudi', 1)")
cursor.execute("INSERT OR REPLACE INTO tenants (name, is_active) VALUES ('examplecorp', 0)")
cursor.execute("INSERT OR REPLACE INTO tenants (name, is_active) VALUES ('testclient', 1)")

conn.commit()
conn.close()

print("✅ All database tables created and demo tenants added.")
