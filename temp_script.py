import sqlite3

# Initialize SQLite for devices
conn = sqlite3.connect("devices.db", check_same_thread=False)
cursor = conn.cursor()

# Create table with house_id if it doesn't exist
cursor.execute("""
CREATE TABLE IF NOT EXISTS devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    house_id TEXT NOT NULL,
    device_name TEXT NOT NULL,
    energy_usage REAL DEFAULT 0,  -- Energy in kWh
    uptime TEXT DEFAULT '00:00'   -- Uptime in HH:MM format
)
""")
conn.commit()

# Alter table to add house_id if it doesn't exist
try:
    cursor.execute("ALTER TABLE devices ADD COLUMN house_id TEXT;")
except sqlite3.OperationalError as e:
    if 'duplicate column name: house_id' not in str(e):
        raise e

# Commit changes
conn.commit()
