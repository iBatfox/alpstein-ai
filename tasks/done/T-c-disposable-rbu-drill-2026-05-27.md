# T-c — Disposable RBU drill (Phase C)

**Status:** done (2026-05-27)  
**Type:** Operational rehearsal — no code/runtime changes  
**Evidence:** [`docs/audits/disposable-rbu-drill-2026-05-27.md`](../docs/audits/disposable-rbu-drill-2026-05-27.md)

## Goal

Validate rollback documentation against disposable compose reality; expose hidden dependencies.

## Rollback tested

`baseline-b2.9-clean-clone-gate` (`f7cca06`) — restore to `02a4ee8`

## Verdict

**CONDITIONAL NO-GO** for Phase D until P0: commit C2 export-scrub + C1 parity docs; retag `baseline-c2-export-scrub-gate`.

## Key findings

- Portable stack rollback **PASS** (trivial diff vs HEAD)
- `export-scrub.sh` **not in git** despite tag name
- C1 registry/README **not in git** at tested tags
- Webhook direct backend **PASS** after bootstrap

## Rollback

N/A — docs only
