"""Product API behavior tests."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    settings = Settings(
        database_path=tmp_path / "products.db",
        log_level="CRITICAL",
    )
    with TestClient(create_app(settings)) as test_client:
        yield test_client


@pytest.fixture
def product_payload() -> dict[str, object]:
    return {
        "title": "Wireless Headphones",
        "price": 79.99,
        "description": "Noise-isolating Bluetooth headphones",
        "category": "electronics",
        "image": "https://example.com/headphones.jpg",
        "rating": {"rate": 4.5, "count": 120},
    }


def test_product_crud(client: TestClient, product_payload: dict[str, object]) -> None:
    created = client.post("/api/v1/products", json=product_payload)
    assert created.status_code == 201
    product_id = created.json()["id"]

    retrieved = client.get(f"/api/v1/products/{product_id}")
    assert retrieved.status_code == 200
    assert retrieved.json()["title"] == "Wireless Headphones"

    updated_payload = {
        **product_payload,
        "title": "Updated Headphones",
        "price": 69.99,
    }
    updated = client.put(f"/api/v1/products/{product_id}", json=updated_payload)
    assert updated.status_code == 200
    assert updated.json()["title"] == "Updated Headphones"

    deleted = client.delete(f"/api/v1/products/{product_id}")
    assert deleted.status_code == 200
    assert deleted.json() == {"message": "Product deleted successfully"}
    assert client.get(f"/api/v1/products/{product_id}").status_code == 404


def test_list_filters_sorts_and_paginates(
    client: TestClient, product_payload: dict[str, object]
) -> None:
    first = client.post("/api/v1/products", json=product_payload)
    second_payload = {
        **product_payload,
        "title": "USB Cable",
        "price": 12.5,
        "category": "Accessories",
        "rating": {"rate": 4.0, "count": 20},
    }
    second = client.post("/api/v1/products", json=second_payload)
    assert first.status_code == second.status_code == 201

    response = client.get(
        "/api/v1/products",
        params={
            "category": "ELECTRONICS",
            "min_price": 50,
            "max_price": 100,
            "sort_by": "price",
            "order": "desc",
            "limit": 1,
            "offset": 0,
        },
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["title"] == "Wireless Headphones"


def test_rejects_inverted_price_range(client: TestClient) -> None:
    response = client.get(
        "/api/v1/products", params={"min_price": 100, "max_price": 10}
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "min_price must be less than or equal to max_price"
    )


def test_update_and_delete_missing_product(
    client: TestClient, product_payload: dict[str, object]
) -> None:
    assert client.put("/api/v1/products/999", json=product_payload).status_code == 404
    assert client.delete("/api/v1/products/999").status_code == 404


def test_rejects_invalid_image_url(
    client: TestClient, product_payload: dict[str, object]
) -> None:
    product_payload["image"] = "relative/image.jpg"

    response = client.post("/api/v1/products", json=product_payload)

    assert response.status_code == 422
