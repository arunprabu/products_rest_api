"""FastAPI dependency providers."""

from collections.abc import Iterator

from fastapi import Request

from app.repositories.products import ProductRepository
from app.services.products import ProductService


def get_product_service(request: Request) -> Iterator[ProductService]:
    """Provide a service backed by a request-scoped SQLite connection."""
    database = request.app.state.database
    with database.connection() as connection:
        yield ProductService(ProductRepository(connection))
