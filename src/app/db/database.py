"""SQLite connection and schema lifecycle."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL CHECK (length(trim(title)) BETWEEN 1 AND 300),
    price REAL NOT NULL CHECK (price > 0),
    description TEXT NOT NULL CHECK (length(trim(description)) BETWEEN 1 AND 10000),
    category TEXT NOT NULL CHECK (length(trim(category)) BETWEEN 1 AND 100),
    image TEXT NOT NULL CHECK (length(image) <= 2048),
    rating_rate REAL NOT NULL CHECK (rating_rate >= 0 AND rating_rate <= 5),
    rating_count INTEGER NOT NULL CHECK (rating_count >= 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_products_price ON products(price);
CREATE INDEX IF NOT EXISTS idx_products_title ON products(title COLLATE NOCASE);
"""


class Database:
    """Own database setup and per-operation SQLite connections."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def initialize(self) -> None:
        """Create the parent directory and initialize the schema atomically."""
        if str(self.path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as connection:
            connection.executescript(_SCHEMA)

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        """Yield a configured connection and close it reliably."""
        connection = sqlite3.connect(
            str(self.path),
            timeout=5.0,
            check_same_thread=False,
            uri=str(self.path).startswith("file:"),
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        if str(self.path) != ":memory:" and "mode=memory" not in str(self.path):
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute("PRAGMA synchronous = NORMAL")
        try:
            yield connection
        finally:
            connection.close()
