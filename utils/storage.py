import json
import sqlite3
import hashlib
from datetime import datetime
from pathlib import Path

DB_DIR = Path("data")
DB_PATH = DB_DIR / "smartquizzer.db"


def _connect():
    DB_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def _column_exists(connection, table, column):
    cursor = connection.cursor()
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    return column in columns


def init_db():
    with _connect() as connection:
        cursor = connection.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS quizzes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            questions_json TEXT NOT NULL,
            source_name TEXT,
            metadata_json TEXT DEFAULT '{}',
            created_at TEXT NOT NULL
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_name TEXT NOT NULL,
            score INTEGER NOT NULL,
            total INTEGER NOT NULL,
            percentage REAL NOT NULL,
            details_json TEXT DEFAULT '[]',
            difficulty_breakdown_json TEXT DEFAULT '{}',
            submitted_at TEXT NOT NULL
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            mobile TEXT,
            created_at TEXT NOT NULL
        )
        """)

        # Add mobile column if it doesn't exist (for existing databases)
        if not _column_exists(connection, "users", "mobile"):
            cursor.execute("ALTER TABLE users ADD COLUMN mobile TEXT")

        connection.commit()


def _hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def register_user(username, password, mobile=None):
    cleaned = (username or "").strip()

    with _connect() as connection:
        cursor = connection.cursor()

        cursor.execute("SELECT id FROM users WHERE LOWER(username) = LOWER(?)", (cleaned,))
        if cursor.fetchone():
            return False, "Username already exists."

        cursor.execute(
            "INSERT INTO users (username, password_hash, mobile, created_at) VALUES (?, ?, ?, ?)",
            (cleaned, _hash_password(password), mobile, datetime.utcnow().isoformat()),
        )

        connection.commit()

    return True, "Registration successful."


def authenticate_user(username, password):
    cleaned = (username or "").strip()

    with _connect() as connection:
        cursor = connection.cursor()

        cursor.execute(
            "SELECT username, password_hash FROM users WHERE LOWER(username) = LOWER(?)",
            (cleaned,),
        )

        row = cursor.fetchone()

        if not row:
            return False, None

        if row["password_hash"] != _hash_password(password):
            return False, None

        return True, row["username"]






def save_questions(questions, source_name="Uploaded File", metadata=None):
    metadata = metadata or {}

    with _connect() as connection:
        cursor = connection.cursor()

        cursor.execute(
            "INSERT INTO quizzes (questions_json, source_name, metadata_json, created_at) VALUES (?, ?, ?, ?)",
            (json.dumps(questions), source_name, json.dumps(metadata), datetime.utcnow().isoformat()),
        )

        connection.commit()
        return cursor.lastrowid


def load_questions():
    with _connect() as connection:
        cursor = connection.cursor()

        cursor.execute("""
        SELECT questions_json, source_name, metadata_json, created_at
        FROM quizzes
        ORDER BY id DESC
        LIMIT 1
        """)

        row = cursor.fetchone()

        if not row:
            return {"questions": [], "metadata": {}, "source_name": None}

        return {
            "questions": json.loads(row["questions_json"]),
            "metadata": json.loads(row["metadata_json"] or "{}"),
            "source_name": row["source_name"],
            "created_at": row["created_at"],
        }


def save_attempt(score, total, user_name="Guest", details=None, difficulty_breakdown=None):
    percentage = (score / total * 100) if total else 0.0

    with _connect() as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO attempts (user_name, score, total, percentage, details_json, difficulty_breakdown_json, submitted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_name,
                score,
                total,
                percentage,
                json.dumps(details or []),
                json.dumps(difficulty_breakdown or {}),
                datetime.utcnow().isoformat(),
            ),
        )

        connection.commit()
        return cursor.lastrowid


def load_attempts(limit=20, user_name=None):
    with _connect() as connection:
        cursor = connection.cursor()

        query = "SELECT user_name, score, total, percentage, details_json, difficulty_breakdown_json, submitted_at FROM attempts"
        params = []
        if user_name:
            query += " WHERE user_name = ?"
            params.append(user_name)
        
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, tuple(params))

        rows = cursor.fetchall()

    percentages = [row["percentage"] for row in rows]

    recent = []
    for row in rows:
        item = dict(row)
        item["details"] = json.loads(item.get("details_json") or "[]")
        item["difficulty_breakdown"] = json.loads(item.get("difficulty_breakdown_json") or "{}")
        recent.append(item)

    return {
        "tests_taken": len(rows),
        "percentages": list(reversed(percentages)),
        "recent": recent,
    }