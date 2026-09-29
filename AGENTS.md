# AGENTS.md

## Project overview

Product catalog REST API built with Python 3.12+, FastAPI, and SQLite, using a `src` layout. Layers are separated: HTTP routing, business logic, persistence, schemas, configuration, and domain models.

## Setup

```shell
uv sync --dev
```

`uv run` executes commands inside `.venv` automatically; no manual activation needed.

## Commands

Run the API locally:

```shell
uv run uvicorn app.main:app --app-dir src --host localhost --port 8000 --reload
```

Run tests (with coverage, must pass before finishing any change):

```shell
uv run pytest
```

Lint and format-check:

```shell
uv run ruff check src tests
uv run ruff format --check src tests
```

Apply formatting:

```shell
uv run ruff format src tests
```

Strict type checking:

```shell
uv run mypy src tests
```

Always run `pytest`, `ruff check`, `ruff format --check`, and `mypy` after modifying code.

## Project structure

```text
src/app/
├── api/           # FastAPI routes and dependencies
├── core/          # Configuration, errors, and logging
├── db/            # SQLite connection and schema lifecycle
├── models/        # Domain models
├── repositories/  # Persistence operations
├── schemas/       # Request and response schemas
└── services/      # Business logic
```

## API

Base URL: `http://localhost:8000/api/v1` (Swagger UI at `/docs`, OpenAPI at `/openapi.json`).

| Method   | Path                            | Description        |
| -------- | ------------------------------- | ------------------ |
| `POST`   | `/api/v1/products`              | Create a product (201) |
| `GET`    | `/api/v1/products`              | List products      |
| `GET`    | `/api/v1/products/{product_id}` | Retrieve a product |
| `PUT`    | `/api/v1/products/{product_id}` | Replace a product  |
| `DELETE` | `/api/v1/products/{product_id}` | Delete a product; returns `{"message": "Product deleted successfully"}` |

`GET /api/v1/products` query parameters: `limit` (1-100, default 20), `offset` (>=0), `category`, `min_price`, `max_price` (`min_price` must not exceed `max_price`), `sort_by` (`id`, `title`, `price`, `category`, `rating`), `order` (`asc`/`desc`).

## Validation rules

- `title`, `description`, and `category` must not be empty.
- `price` must be greater than zero.
- `image` may be empty or an absolute HTTP(S) URL.
- `rating.rate` must be between `0` and `5`; `rating.count` must be a non-negative integer.
- Unknown request fields are rejected (`extra="forbid"`).

## Configuration

Environment variables (see `.env.example`):

| Variable        | Default              | Description                      |
| --------------- | -------------------- | -------------------------------- |
| `DATABASE_PATH` | `./data/products.db` | Path to the SQLite database file |
| `LOG_LEVEL`     | `INFO`               | Application logging level        |

## Conventions

- Persistence uses parameterized SQL with explicit transactions.
- Sorting is allow-listed via the `SortField` type; never interpolate user input into SQL.
- Follow existing layer boundaries: routes call services, services call repositories.
- Do not add comments unless necessary; match existing docstring style.
