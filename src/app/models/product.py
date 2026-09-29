"""Domain model for products."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Rating:
    """Aggregate customer rating."""

    rate: float
    count: int


@dataclass(frozen=True, slots=True)
class Product:
    """Persisted product representation."""

    id: int
    title: str
    price: float
    description: str
    category: str
    image: str
    rating: Rating
