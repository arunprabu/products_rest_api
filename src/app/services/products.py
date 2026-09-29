"""Product use cases."""

from app.models.product import Product
from app.repositories.products import ProductRepository, SortField
from app.schemas.product import ProductCreate, ProductUpdate


class ProductService:
    """Business logic for product catalog operations."""

    def __init__(self, repository: ProductRepository) -> None:
        self._repository = repository

    def create(self, product: ProductCreate) -> Product:
        return self._repository.create(product)

    def get(self, product_id: int) -> Product | None:
        return self._repository.get(product_id)

    def update(self, product_id: int, product: ProductUpdate) -> Product | None:
        return self._repository.update(product_id, product)

    def delete(self, product_id: int) -> bool:
        return self._repository.delete(product_id)

    def list(
        self,
        *,
        limit: int,
        offset: int,
        category: str | None,
        min_price: float | None,
        max_price: float | None,
        sort_by: SortField,
        order: str,
    ) -> tuple[list[Product], int]:
        return self._repository.list(
            limit=limit,
            offset=offset,
            category=category,
            min_price=min_price,
            max_price=max_price,
            sort_by=sort_by,
            order=order,  # type: ignore[arg-type]
        )
