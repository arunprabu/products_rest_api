# AGENTS.md

Note: Do not assume everything on your own. If the request/prompt/query is ambiguous, ask questions at the user.

## Project overview

Product catalog REST API built with Python 3.12+, FastAPI, and SQLite, using a `src` layout. Layers are separated: HTTP routing, business logic, persistence, schemas, configuration, and domain models.

## Setup

```shell
uv sync --dev
```

`uv run` executes commands inside `.venv` automatically; no manual activation needed.

Enable the pre-commit hooks once per clone (runs Ruff format + lint on staged files and blocks the commit on failure):

```shell
uv run pre-commit install
```

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

Pre-commit hooks (`.pre-commit-config.yaml`) run `ruff format` and `ruff check --fix` on staged Python files and abort the commit on failure. Run them across the whole tree with `uv run pre-commit run --all-files`.

Build and run the container:

```shell
docker build -t products-rest-api:local .
docker compose up --build
```

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

| Method   | Path                            | Description                                                             |
| -------- | ------------------------------- | ----------------------------------------------------------------------- |
| `POST`   | `/api/v1/products`              | Create a product (201)                                                  |
| `GET`    | `/api/v1/products`              | List products                                                           |
| `GET`    | `/api/v1/products/{product_id}` | Retrieve a product                                                      |
| `PUT`    | `/api/v1/products/{product_id}` | Replace a product                                                       |
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

## Docker

- `Dockerfile` — multi-stage build. A builder stage installs runtime dependencies from `uv.lock` with `uv`; the runtime stage copies only the virtualenv and `src/`.
- Runs as the unprivileged `app` user and exposes a `HEALTHCHECK` against `/openapi.json`.
- Defaults: `DATABASE_PATH=/app/data/products.db`, `LOG_LEVEL=INFO`. Mount a volume at `/app/data` to persist the SQLite database.
- `.dockerignore` excludes tests, caches, `.env*`, local databases, and agent tooling from the build context.
- `docker-compose.yml` runs the API locally with a named `products-data` volume.

## CI/CD

GitHub Actions workflows live in `.github/workflows/`.

- `ci.yml` — runs on pushes and pull requests to `main`, and is reusable via `workflow_call`.
  - `quality`: `ruff format --check`, `ruff check`, `mypy`.
  - `audit`: `pip-audit` against the locked environment, enriched with OSV severity; fails on HIGH/CRITICAL findings (`scripts/audit_dependencies.py`).
  - `test`: `pytest -m api` with coverage; uploads `coverage.xml`.
  - `e2e`: `pytest -m e2e` with Chromium; uploads traces/screenshots on failure.
  - `test` and `e2e` run only after `quality` passes.
- `cd.yml` — runs on pushes to `main` and via `workflow_dispatch`.
  - `ci`: reuses `ci.yml` so a failing commit is never deployed.
  - `build-and-push`: builds the image and pushes to GHCR as `ghcr.io/<owner>/<repo>:<sha>` and `:latest`.
  - `deploy`: pulls the image on the target host over SSH and restarts the container, gated by the `production` environment.

Required repository secrets: `DEPLOY_SSH_KEY`, `DEPLOY_HOST`, `DEPLOY_USER`. GHCR uses the built-in `GITHUB_TOKEN`. Protect `main` and require the `Lint, format, type-check`, `Dependency audit`, `Tests (API)`, and `E2E (Playwright)` checks.

## Commit messages

All commits MUST follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/):

```text
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

- Use a lowercase `type` from: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`.
- Use an optional scope naming the affected area, e.g. `api`, `services`, `repositories`, `schemas`, `db`, `core`, `deps`, `ci`.
- Write the description in the imperative mood, lowercase, with no trailing period (e.g. `add price range filter`).
- Mark breaking changes with `!` after the type/scope (e.g. `feat(api)!: ...`) and/or a `BREAKING CHANGE:` footer.
- Reference issues in the footer (e.g. `Refs: #123`, `Closes: #123`).

Examples:

```text
feat(api): add price range filter to product listing
fix(repositories): escape category before LIKE match
docs: document Conventional Commits workflow
test(services): cover duplicate product creation
chore(deps): bump fastapi to 0.115
```

## Conventions

- Persistence uses parameterized SQL with explicit transactions.
- Sorting is allow-listed via the `SortField` type; never interpolate user input into SQL.
- Follow existing layer boundaries: routes call services, services call repositories.
- Do not add comments unless necessary; match existing docstring style.
