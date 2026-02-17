#!/usr/bin/env python3
"""Reset SQLite database for the notes app.

This utility is intended for local/dev usage to get back to a clean state:
- Drops the notes table (and its trigger) and recreates the schema by invoking init logic.
- Leaves the database file in place, ensuring tooling that expects the file continues to work.

Usage:
  python3 reset_db.py

Notes:
- This script is intentionally conservative and only resets the application tables.
"""

import os
import sqlite3

import init_db

DB_NAME = "myapp.db"


def _connect(db_path: str) -> sqlite3.Connection:
    """Create a SQLite connection with foreign keys enabled."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def main() -> None:
    """Entry point for resetting the DB schema/data related to the notes app."""
    if not os.path.exists(DB_NAME):
        # If DB doesn't exist, just initialize it.
        init_db.main()
        return

    conn = _connect(DB_NAME)
    try:
        cur = conn.cursor()

        # Drop trigger first (SQLite may drop it with table drop, but this is explicit and reliable).
        cur.execute("DROP TRIGGER IF EXISTS notes_set_updated_at")

        # Drop and recreate notes table.
        cur.execute("DROP TABLE IF EXISTS notes")

        conn.commit()
    finally:
        conn.close()

    # Recreate schema and helper files.
    init_db.main()


if __name__ == "__main__":
    main()
