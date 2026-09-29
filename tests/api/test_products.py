"""In-process tests for the product API endpoints."""

from copy import deepcopy
from typing import TypedDict, cast

import pytest
from fastapi.testclient import TestClient


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


pytestmark = pytest.mark.api
PRODUCTS_URL = "/api/v1/products"


def _create_product(client: TestClient, payload: ProductPayload) -> int:
    response = client.post(PRODUCTS_URL, json=payload)
    assert response.status_code == 201
    body = cast(dict[str, object], response.json())
    product_id = body["id"]
    assert isinstance(product_id, int)
    return product_id


def _product_payload(
    *,
    title: str,
    price: float,
    category: str,
    rate: float,
) -> ProductPayload:
    return {
        "title": title,
        "price": price,
        "description": f"Description for {title}",
        "category": category,
        "image": "",
        "rating": {"rate": rate, "count": 10},
    }


def test_create_product_returns_created_product(
    client: TestClient, product_payload: ProductPayload
) -> None:
    response = client.post(PRODUCTS_URL, json=product_payload)

    assert response.status_code == 201
    assert response.json() == {"id": 1, **product_payload}


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        pytest.param("title", "   ", id="blank-title"),
        pytest.param("price", 0, id="non-positive-price"),
        pytest.param("description", "   ", id="blank-description"),
        pytest.param("category", "   ", id="blank-category"),
        pytest.param("image", "images/product.jpg", id="relative-image"),
    ],
)
def test_create_product_rejects_invalid_product_fields(
    client: TestClient,
    product_payload: ProductPayload,
    field: str,
    invalid_value: object,
) -> None:
    payload = cast(dict[str, object], deepcopy(product_payload))
    payload[field] = invalid_value

    response = client.post(PRODUCTS_URL, json=payload)

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        pytest.param("rate", -0.1, id="rate-below-zero"),
        pytest.param("rate", 5.1, id="rate-above-five"),
        pytest.param("count", -1, id="negative-count"),
    ],
)
def test_create_product_rejects_invalid_rating_fields(
    client: TestClient,
    product_payload: ProductPayload,
    field: str,
    invalid_value: object,
) -> None:
    payload = cast(dict[str, object], deepcopy(product_payload))
    rating = cast(dict[str, object], payload["rating"])
    rating[field] = invalid_value

    response = client.post(PRODUCTS_URL, json=payload)

    assert response.status_code == 422


@pytest.mark.parametrize("location", ["product", "rating"])
def test_create_product_rejects_unknown_fields(
    client: TestClient,
    product_payload: ProductPayload,
    location: str,
) -> None:
    payload = cast(dict[str, object], deepcopy(product_payload))
    if location == "product":
        payload["unknown"] = True
    else:
        rating = cast(dict[str, object], payload["rating"])
        rating["unknown"] = True

    response = client.post(PRODUCTS_URL, json=payload)

    assert response.status_code == 422


def test_list_products_returns_default_empty_page(client: TestClient) -> None:
    response = client.get(PRODUCTS_URL)

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "total": 0,
        "limit": 20,
        "offset": 0,
    }


def _seed_products(client: TestClient) -> list[ProductPayload]:
    products = [
        _product_payload(
            title="Wireless Headphones",
            price=79.99,
            category="electronics",
            rate=4.5,
        ),
        _product_payload(
            title="USB Cable",
            price=12.5,
            category="accessories",
            rate=4.0,
        ),
        _product_payload(
            title="Wall Charger",
            price=35.0,
            category="Electronics",
            rate=3.8,
        ),
        _product_payload(
            title="Monitor",
            price=249.0,
            category="electronics",
            rate=4.8,
        ),
    ]
    for payload in products:
        _create_product(client, payload)
    return products


def test_list_products_filters_category_case_insensitively(
    client: TestClient,
) -> None:
    products = _seed_products(client)

    response = client.get(PRODUCTS_URL, params={"category": "ELECTRONICS"})

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {"id": 1, **products[0]},
            {"id": 3, **products[2]},
            {"id": 4, **products[3]},
        ],
        "total": 3,
        "limit": 20,
        "offset": 0,
    }


def test_list_products_filters_by_price_range(client: TestClient) -> None:
    products = _seed_products(client)

    response = client.get(
        PRODUCTS_URL,
        params={"min_price": 30, "max_price": 100},
    )

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {"id": 1, **products[0]},
            {"id": 3, **products[2]},
        ],
        "total": 2,
        "limit": 20,
        "offset": 0,
    }


