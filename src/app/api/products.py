"""Product catalog endpoints."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_product_service
from app.models.product import Product
from app.repositories.products import SortField
from app.schemas.product import (
    MessageResponse,
    ProductCreate,
    ProductListResponse,
    ProductResponse,
    ProductUpdate,
    RatingResponse,
)
from app.services.products import ProductService

router = APIRouter(prefix="/products", tags=["products"])
ServiceDependency = Annotated[ProductService, Depends(get_product_service)]


def _response(product: Product) -> ProductResponse:
    """Map a domain product to the nested public representation."""
    return ProductResponse(
        id=product.id,
        title=product.title,
        price=product.price,
        description=product.description,
        category=product.category,
        image=product.image,
        rating=RatingResponse(
            rate=product.rating.rate,
            count=product.rating.count,
        ),
    )


# localhost:8000/api/v1/products - POST
@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    product: ProductCreate, service: ServiceDependency
) -> ProductResponse:
    """Create a product."""
    return _response(service.create(product))


# localhost:8000/api/v1/products - GET
@router.get("", response_model=ProductListResponse)
def list_products(
    service: ServiceDependency,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    category: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    min_price: Annotated[float | None, Query(ge=0)] = None,
    max_price: Annotated[float | None, Query(ge=0)] = None,
    sort_by: Annotated[SortField, Query()] = "id",
    order: Literal["asc", "desc"] = "asc",
) -> ProductListResponse:
    """List/filter/sort products with bounded offset pagination."""
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="min_price must be less than or equal to max_price",
        )
    products, total = service.list(
        limit=limit,
        offset=offset,
        category=category,
        min_price=min_price,
        max_price=max_price,
        sort_by=sort_by,
        order=order,
    )
    return ProductListResponse(
        items=[_response(product) for product in products],
        total=total,
        limit=limit,
        offset=offset,
    )


# localhost:8000/api/v1/products/{product_id} - GET
@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, service: ServiceDependency) -> ProductResponse:
    """Retrieve one product by ID."""
    product = service.get(product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )
    return _response(product)


# localhost:8000/api/v1/products/{product_id} - PUT
@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int, product: ProductUpdate, service: ServiceDependency
) -> ProductResponse:
    """Replace a product's mutable fields."""
    updated = service.update(product_id, product)
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )
    return _response(updated)


# localhost:8000/api/v1/products/{product_id} - DELETE
@router.delete("/{product_id}", response_model=MessageResponse)
def delete_product(product_id: int, service: ServiceDependency) -> MessageResponse:
    """Delete a product."""
    if not service.delete(product_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )
    return MessageResponse(message="Product deleted successfully")
