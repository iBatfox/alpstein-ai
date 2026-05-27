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

| [`postgres-compose.md`](postgres-compose.md) | B2.2 Postgres service ops |
| [`backend-image.md`](backend-image.md) | B2.3 Backend Dockerfile / image build |

## Compose (git-tracked)

| File | Purpose |
|------|---------|
| [`docker-compose.yml`](../../docker-compose.yml) | **Postgres only** (B2.2) — `postgres:15`, volume `alpstein_postgres_data` |
| [`docker-compose.dev.yml`](../../docker-compose.dev.yml) | Dev-only `127.0.0.1:15433` host bind |
| [`.env.example`](../../.env.example) | `POSTGRES_*` for compose |

| [`backend/Dockerfile`](../../backend/Dockerfile) | Backend image (B2.3) — **not** in compose until B2.6 |

Backend service in root compose and n8n network: B2.6 / B2.7 per contract §12.

**Python version (portable image):** 3.12 (`python:3.12-slim-bookworm`).
