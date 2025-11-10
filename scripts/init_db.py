#!/usr/bin/env python3
"""
Initialize the database with required tables.
Note: With the new SQLite implementation, tables are created automatically
on first import. This script is kept for backwards compatibility and
can be used to verify database initialization.
"""

import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.database import db


def init_database():
    """Initialize the database (tables are auto-created on import)"""
    print("Initializing database...")
    print(f"Database path: {db.db_path}")

    # Database is already initialized in the Database.__init__ method
    # This just verifies connectivity
    with db.get_connection() as conn:
        cursor = conn.cursor()

        # Verify tables exist
        cursor.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='table'
            ORDER BY name
        """
        )
        tables = cursor.fetchall()

        print("\nExisting tables:")
        for table in tables:
            print(f"  - {table[0]}")

    print("\nDatabase initialization verified successfully!")


if __name__ == "__main__":
    init_database()
