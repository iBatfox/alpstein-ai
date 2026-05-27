# T-b2.1 — Deployment Governance Artifacts (B2.1)

**Status:** done (awaiting operator review)  
**Phase:** B2 — Deployment Portability  
**Depends on:** [`T-b2.0-deployment-contract-formalization.md`](T-b2.0-deployment-contract-formalization.md)

## Goal

Commit and align deployment governance artifacts before Docker implementation.

## Scope

- Track and align `.env.example` templates with B2.0 contract
- Mark deprecated env names and legacy host patterns
- Update project-status and contradicting spec/ops references
- No Dockerfile, compose, runtime, or health endpoint changes

## Deliverables

- [x] `backend/.env.example` (canonical backend template)
- [x] `.env.example` (repo index / pointer)
- [x] `n8n/.env.example` (aligned + legacy/portable comments)
- [x] `docs/deployment/README.md`
- [x] `specs/architecture/deployment.md` — portability banner + §10 names
- [x] `specs/architecture/backend-architecture.md` — §15 names
- [x] `docs/ops/n8n-runtime-start.md`, `n8n-env-credential-checklist.md` — legacy/portable notes
- [x] `docs/project-status/current-state.md`, `next-steps.md`
- [x] `docs/deployment/deployment-contract.md` — B2.1 changelog + canonical paths

## Acceptance

- Clean clone exposes env contract via tracked examples
- No secrets committed
- Naming matches B2.0 contract
- Legacy values marked, not presented as target
- Docker not started

## Next

**B2.2** — Postgres compose service only (`postgres:15`, volume `alpstein_ai`, no backend image)
