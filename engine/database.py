import os
import sqlite3


def create_database(db_path="generated_app/database/saas.db"):
    """
    Creates a SQLite database for the generated SaaS app.
    If the database already exists, it will not overwrite it.
    """

    # Step 1 — Ensure folder exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    # Step 2 — Connect to database (creates file if not exists)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Step 3 — Create basic SaaS tables

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Example: simple items table (you can expand later)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            description TEXT,
            user_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    # Step 4 — Save changes
    conn.commit()

    # Step 5 — Close connection
    conn.close()

    print(f"Database created successfully at: {db_path}")