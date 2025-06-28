import sqlite3

conn = sqlite3.connect('inventory.db')
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    price REAL NOT NULL
)
''')

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

conn.commit()
conn.close()
print("✅ Database tables created.")

CREATE TABLE IF NOT EXISTS tenants (
    name TEXT PRIMARY KEY,
    is_active INTEGER DEFAULT 1
);
INSERT INTO tenants (name, is_active) VALUES ('alamudi', 1);
INSERT INTO tenants (name, is_active) VALUES ('examplecorp', 0);
