# Project instructions

- Use Python 3.12+, FastAPI, standard-library `sqlite3`, and the src layout.
- Keep HTTP handling, business logic, persistence, schemas, and configuration in their respective layers.
- Write or update pytest coverage before or alongside every behavior change.
- Use parameterized SQL, explicit transactions, and allow-listed sort/filter columns; never interpolate client input into SQL identifiers.
- Never commit real secrets or modify `.env*` except `.env.example`.
- Format/lint with Ruff, type-check with strict mypy, and run pytest with coverage before completing work.
