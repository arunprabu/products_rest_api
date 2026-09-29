"""Application startup and routing tests."""

from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_application_starts_and_serves_product_routes(tmp_path: Path) -> None:
    settings = Settings(
        database_path=tmp_path / "products.db",
        log_level="CRITICAL",
    )

    with TestClient(create_app(settings)) as client:
        response = client.get("/api/v1/products")

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "total": 0,
        "limit": 20,
        "offset": 0,
    }


def test_openapi_document_includes_product_routes(tmp_path: Path) -> None:
    settings = Settings(
        database_path=tmp_path / "products.db",
        log_level="CRITICAL",
    )

    with TestClient(create_app(settings)) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/api/v1/products" in response.json()["paths"]
