# Deployment documentation

| Document | Purpose |
|----------|---------|
| [`deployment-contract.md`](deployment-contract.md) | **Canonical** env names, startup order, network, RBUs (B2.0+) |
| [`../ops/database-recovery.md`](../ops/database-recovery.md) | Alembic replay after DB loss |
| [`../ops/n8n-env-credential-checklist.md`](../ops/n8n-env-credential-checklist.md) | n8n ↔ backend token alignment |
| [`../ops/n8n-runtime-start.md`](../ops/n8n-runtime-start.md) | Legacy host n8n start (Contabo) |

## Environment templates (git-tracked)

| File | Service |
|------|---------|
| [`backend/.env.example`](../../backend/.env.example) | Backend + Alembic (canonical) |
| [`n8n/.env.example`](../../n8n/.env.example) | Alpstein n8n |
| [`.env.example`](../../.env.example) | Index / quick-start pointer |

| [`postgres-compose.md`](postgres-compose.md) | B2.2+ Postgres + B2.6 backend compose ops |
| [`backend-image.md`](backend-image.md) | B2.3–B2.6 Backend image + entrypoint + compose |

## Compose (git-tracked)

| File | Purpose |
|------|---------|
| [`docker-compose.yml`](../../docker-compose.yml) | `postgres` + `backend` (B2.6) — internal network only |
| [`docker-compose.dev.yml`](../../docker-compose.dev.yml) | Dev-only `127.0.0.1` binds (postgres `15433`, backend `8000`) |
| [`.env.example`](../../.env.example) | `POSTGRES_*`, backend vars for compose |

| [`backend/Dockerfile`](../../backend/Dockerfile) | Backend image build context |

n8n on compose network: **B2.7** per contract §12.

**Python version (portable image):** 3.12 (`python:3.12-slim-bookworm`).
