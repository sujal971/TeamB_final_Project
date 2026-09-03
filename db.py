"""Database connection helpers.

This module provides lightweight helpers for connecting to a MySQL database using
mysql-connector-python. It is used by `utils/storage.py` to persist quizzes, users,
and attempts.

Configuration is done via environment variables (see README.md):
- MYSQL_HOST (default: localhost)
- MYSQL_PORT (default: 3306)
- MYSQL_USER (default: root)
- MYSQL_PASSWORD (default: "")
- MYSQL_DATABASE (default: smartquizz)
"""

import os
import mysql.connector
from mysql.connector import errorcode

def _get_config():
    return {
        "host": os.getenv("MYSQL_HOST", "localhost"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER", "shiva"),
        "password": os.getenv("MYSQL_PASSWORD", "K.shiva@3813"),
        "database": os.getenv("MYSQL_DATABASE", "smartquizz"),
        "charset": "utf8mb4",
        "use_unicode": True,
    }

def ensure_database():
    """Ensure the configured database exists.
    This will connect to the server (without selecting a database) and create the
    configured database if it does not already exist.
    """

    cfg = _get_config()
    # Connect without specifying a database (some servers require this when the
    # database doesn't exist yet).
    try:
        conn = mysql.connector.connect(
            host=cfg["host"],
            port=cfg["port"],
            user=cfg["user"],
            password=cfg["password"],
        )

    except mysql.connector.Error as exc:
        msg = (
            "Unable to connect to MySQL while ensuring the database exists. "
            "Please ensure MySQL is running and the connection environment variables are set. "
            f"(host={cfg['host']} port={cfg['user']} db={cfg['database']}) "
        )

        if getattr(exc, 'errno', None) == errorcode.ER_ACCESS_DENIED_ERROR:
            msg += (
                "Access denied indicates the provided username/password is invalid. "
                "Set MYSQL_USER and MYSQL_PASSWORD environment variables to the correct values. "
                )
        raise RuntimeError(f"{msg}Underlying error: {exc}") from exc
    try:
        cursor = conn.cursor()
        cursor.execute(
            "CREATE DATABASE IF NOT EXISTS `{}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci".format(
                cfg["database"]
            )
        )
    finally:
        cursor.close()
        conn.close()
def get_connection():
    """Return a new connection to the configured MySQL database."""
    cfg = _get_config()
    try:
        return mysql.connector.connect(**cfg)
    except mysql.connector.Error as exc:
        # Provide a helpful error message when connection fails.
        raise RuntimeError(
            "Unable to connect to MySQL. "
            "Please ensure MySQL is running and the connection environment variables are set. "
            f"(host={cfg['host']} port={cfg['user']} db={cfg['database']}) "
            f"Underlying error: {exc}"
        ) from exc 
