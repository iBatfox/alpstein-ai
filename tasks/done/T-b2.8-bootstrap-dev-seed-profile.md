# T-b2.8 — Bootstrap / Dev Seed Profile (B2.8)

**Status:** done (awaiting operator review)  
**Phase:** B2 — Deployment Portability  
**Depends on:** [`T-b2.6-backend-compose-service.md`](T-b2.6-backend-compose-service.md), [`T-b2.7-n8n-internal-compose-network.md`](T-b2.7-n8n-internal-compose-network.md)  
**Rollback anchors:** `baseline-b2.6-compose`, `baseline-b2.7-n8n-network`

## Goal

Optional compose profile `bootstrap` for dev/test seed after migrations — never on normal `up`, never in production-like env.

## Scope

- `backend/docker-bootstrap.sh`
- `docker-compose.yml` — `backend-bootstrap` profile service
- Dockerfile copies `scripts/`
- [`bootstrap-profile.md`](../docs/deployment/bootstrap-profile.md)
- Contract + project status docs

## Out of scope

- n8n workflow import/activation
- Auto-seed on compose up
- Contabo / live runtime
- New Alembic revisions

## Deliverables

- [x] Bootstrap policy documented
- [x] Compose profile `bootstrap` + one-shot service
- [x] Env guard (dev/test only)
- [x] Seed order: Python seed → 2 SQL files
- [x] Agent validation (2026-05-27): `config` OK; production env exit 1; bootstrap exit 0; businesses `demo_barbershop_001`, `alpstein_ai_demo_001`; no secrets in logs; no bootstrap in default `ps`

## Acceptance

- [x] Normal `up` does not run bootstrap
- [x] `--profile bootstrap` runs seed successfully on fresh DB
- [x] `ALPSTEIN_AI_ENVIRONMENT=production` refuses bootstrap
- [x] No secrets in bootstrap logs
- [ ] Operator tag `baseline-b2.8-bootstrap` after review

## Next

**B2.9** — clean-clone gate transcript
