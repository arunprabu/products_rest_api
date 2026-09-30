"""Browser-based end-to-end tests for the product catalog API."""

from __future__ import annotations

import re
from typing import TypedDict, cast

import pytest
from playwright.sync_api import APIResponse, Page, Response, expect

pytestmark = pytest.mark.e2e

PRODUCTS_PATH = "/api/v1/products"


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


def _create_product(page: Page, payload: ProductPayload) -> int:
    response = page.request.post(PRODUCTS_PATH, data=payload)
    assert response.status == 201
    body = cast(dict[str, object], response.json())
    product_id = body["id"]
    assert isinstance(product_id, int)
    return product_id


def _goto(page: Page, url: str) -> Response:
    response = page.goto(url)
    assert response is not None
    return response


def test_swagger_ui_loads(page: Page) -> None:
    response = _goto(page, "/docs")

    assert response.status == 200
    expect(page).to_have_title(re.compile("Products REST API"))
    expect(page.locator(".swagger-ui")).to_be_visible()


def test_openapi_schema_exposes_product_routes(page: Page) -> None:
    response = _goto(page, "/openapi.json")

    assert response.status == 200
    schema = cast(dict[str, object], response.json())
    paths = cast(dict[str, object], schema["paths"])
    assert PRODUCTS_PATH in paths
    assert f"{PRODUCTS_PATH}/{{product_id}}" in paths


def test_created_product_is_retrievable_in_browser(page: Page) -> None:
    payload = _product_payload(
        title="Wireless Headphones",
        price=79.99,
        category="electronics",
        rate=4.5,
    )
    product_id = _create_product(page, payload)

    response = _goto(page, f"{PRODUCTS_PATH}/{product_id}")

    assert response.status == 200
    body = cast(dict[str, object], response.json())
    assert body["id"] == product_id
    assert body["title"] == payload["title"]
    expect(page.locator("body")).to_contain_text(payload["title"])


def test_product_list_renders_json_in_browser(page: Page) -> None:
    payload = _product_payload(
        title="Mechanical Keyboard",
        price=129.5,
        category="electronics",
        rate=4.8,
    )
    _create_product(page, payload)

    response = _goto(page, f"{PRODUCTS_PATH}?category=electronics")

    assert response.status == 200
    body = cast(dict[str, object], response.json())
    items = cast(list[dict[str, object]], body["items"])
    assert any(item["title"] == payload["title"] for item in items)
    expect(page.locator("body")).to_contain_text(payload["title"])


def test_missing_product_returns_not_found(page: Page) -> None:
    response = _goto(page, f"{PRODUCTS_PATH}/999999")

    assert response.status == 404
    body = cast(dict[str, object], response.json())
    assert body["detail"] == "Product not found"


def test_invalid_product_payload_is_rejected(page: Page) -> None:
    payload = _product_payload(
        title="Broken Product",
        price=10.0,
        category="electronics",
        rate=4.0,
    )
    payload["price"] = 0

    response: APIResponse = page.request.post(PRODUCTS_PATH, data=payload)

    assert response.status == 422
