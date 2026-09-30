# 🔐 Security Review Report

|                |                                                                                                    |
| -------------- | -------------------------------------------------------------------------------------------------- |
| **Project**    | products_rest_api                                                                                  |
| **Scan Date**  | 2026-09-30                                                                                         |
| **Scope**      | `src/`, `tests/`, `.github/`, `Dockerfile`, `docker-compose.yml`, `pyproject.toml`, `.env.example` |
| **Languages**  | Python 3.12+, YAML, Dockerfile                                                                     |
| **Frameworks** | FastAPI, Pydantic v2, SQLite (stdlib `sqlite3`), Uvicorn                                           |
| **Tooling**    | `/security-review` skill (AI-assisted static analysis) + `pip-audit`                               |

---

## Findings Summary

| Severity    | Count  |
| ----------- | ------ |
| 🔴 CRITICAL | 0      |
| 🟠 HIGH     | 2      |
| 🟡 MEDIUM   | 3      |
| 🔵 LOW      | 4      |
| ⚪ INFO     | 3      |
| **TOTAL**   | **12** |

- **Dependency Audit:** 0 vulnerable packages (`pip-audit`: "No known vulnerabilities found")
- **Secrets Scan:** 0 exposed credentials

**Headline:** The code is genuinely well-hardened on the classic injection surface — every SQL statement is parameterized, sort/filter columns are allow-listed, and Pydantic rejects unknown fields. The real gaps are **missing authentication/authorization**, **no rate limiting**, and **deploy-pipeline hardening**.

---

## 🟠 HIGH — Missing Authentication & Authorization

**Confidence: HIGH** · `src/app/api/products.py` (all routes), `src/app/main.py`

Every endpoint — including `POST`, `PUT`, and `DELETE` — is completely unauthenticated. There is no auth dependency, no API key check, no middleware.

⚠️ **Risk:** Any anonymous client can create, overwrite, or delete the entire product catalog. `DELETE /api/v1/products/{id}` is a one-request destructive action. This is the single most impactful issue in the repo.

✅ **Recommended fix:** Add an auth dependency (API key or OAuth2/JWT) and apply it to the mutating routes at minimum. Example shape:

```python
from fastapi import Security
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

def require_api_key(key: str = Security(api_key_header)) -> None:
    expected = os.environ["API_KEY"]  # never hardcode
    if not secrets.compare_digest(key, expected):
        raise HTTPException(status_code=401, detail="Invalid API key")

@router.post("", dependencies=[Depends(require_api_key)], ...)
```

📚 OWASP A01:2021 – Broken Access Control

---

## 🟠 HIGH — Unverified SSH Host Key in Deployment Pipeline

**Confidence: HIGH** · `.github/workflows/cd.yml`, deploy step

```yaml
ssh-keyscan -H "$HOST" >> ~/.ssh/known_hosts 2>/dev/null
```

⚠️ **Risk:** `ssh-keyscan` blindly trusts whatever host answers at `$HOST`. An attacker who can spoof DNS/network for the deploy host can present their own key, capture the SSH session, and receive the `GHCR_TOKEN` that is piped into the remote shell — leading to registry and deployment compromise. This is a textbook MITM in the CD path.

✅ **Recommended fix:** Store the host's public key as a repository secret and write it to `known_hosts` instead of scanning:

```yaml
- name: Trust deploy host key
  run: |
    mkdir -p ~/.ssh
    printf '%s\n' "${{ secrets.DEPLOY_HOST_KEY }}" > ~/.ssh/known_hosts
    chmod 600 ~/.ssh/known_hosts
```

📚 OWASP A02:2021 – Cryptographic Failures / CWE-295

---

## 🟡 MEDIUM — No Rate Limiting on Any Endpoint

**Confidence: HIGH** · `src/app/main.py`

No rate limiting or throttling exists. Combined with the missing auth (above), the API is trivially abusable for catalog flooding, resource exhaustion, and enumeration of product IDs.

✅ **Recommended fix:** Add `slowapi` (or a reverse-proxy limit) and apply a default limit, with stricter limits on writes.

📚 OWASP A04:2021 – Insecure Design

---

## 🟡 MEDIUM — Secrets Exposed via Process Arguments on Deploy Host

**Confidence: MEDIUM** · `.github/workflows/cd.yml`

```yaml
ssh "$USER@$HOST" "GHCR_USER='$GHCR_USER' GHCR_TOKEN='$GHCR_TOKEN' IMAGE='$IMAGE' bash -s" <<'REMOTE'
```

⚠️ **Risk:** The `GITHUB_TOKEN` is interpolated into the remote command line, so it is visible in the remote host's process table (`ps`) to any local user during the deploy window.

✅ **Recommended fix:** Pass the token over stdin or use `ssh -o SendEnv` / a temporary `docker login` on the runner, or scope the token to `read:packages` only (it already is via `GITHUB_TOKEN`, which limits blast radius).

---

## 🟡 MEDIUM — `image` URL Validation Is Too Permissive

**Confidence: MEDIUM** · `src/app/schemas/product.py`, `validate_image_url`

```python
if value and not value.startswith(("https://", "http://")):
    raise ValueError(...)
```

⚠️ **Risk:** `startswith` accepts malformed values such as `"http://"`, `"https:// "`, or `"http://evil"` with no host. The existing test `test_incomplete_absolute_image_url_is_rejected` expects `"http://"` to be rejected — but the validator accepts it, so the intended contract is not enforced (the test is currently masked by the collection error noted below). No SSRF today because the URL is never fetched server-side, but it is a stored-data integrity weakness.

