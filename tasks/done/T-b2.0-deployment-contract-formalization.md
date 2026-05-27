# T-b2.0 — Deployment Contract Formalization (B2.0)

**Status:** done (spec deliverable)  
**Phase:** B2 — Deployment Portability  
**Depends on:** B1 Deployment Portability Audit  

## Goal

Formalize canonical deployment contracts before any Docker implementation.

## Scope

- Create `docs/deployment/deployment-contract.md`
- Startup lifecycle, env model, network model, boundaries, RBUs, B2 phases

## Out of scope

- Dockerfile, compose, runtime changes, health endpoint implementation

## Deliverable

- [x] `docs/deployment/deployment-contract.md`

## Next

- B2.1 — Track `.env.example` in git; align spec drift (`DATABASE_URL` vs `ALPSTEIN_AI_DATABASE_URL`)