def test_list_products_sorts_by_price_descending(client: TestClient) -> None:
    products = _seed_products(client)

    response = client.get(
        PRODUCTS_URL,
        params={
            "sort_by": "price",
            "order": "desc",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {"id": 4, **products[3]},
            {"id": 1, **products[0]},
            {"id": 3, **products[2]},
            {"id": 2, **products[1]},
        ],
        "total": 4,
        "limit": 20,
        "offset": 0,
    }


def test_list_products_paginates_and_preserves_total(client: TestClient) -> None:
    products = _seed_products(client)

    response = client.get(
        PRODUCTS_URL,
        params={"limit": 1, "offset": 1},
    )

    assert response.status_code == 200
    assert response.json() == {
        "items": [{"id": 2, **products[1]}],
        "total": 4,
        "limit": 1,
        "offset": 1,
    }


@pytest.mark.parametrize(
    "params",
    [
        pytest.param({"limit": 0}, id="limit-below-minimum"),
        pytest.param({"limit": 101}, id="limit-above-maximum"),
        pytest.param({"offset": -1}, id="negative-offset"),
        pytest.param({"category": ""}, id="empty-category"),
        pytest.param({"min_price": -1}, id="negative-min-price"),
        pytest.param({"max_price": -1}, id="negative-max-price"),
        pytest.param({"sort_by": "description"}, id="unsupported-sort-field"),
        pytest.param({"order": "sideways"}, id="unsupported-sort-order"),
    ],
)
def test_list_products_rejects_invalid_query_parameters(
    client: TestClient, params: dict[str, str | int | float | bool | None]
) -> None:
    response = client.get(PRODUCTS_URL, params=params)

    assert response.status_code == 422


def test_list_products_rejects_inverted_price_range(client: TestClient) -> None:
    response = client.get(
        PRODUCTS_URL,
        params={"min_price": 100, "max_price": 10},
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": "min_price must be less than or equal to max_price"
    }


def test_get_product_returns_product(
    client: TestClient, product_payload: ProductPayload
) -> None:
    product_id = _create_product(client, product_payload)

    response = client.get(f"{PRODUCTS_URL}/{product_id}")

    assert response.status_code == 200
    assert response.json() == {"id": product_id, **product_payload}


def test_get_product_returns_not_found(client: TestClient) -> None:
    response = client.get(f"{PRODUCTS_URL}/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Product not found"}


def test_update_product_replaces_product(
    client: TestClient, product_payload: ProductPayload
) -> None:
    product_id = _create_product(client, product_payload)
    updated_payload: ProductPayload = {
        **product_payload,
        "title": "Updated Headphones",
        "price": 69.99,
        "rating": {"rate": 4.9, "count": 150},
    }

    response = client.put(
        f"{PRODUCTS_URL}/{product_id}",
        json=updated_payload,
    )

    assert response.status_code == 200
    assert response.json() == {"id": product_id, **updated_payload}
    assert client.get(f"{PRODUCTS_URL}/{product_id}").json() == {
        "id": product_id,
        **updated_payload,
    }


def test_update_product_requires_full_replacement(
    client: TestClient, product_payload: ProductPayload
) -> None:
    product_id = _create_product(client, product_payload)

    response = client.put(
        f"{PRODUCTS_URL}/{product_id}",
        json={"title": "Only a title"},
    )

    assert response.status_code == 422


def test_update_product_returns_not_found(
    client: TestClient, product_payload: ProductPayload
) -> None:
    response = client.put(f"{PRODUCTS_URL}/999", json=product_payload)

    assert response.status_code == 404
    assert response.json() == {"detail": "Product not found"}


def test_delete_product_removes_product(
    client: TestClient, product_payload: ProductPayload
) -> None:
    product_id = _create_product(client, product_payload)

    response = client.delete(f"{PRODUCTS_URL}/{product_id}")

    assert response.status_code == 200
    assert response.json() == {"message": "Product deleted successfully"}
    assert client.get(f"{PRODUCTS_URL}/{product_id}").status_code == 404


def test_delete_product_returns_not_found(client: TestClient) -> None:
    response = client.delete(f"{PRODUCTS_URL}/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Product not found"}
