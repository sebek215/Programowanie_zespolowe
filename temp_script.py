import sqlite3

# Connect to the database
conn = sqlite3.connect("devices.db")
cursor = conn.cursor()

# Add new columns to the 'devices' table
try:
    cursor.execute("ALTER TABLE devices ADD COLUMN energy_usage REAL DEFAULT 0;")
    cursor.execute("ALTER TABLE devices ADD COLUMN uptime TEXT DEFAULT '00:00';")
    conn.commit()
    print("Columns added successfully!")
except sqlite3.OperationalError as e:
    print(f"Error: {e}")

# Close the connection
conn.close()
