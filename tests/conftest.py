"""Shared fixtures for in-process API tests."""

from collections.abc import Iterator
from pathlib import Path
from typing import TypedDict

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


class RatingPayload(TypedDict):
    """JSON-compatible rating request payload."""

    rate: float
    count: int


class ProductPayload(TypedDict):
    """JSON-compatible product request payload."""

    title: str
    price: float
    description: str
    category: str
    image: str
    rating: RatingPayload


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    """Serve the FastAPI app in-process with an isolated SQLite database."""
    settings = Settings(
        database_path=tmp_path / "products.db",
        log_level="CRITICAL",
    )
    with TestClient(create_app(settings)) as test_client:
        yield test_client


@pytest.fixture
def product_payload() -> ProductPayload:
    """Return a valid product write payload."""
    return {
        "title": "Wireless Headphones",
        "price": 79.99,
        "description": "Noise-isolating Bluetooth headphones",
        "category": "electronics",
        "image": "https://example.com/headphones.jpg",
        "rating": {"rate": 4.5, "count": 120},
    }
