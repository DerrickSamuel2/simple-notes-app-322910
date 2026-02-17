#!/usr/bin/env python3
"""Initialize SQLite database for the notes app (database container).

This script is safe to run multiple times:
- Ensures core tables exist (idempotent CREATE TABLE IF NOT EXISTS).
- Writes connection helper files for developers and the bundled DB visualizer.
"""

import os
import sqlite3
from pathlib import Path

DB_NAME = "myapp.db"
DB_USER = "kaviasqlite"  # Not used for SQLite, but kept for consistency
DB_PASSWORD = "kaviadefaultpassword"  # Not used for SQLite, but kept for consistency
DB_PORT = "5000"  # Not used for SQLite, but kept for consistency


def _connect(db_path: str) -> sqlite3.Connection:
    """Create a SQLite connection with recommended pragmas enabled."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    # Improve correctness and concurrent-read behavior. WAL is safe for single-file DB usage.
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    """Create required tables if they do not already exist."""
    cursor = conn.cursor()

    # App metadata table (kept from template; harmless and useful for debugging).
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS app_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            value TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # Notes table for the application.
    # Timestamps:
    # - created_at: set on insert (default CURRENT_TIMESTAMP)
    # - updated_at: set on insert, and maintained via trigger on UPDATE
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # Trigger to auto-update updated_at on any UPDATE.
    cursor.execute(
        """
        CREATE TRIGGER IF NOT EXISTS notes_set_updated_at
        AFTER UPDATE ON notes
        FOR EACH ROW
        BEGIN
            UPDATE notes
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = OLD.id;
        END;
        """
    )

    # Optional sample users table (left intact for compatibility with existing tooling).
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn.commit()


def _write_connection_files(db_path: str) -> None:
    """Write db_connection.txt and db_visualizer/sqlite.env with the absolute DB path."""
    current_dir = os.getcwd()
    connection_string = f"sqlite:///{current_dir}/{DB_NAME}"

    try:
        with open("db_connection.txt", "w", encoding="utf-8") as f:
            f.write("# SQLite connection methods:\n")
            f.write(f"# Python: sqlite3.connect('{DB_NAME}')\n")
            f.write(f"# Connection string: {connection_string}\n")
            f.write(f"# File path: {current_dir}/{DB_NAME}\n")
        print("Connection information saved to db_connection.txt")
    except Exception as e:
        print(f"Warning: Could not save connection info: {e}")

    # Create environment variables file for Node.js viewer
    if not os.path.exists("db_visualizer"):
        os.makedirs("db_visualizer", exist_ok=True)
        print("Created db_visualizer directory")

    try:
        with open("db_visualizer/sqlite.env", "w", encoding="utf-8") as f:
            f.write(f'export SQLITE_DB="{db_path}"\n')
        print("Environment variables saved to db_visualizer/sqlite.env")
    except Exception as e:
        print(f"Warning: Could not save environment variables: {e}")


def _print_stats(conn: sqlite3.Connection) -> None:
    """Print basic DB statistics (table count, etc.)."""
    cursor = conn.cursor()

    cursor.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )
    table_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM app_info")
    record_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM notes")
    notes_count = cursor.fetchone()[0]

    print("Database statistics:")
    print(f"  Tables: {table_count}")
    print(f"  App info records: {record_count}")
    print(f"  Notes records: {notes_count}")


def main() -> None:
    """Entry point: ensure the SQLite DB exists and has the required schema."""
    print("Starting SQLite setup...")

    db_exists = os.path.exists(DB_NAME)
    if db_exists:
        print(f"SQLite database already exists at {DB_NAME}")
    else:
        print("Creating new SQLite database...")

    db_path = os.path.abspath(DB_NAME)

    # Ensure parent directory exists (generally true, but keeps script robust).
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    try:
        conn = _connect(DB_NAME)
        conn.execute("SELECT 1")
        _ensure_schema(conn)

        # Seed app_info (idempotent).
        conn.execute(
            "INSERT OR REPLACE INTO app_info (key, value) VALUES (?, ?)",
            ("project_name", "database"),
        )
        conn.execute(
            "INSERT OR REPLACE INTO app_info (key, value) VALUES (?, ?)",
            ("version", "0.1.0"),
        )
        conn.execute(
            "INSERT OR REPLACE INTO app_info (key, value) VALUES (?, ?)",
            ("author", "John Doe"),
        )
        conn.execute(
            "INSERT OR REPLACE INTO app_info (key, value) VALUES (?, ?)",
            ("description", ""),
        )
        conn.commit()

        print("Database is accessible and schema is ensured.")
        _write_connection_files(db_path)

        print("\nSQLite setup complete!")
        print(f"Database: {DB_NAME}")
        print(f"Location: {os.getcwd()}/{DB_NAME}\n")

        print("To use with Node.js viewer, run: source db_visualizer/sqlite.env\n")

        print("To connect to the database, use one of the following methods:")
        print(f"1. Python: sqlite3.connect('{DB_NAME}')")
        print(f"2. Connection string: sqlite:///{os.getcwd()}/{DB_NAME}")
        print(f"3. Direct file access: {os.getcwd()}/{DB_NAME}\n")

        _print_stats(conn)

        # If sqlite3 CLI is available, show how to use it
        try:
            import subprocess

            result = subprocess.run(["which", "sqlite3"], capture_output=True, text=True)
            if result.returncode == 0:
                print("\nSQLite CLI is available. You can also use:")
                print(f"  sqlite3 {DB_NAME}")
        except Exception:
            pass

        print("\nScript completed successfully.")
    except Exception as e:
        print(f"Error: SQLite setup failed: {e}")
        raise
    finally:
        try:
            if "conn" in locals():
                conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
