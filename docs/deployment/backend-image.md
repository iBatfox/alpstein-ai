# Backend container image (B2.3)

**Contract:** [`deployment-contract.md`](deployment-contract.md)  
**Dockerfile:** [`backend/Dockerfile`](../../backend/Dockerfile)  
**Production deps:** [`backend/requirements-prod.txt`](../../backend/requirements-prod.txt)

Reproducible backend **image artifact only** — not added to root `docker-compose.yml` until **B2.6**.

---

## Image summary

| Attribute | Value |
|-----------|--------|
| Base image | `python:3.12-slim-bookworm` |
| Python | **3.12** (matches dev venv baseline) |
| Workdir | `/app` |
| User | `alpstein` (uid 1000, non-root) |
| Exposed port | `8000` |
| Default CMD | `uvicorn app.main:app --host 0.0.0.0 --port 8000` |
| Alembic in image | Yes (files copied; **not** run at build) |
| Secrets in image | **No** |

---

## Production dependencies

`requirements-prod.txt` — runtime only:

| Package | Purpose |
|---------|---------|
| fastapi | HTTP API |
| uvicorn[standard] | ASGI server |
| pydantic-settings | `app.core.config` |
| httpx | OpenAI HTTP client |
| SQLAlchemy + asyncpg | Async PostgreSQL |
| alembic | Migrations (exec at deploy, not build) |
| langfuse | Dev/internal tracing (import required at startup) |

**Excluded:** `pytest` (remains in `requirements.txt` for local/CI).

---

## Build

From repository root:

```bash
docker build -f backend/Dockerfile -t alpstein-ai-backend:local backend
```

Tag convention for releases: `alpstein-ai-backend:<git-short-sha>` (operator-defined).

---

## Validation (no live DB)

```bash
# Import smoke — does not start uvicorn or connect to Postgres
docker run --rm alpstein-ai-backend:local \
  python -c "import app.main; print('import ok')"

# Optional — container starts (will fail readiness on traffic without DB/env)
docker run --rm -p 8000:8000 \
  -e ALPSTEIN_AI_DATABASE_URL=postgresql+asyncpg://alpstein:x@postgres:5432/alpstein_ai \
  -e N8N_BACKEND_API_TOKEN=dev-token \
  alpstein-ai-backend:local
# curl http://127.0.0.1:8000/api/v1/health
```

Build-time validation must **not** require PostgreSQL.

---

## `.dockerignore`

Excludes: `.venv`, `tests/`, `scripts/`, `.env`, caches, `*.md` under backend context.

---

## Rollback

| Action | Effect |
|--------|--------|
| Stop using image tag | Compose/k8s not wired yet — no runtime impact |
| `docker rmi alpstein-ai-backend:local` | Remove local image |
| Revert Dockerfile commit | Previous build recipe |

RBU (image-only): previous image digest or tag + Dockerfile git revision.

---

## Out of scope (B2.3)

- `backend` service in root `docker-compose.yml` (B2.6)
- `alembic upgrade` in Dockerfile or CMD (B2.5 entrypoint)
- Live Contabo host uvicorn replacement
- n8n workflow changes

---

## Related

- [`postgres-compose.md`](postgres-compose.md) — B2.2 database service
- [`backend/.env.example`](../../backend/.env.example) — runtime env at deploy