✅ **Recommended fix:** Use Pydantic's `AnyHttpUrl` (or `TypeAdapter(AnyHttpUrl)`) and allow `""` explicitly.

📚 OWASP A03:2021 – Injection (input validation)

---

## 🔵 LOW — No Security Response Headers

**Confidence: HIGH** · `src/app/main.py`

No `X-Content-Type-Options`, `X-Frame-Options`, `Strict-Transport-Security`, or CSP. Swagger UI is served at `/docs` in all environments.

✅ Add `starlette.middleware.httpsredirect`/`TrustedHostMiddleware` and a small header middleware; consider disabling `/docs` outside dev.

---

## 🔵 LOW — No CORS Policy Defined

**Confidence: MEDIUM** · `src/app/main.py`

No `CORSMiddleware`. Default browser behavior blocks cross-origin reads, which is safe-by-default, but the absence is undocumented and easy to misconfigure later. If CORS is added, avoid `allow_origins=["*"]` with credentials.

---

## 🔵 LOW — `request_id` Is Never Populated

**Confidence: HIGH** · `src/app/core/errors.py` + `src/app/core/logging.py`

`problem_response` reads `request.state.request_id`, but nothing ever sets it (no middleware). Every error response and log line reports `"request_id": "unknown"`, defeating request correlation for incident response.

✅ Add middleware that reads/generates `X-Request-ID` and sets `request.state.request_id`.

---

## 🔵 LOW — SQLite Database File Permissions Not Restricted

**Confidence: LOW** · `src/app/db/database.py`

The DB file is created with default umask permissions. On a shared host this may be world-readable. Consider `os.chmod(path, 0o600)` after creation, or rely on the container's non-root user (already good).

---

## ⚪ INFO — Unused `httpx2` Dev Dependency

**Confidence: HIGH** · `pyproject.toml:15`

`httpx2>=2.13.1` is declared but never imported anywhere in the repo (verified). It is a legitimate package (`pydantic/httpx2`), but it is dead weight that widens the supply-chain surface for no benefit. Remove it unless intentionally staged for future use.

---

## ⚪ INFO — Pre-existing Test Collection Failure Masks Coverage

**Confidence: HIGH** · `tests/test_error_handling.py:11`

`from app.core.errors import PersistenceError` — `PersistenceError` does not exist in `src/app/core/errors.py`. This `ImportError` blocks whole-suite collection, so the error-handling and validation tests (including the `image` URL test above) never run. Not a vulnerability itself, but it hides real regressions.

---

## ⚪ INFO — Docker Base Image Not Digest-Pinned

**Confidence: MEDIUM** · `Dockerfile`

`FROM python:3.12-slim` and `ghcr.io/astral-sh/uv:0.5.11` are tag-pinned, not digest-pinned. Tags are mutable. The image otherwise follows good practice (multi-stage, non-root `app` user, healthcheck, no secrets in `ENV`/`ARG`).

---

## ✅ What's Done Right (verified, not assumed)

- **SQL injection:** All queries in `src/app/repositories/products.py` use `?` placeholders. The only f-string interpolation is `where_clause` (built from fixed literals), `column` (from the `_SORT_COLUMNS` allow-list), and `direction` (constrained to `asc`/`desc`). No user input reaches SQL identifiers.
- **Mass assignment:** `extra="forbid"` on all request models; unknown fields rejected.
- **Secrets:** No hardcoded credentials. `.env*` is git-ignored with `!.env.example`; only `.env.example` exists. CI/CD uses `${{ secrets.* }}` correctly.
- **Dependencies:** `pip-audit` reports no known vulnerabilities.
- **Error handling:** RFC 7807 problem responses; no stack traces returned to clients.
- **Container:** Runs as unprivileged user; `.dockerignore` excludes `.env*`, tests, and local DBs.

---

## 🛠️ Patch Proposals

> ⚠️ **Review each patch before applying. Nothing has been changed yet.**

**Patch 1/2 — Add API-key auth to mutating routes** (`src/app/api/products.py`)
Add a `require_api_key` dependency and attach it to `POST`/`PUT`/`DELETE`. Requires an `API_KEY` env var (add to `.env.example`).

**Patch 2/2 — Pin the deploy host key** (`.github/workflows/cd.yml`)
Replace `ssh-keyscan` with a `DEPLOY_HOST_KEY` secret written to `known_hosts`.

Both are shown in the findings above. No files were modified by this audit.

---

## 📋 Scan Coverage

| Metric           | Value                                                                              |
| ---------------- | ---------------------------------------------------------------------------------- |
| Files scanned    | ~20 source/config files (`src/`, `tests/`, `.github/`, Docker, compose, pyproject) |
| Lines analyzed   | ~1,200 (excluding `.venv`, caches, skill docs)                                     |
| Dependency audit | `pip-audit` — clean                                                                |

### ⚡ Next Steps

1. Decide on auth model for write endpoints (HIGH)
2. Fix the CD host-key verification (HIGH)
3. Add rate limiting + request-id middleware (MEDIUM/LOW)
4. Fix the `PersistenceError` import so the test suite actually runs

> 💡 **NOTE:** Static analysis only — it does not execute the app. Pair with DAST for runtime coverage.
