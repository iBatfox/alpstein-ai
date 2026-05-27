# T-c1 — n8n runtime / export parity (Phase C Step C1)

**Status:** Done (2026-05-27)  
**Type:** Audit + governance (no workflow or live runtime changes)

## Goal

Establish discipline so n8n runtime state can be reproduced from repository state. Prevent silent UI drift; optimize rollback safety.

## Deliverables

| # | Deliverable | Location |
|---|-------------|----------|
| 1 | Runtime/export parity audit | [`docs/ops/n8n-runtime-export-parity.md`](../../docs/ops/n8n-runtime-export-parity.md) |
| 2 | Drift risks (D1–D10) | Same §3 |
| 3 | Repository structure | [`n8n/workflows/README.md`](../../n8n/workflows/README.md) |
| 4 | Export governance rules (E1–E5) | Parity doc §5 |
| 5 | Runtime verification procedure (R1–R6) | Parity doc §6 |
| 6 | Safe export/import flow | Parity doc §7 |
| 7 | Rollback-safe workflow RBU | Parity doc §8 |
| 8 | Pre-deploy gates G-EXP-1..7 | Parity doc §9 |
| 9 | Minimal operational policy | Parity doc §10 |
| 10 | Implementation breakdown C2–C7 | Parity doc §11 |

## Also added

- [`n8n/workflows/runtime-registry.md`](../../n8n/workflows/runtime-registry.md) — runtime ID map (ops-maintained)

## Out of scope (confirmed)

- Live Contabo import/activate changes
- Workflow redesign / business logic
- Backend, migrations, K8s, observability
- Automated scrub (deferred to C2 / T14.6)

## Next

| Task | Priority |
|------|----------|
| **C2 / T14.6** | **done** — [`T14.6-n8n-export-scrub-parity-gate.md`](T14.6-n8n-export-scrub-parity-gate.md) |
| **C5 / T14.5** | Telegram regression on canonical export |
| **C6** | Extend clean-clone gate with G5 webhook import |

## Rollback

Revert doc commits only — no runtime effect.
