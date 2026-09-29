# Products REST API

A production-minded product catalog REST API built with Python 3.12+, FastAPI, and SQLite. The project uses a `src` layout and separates HTTP routing, business logic, persistence, schemas, configuration, and domain models.

## Features

- Create, retrieve, replace, list, and delete products
- Request and response validation with Pydantic
- SQLite persistence with parameterized SQL and explicit transactions
- Pagination, filtering, and allow-listed sorting
- Nested product ratings
- OpenAPI and Swagger UI through FastAPI
- Ruff linting and formatting, strict mypy type checking, and pytest coverage

## Requirements

- Python 3.12 or later
- [`uv`](https://docs.astral.sh/uv/) (recommended), or another Python package manager

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

## Setup

Install the project and development dependencies:

```shell
uv sync --dev
```

This creates a virtual environment in `.venv`. Activate it before running
commands directly inside the environment.

### Activate the virtual environment

On macOS or Linux (`bash`/`zsh`):

```shell
source .venv/bin/activate
```

On Windows Command Prompt:

```bat
.venv\Scripts\activate.bat
```

On Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

To leave the virtual environment on any platform, run:

```shell
deactivate
```

Activation is optional when using `uv run`, because `uv` automatically runs
the command in the project's virtual environment.

Runtime configuration is read from environment variables. The defaults are suitable for local development; see `.env.example` for the available settings.

| Variable        | Default              | Description                      |
| --------------- | -------------------- | -------------------------------- |
| `DATABASE_PATH` | `./data/products.db` | Path to the SQLite database file |
| `LOG_LEVEL`     | `INFO`               | Application logging level        |

## Run locally

```shell
uv run uvicorn app.main:app --app-dir src --host localhost --port 8000 --reload
```

Once running:

- API base URL: `http://localhost:8000/api/v1`
- Swagger UI: `http://localhost:8000/docs`
- OpenAPI schema: `http://localhost:8000/openapi.json`

## API endpoints

| Method   | Path                            | Description        |
| -------- | ------------------------------- | ------------------ |
| `POST`   | `/api/v1/products`              | Create a product   |
| `GET`    | `/api/v1/products`              | List products      |
| `GET`    | `/api/v1/products/{product_id}` | Retrieve a product |
| `PUT`    | `/api/v1/products/{product_id}` | Replace a product  |
| `DELETE` | `/api/v1/products/{product_id}` | Delete a product   |

### Create a product

```shell
curl --request POST 'http://localhost:8000/api/v1/products' \
  --header 'Content-Type: application/json' \
  --data '{
    "title": "Wireless Headphones",
    "price": 79.99,
    "description": "Noise-isolating Bluetooth headphones",
    "category": "electronics",
    "image": "https://example.com/images/headphones.jpg",
    "rating": {
      "rate": 4.5,
      "count": 120
    }
  }'
```

Example response (`201 Created`):

```json
{
  "id": 1,
  "title": "Wireless Headphones",
  "price": 79.99,
  "description": "Noise-isolating Bluetooth headphones",
  "category": "electronics",
  "image": "https://example.com/images/headphones.jpg",
  "rating": {
    "rate": 4.5,
    "count": 120
  }
}
```

The same complete request body is required by `PUT /api/v1/products/{product_id}`.

### List products

`GET /api/v1/products` supports these query parameters:

| Parameter   | Default | Constraints                                            |
| ----------- | ------- | ------------------------------------------------------ |
| `limit`     | `20`    | Integer from 1 through 100                             |
| `offset`    | `0`     | Non-negative integer                                   |
| `category`  | —       | Exact, case-insensitive category match                 |
| `min_price` | —       | Non-negative number                                    |
| `max_price` | —       | Non-negative number; must not be less than `min_price` |
| `sort_by`   | `id`    | `id`, `title`, `price`, `category`, or `rating`        |
| `order`     | `asc`   | `asc` or `desc`                                        |

Example:

```shell
curl 'http://localhost:8000/api/v1/products?category=electronics&min_price=25&sort_by=price&order=desc&limit=10'
```

## Validation rules

- `title`, `description`, and `category` must not be empty.
- `price` must be greater than zero.
- `image` may be empty or an absolute HTTP(S) URL.
- `rating.rate` must be between `0` and `5`.
- `rating.count` must be a non-negative integer.
- Unknown request fields are rejected.

## Development checks

Install the Chromium browser used by Playwright after syncing dependencies:

```shell
uv run playwright install chromium
```

Run the complete test suite with coverage:

```shell
uv run pytest
```

Pytest discovers tests under `tests/`, adds `src/` to the import path, and
writes HTML coverage output to `htmlcov/`. Browser tests use Chromium by
default and retain traces and screenshots when a test fails. The configured
Playwright base URL is `http://localhost:8000`; start the API before running
browser-based tests.

Run only API or browser tests using the configured markers:

```shell
uv run pytest -m api
uv run pytest -m e2e
```

Lint and format-check the project:

```shell
uv run ruff check src tests
uv run ruff format --check src tests
```

Run strict type checking:

```shell
uv run mypy src tests
```

Apply Ruff formatting:

```shell
uv run ruff format src tests
```
