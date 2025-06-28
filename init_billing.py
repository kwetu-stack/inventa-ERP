import sqlite3

conn = sqlite3.connect('inventory.db')
cursor = conn.cursor()

# Create tenants table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS tenants (
        name TEXT PRIMARY KEY,
        is_active INTEGER DEFAULT 1
    )
''')

# Add test tenant
cursor.execute('INSERT OR IGNORE INTO tenants (name, is_active) VALUES (?, ?)', ('alamudi', 1))
cursor.execute('INSERT OR IGNORE INTO tenants (name, is_active) VALUES (?, ?)', ('testclient', 0))

conn.commit()
conn.close()

print("Tenants table initialized.")
