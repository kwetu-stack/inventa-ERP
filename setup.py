import sqlite3

conn = sqlite3.connect('inventa.db')

conn.execute('''
    CREATE TABLE IF NOT EXISTS tenants (
        name TEXT PRIMARY KEY,
        is_active INTEGER NOT NULL DEFAULT 1
    )
''')

print("Tenants table created.")
conn.commit()
conn.close()
