"""Failure-path tests for persistence and HTTP error handling."""

import sqlite3
from pathlib import Path
from typing import cast

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.errors import PersistenceError
from app.db.database import Database
from app.repositories.products import ProductRepository
from app.schemas.product import ProductCreate


def _product() -> ProductCreate:
    return ProductCreate(
        title="Test product",
        price=10,
        description="Test description",
        category="test",
        image="",
        rating={"rate": 4, "count": 1},
    )


def test_create_rolls_back_when_inserted_product_cannot_be_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database = Database(tmp_path / "products.db")
    database.initialize()
    with database.connection() as connection:
        repository = ProductRepository(connection)
        monkeypatch.setattr(repository, "get", lambda product_id: None)

        with pytest.raises(PersistenceError) as exc_info:
            repository.create(_product())

        assert isinstance(exc_info.value.__cause__, RuntimeError)
        count = connection.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        assert count == 0


def test_repository_chains_sqlite_errors(tmp_path: Path) -> None:
    database = Database(tmp_path / "products.db")
    database.initialize()
    with database.connection() as connection:
        repository = ProductRepository(connection)
        connection.execute("DROP TABLE products")

        with pytest.raises(PersistenceError) as exc_info:
            repository.get(1)

        assert isinstance(exc_info.value.__cause__, sqlite3.Error)


def test_persistence_error_returns_correlated_problem_response(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_create(self: ProductRepository, product: ProductCreate) -> None:
        raise PersistenceError("Product database operation failed")

    monkeypatch.setattr(ProductRepository, "create", fail_create)

    response = client.post(
        "/api/v1/products",
        headers={"X-Request-ID": "test-request-id"},
        json=_product().model_dump(),
    )

    assert response.status_code == 503
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.headers["x-request-id"] == "test-request-id"
    body = cast(dict[str, object], response.json())
    assert body == {
        "type": "about:blank",
        "title": "Service Unavailable",
        "status": 503,
        "detail": "Product database operation failed",
        "instance": "/api/v1/products",
        "request_id": "test-request-id",
    }


@pytest.mark.parametrize("product_id", [0, -1])
def test_product_id_must_be_positive(client: TestClient, product_id: int) -> None:
    response = client.get(f"/api/v1/products/{product_id}")

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")


def test_whitespace_category_is_rejected(client: TestClient) -> None:
    response = client.get("/api/v1/products", params={"category": "   "})

    assert response.status_code == 422


def test_incomplete_absolute_image_url_is_rejected(
    client: TestClient, product_payload: dict[str, object]
) -> None:
    product_payload["image"] = "http://"

    response = client.post("/api/v1/products", json=product_payload)

    assert response.status_code == 422


@pytest.mark.parametrize(
    "settings",
    [
        Settings(database_path=Path("products.db"), log_level="INVALID"),
        Settings(database_path=Path(""), log_level="INFO"),
        Settings(database_path=Path("products.db"), log_level="INFO", api_prefix="api"),
    ],
)
def test_settings_reject_invalid_values(settings: Settings) -> None:
    pytest.fail(f"Settings unexpectedly accepted: {settings}")
