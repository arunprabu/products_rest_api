# Products REST API

A production-minded product catalog REST API built with Python 3.12+, FastAPI, and SQLite. The project uses a `src` layout and separates HTTP routing, business logic, persistence, schemas, configuration, and domain models.

Note: Do not assume everything on your own. If the request/prompt/query is ambiguous, ask questions at the user.

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

### Pre-commit hooks

The repository ships a [pre-commit](https://pre-commit.com/) configuration that
runs Ruff formatting and linting on staged Python files. A failing hook aborts
the commit, so lint or format errors cannot be committed.

Enable the hooks once per clone:

```shell
uv run pre-commit install
```

After that, `git commit` automatically runs `ruff format` and `ruff check --fix`
against the staged files. To run the hooks manually against the whole tree:

```shell
uv run pre-commit run --all-files
```

The hooks invoke the project's own Ruff through `uv run`, so local results match
the CI `quality` job exactly.

## Contributing

### Commit messages

This project follows [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/).
Every commit message must use the form:

```text
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

- **type** — one of `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`.
- **scope** (optional) — the affected area, e.g. `api`, `services`, `repositories`, `schemas`, `db`, `core`, `deps`, `ci`.
- **description** — imperative mood, lowercase, no trailing period.

Mark breaking changes with `!` after the type/scope (e.g. `feat(api)!: ...`) and/or a
`BREAKING CHANGE:` footer. Reference issues in the footer (e.g. `Closes: #123`).

Examples:

```text
feat(api): add price range filter to product listing
fix(repositories): escape category before LIKE match
docs: document Conventional Commits workflow
test(services): cover duplicate product creation
chore(deps): bump fastapi to 0.115
```

### Workflow

1. Create a branch for your change (e.g. `feat/price-range-filter`).
2. Make the change and add or update tests.
3. Run the development checks above (`pytest`, `ruff`, `mypy`).
4. Commit using a Conventional Commit message and open a pull request.

## Docker

Build the image:

```shell
docker build -t products-rest-api:local .
```

Run the container (the SQLite database is persisted in a named volume):

```shell
docker run --rm -p 8000:8000 -v products-data:/app/data products-rest-api:local
```

Or use Docker Compose:

```shell
docker compose up --build
```

The image is a multi-stage build that installs runtime dependencies from
`uv.lock` with `uv`, runs as an unprivileged `app` user, and exposes a
`HEALTHCHECK` against `/openapi.json`. Runtime configuration is supplied
through environment variables (`DATABASE_PATH`, `LOG_LEVEL`); mount a volume
at `/app/data` so the database survives container restarts.

## CI/CD

Continuous integration and deployment run on GitHub Actions.

### CI (`.github/workflows/ci.yml`)

Runs on pushes and pull requests targeting `main`, and is reusable via
`workflow_call`:

- **quality** — Ruff format check, Ruff lint, and strict mypy.
- **test** — API tests with coverage (`pytest -m api`), uploading `coverage.xml`.
- **e2e** — Playwright browser tests (`pytest -m e2e`) with Chromium; traces and
  screenshots are uploaded when a test fails.

The `test` and `e2e` jobs run only after `quality` passes.

### CD (`.github/workflows/cd.yml`)

Runs on pushes to `main` (and manually via `workflow_dispatch`):

1. **ci** — reuses the CI workflow so a red commit is never deployed.
2. **build-and-push** — builds the Docker image and pushes it to GitHub
   Container Registry as `ghcr.io/<owner>/<repo>:<sha>` and `:latest`.
3. **deploy** — pulls the image on the target host over SSH and restarts the
   container, gated by the `production` environment.

### Required configuration

Add these repository secrets (Settings → Secrets and variables → Actions):

| Secret           | Purpose                         |
| ---------------- | ------------------------------- |
| `DEPLOY_SSH_KEY` | Private key for the deploy host |
| `DEPLOY_HOST`    | Target hostname or IP           |
| `DEPLOY_USER`    | SSH user on the target host     |

Create a `production` environment (Settings → Environments) to require manual
approval and scope deployment secrets. The workflow uses the built-in
`GITHUB_TOKEN` for GHCR, so no extra registry credentials are needed.

### Branch protection

Protect `main` and require the `Lint, format, type-check`, `Tests (API)`, and
`E2E (Playwright)` status checks before merging.
