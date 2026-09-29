"""Parameterized SQL operations for products."""

from __future__ import annotations

import sqlite3
from typing import Literal

from app.models.product import Product, Rating
from app.schemas.product import ProductCreate, ProductUpdate

SortField = Literal["id", "title", "price", "category", "rating"]
_SORT_COLUMNS: dict[SortField, str] = {
    "id": "id",
    "title": "title COLLATE NOCASE",
    "price": "price",
    "category": "category COLLATE NOCASE",
    "rating": "rating_rate",
}


class ProductRepository:
    """Encapsulates persistence queries; each write owns a transaction."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def create(self, product: ProductCreate) -> Product:
        """Insert a product and return the stored representation."""
        data = product.model_dump()
        rating = data.pop("rating")
        with self._connection:
            cursor = self._connection.execute(
                """INSERT INTO products
                (title, price, description, category, image, rating_rate, rating_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    data["title"],
                    data["price"],
                    data["description"],
                    data["category"],
                    data["image"],
                    rating["rate"],
                    rating["count"],
                ),
            )
        product_id = cursor.lastrowid
        if product_id is None:
            raise RuntimeError("SQLite did not return an inserted product ID")
        created = self.get(product_id)
        if created is None:
            raise RuntimeError("Inserted product could not be retrieved")
        return created

    def get(self, product_id: int) -> Product | None:
        """Return a product by its identifier."""
        row = self._connection.execute(
            "SELECT * FROM products WHERE id = ?", (product_id,)
        ).fetchone()
        return self._to_product(row) if row is not None else None

    def update(self, product_id: int, product: ProductUpdate) -> Product | None:
        """Replace all mutable product properties."""
        data = product.model_dump()
        rating = data.pop("rating")
        with self._connection:
            cursor = self._connection.execute(
                """UPDATE products SET title = ?, price = ?, description = ?,
                category = ?, image = ?, rating_rate = ?, rating_count = ?,
                updated_at = CURRENT_TIMESTAMP WHERE id = ?""",
                (
                    data["title"],
                    data["price"],
                    data["description"],
                    data["category"],
                    data["image"],
                    rating["rate"],
                    rating["count"],
                    product_id,
                ),
            )
        return self.get(product_id) if cursor.rowcount else None

    def delete(self, product_id: int) -> bool:
        """Delete a product; return whether one existed."""
        with self._connection:
            cursor = self._connection.execute(
                "DELETE FROM products WHERE id = ?", (product_id,)
            )
        return cursor.rowcount > 0

    def list(
        self,
        *,
        limit: int,
        offset: int,
        category: str | None,
        min_price: float | None,
        max_price: float | None,
        sort_by: SortField,
        order: Literal["asc", "desc"],
    ) -> tuple[list[Product], int]:
        """List products with parameterized filters and allow-listed ordering."""
        conditions: list[str] = []
        parameters: list[str | int | float] = []
        if category is not None:
            conditions.append("category = ? COLLATE NOCASE")
            parameters.append(category)
        if min_price is not None:
            conditions.append("price >= ?")
            parameters.append(min_price)
        if max_price is not None:
            conditions.append("price <= ?")
            parameters.append(max_price)
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        total_row = self._connection.execute(
            f"SELECT COUNT(*) AS total FROM products {where_clause}", parameters
        ).fetchone()
        total = int(total_row["total"])
        column = _SORT_COLUMNS[sort_by]
        direction = order.upper()
        rows = self._connection.execute(
            f"SELECT * FROM products {where_clause} "
            f"ORDER BY {column} {direction}, id ASC LIMIT ? OFFSET ?",
            [*parameters, limit, offset],
        ).fetchall()
        return [self._to_product(row) for row in rows], total

    @staticmethod
    def _to_product(row: sqlite3.Row) -> Product:
        return Product(
            id=int(row["id"]),
            title=str(row["title"]),
            price=float(row["price"]),
            description=str(row["description"]),
            category=str(row["category"]),
            image=str(row["image"]),
            rating=Rating(
                rate=float(row["rating_rate"]), count=int(row["rating_count"])
            ),
        )
