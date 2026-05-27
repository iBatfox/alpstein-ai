# Deployment documentation

| Document | Purpose |
|----------|---------|
| [`deployment-contract.md`](deployment-contract.md) | **Canonical** env names, startup order, network, RBUs (B2.0+) |
| [`../audits/clean-clone-gate-2026-05-27.md`](../audits/clean-clone-gate-2026-05-27.md) | B2.9 clean-clone verification evidence |
| [`../audits/disposable-rbu-drill-2026-05-27.md`](../audits/disposable-rbu-drill-2026-05-27.md) | Disposable RBU rollback rehearsal |
| [`../audits/d4-2-compose-e2e-hardening-2026-05-28.md`](../audits/d4-2-compose-e2e-hardening-2026-05-28.md) | D4.2 compose E2E / portability drill |
| [`../audits/d4-operational-wrap-up-2026-05-27.md`](../audits/d4-operational-wrap-up-2026-05-27.md) | **D4.5** operational wrap-up — SoT, risks, Phase E readiness |
| [`../ops/operational-ingress-policy.md`](../ops/operational-ingress-policy.md) | Single ingress policy (OPS-C1) |
| [`../ops/n8n-runtime-export-parity.md`](../ops/n8n-runtime-export-parity.md) | n8n export governance + G-EXP-2 |
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
| [`bootstrap-profile.md`](bootstrap-profile.md) | B2.8 optional dev seed profile |

## Compose (git-tracked)

| File | Purpose |
|------|---------|
| [`docker-compose.yml`](../../docker-compose.yml) | `postgres` + `backend` + `n8n` (B2.6–B2.7) — internal network only |
| [`docker-compose.dev.yml`](../../docker-compose.dev.yml) | Dev-only `127.0.0.1` binds (postgres `15433`, backend `8000`, n8n `15680`) |
| [`.env.example`](../../.env.example) | `POSTGRES_*`, backend vars for compose |

| [`backend/Dockerfile`](../../backend/Dockerfile) | Backend image build context |

| [`n8n-compose.md`](n8n-compose.md) | B2.7 n8n on `alpstein_internal` → `http://backend:8000` |
| [`n8n-runtime-export-parity.md`](../ops/n8n-runtime-export-parity.md) | Phase C1 — workflow export governance |

Legacy host n8n: [`n8n/docker-compose.yml`](../../n8n/docker-compose.yml) + [`n8n-runtime-start.md`](../ops/n8n-runtime-start.md).

**Python version (portable image):** 3.12 (`python:3.12-slim-bookworm`).
