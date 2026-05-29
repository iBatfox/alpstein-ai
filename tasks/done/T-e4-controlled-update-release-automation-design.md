# T-e4 — Controlled update & release automation (design)

**Status:** done (spec-only)  
**Date:** 2026-05-28  
**Phase:** E4.1–E4.6 architecture

## Goal

Design central release orchestration with Telegram approval, staging verification, production gate, rollback, and immutable audit — **no implementation** in this task.

## Deliverables

- [x] [`docs/architecture/e4-controlled-update-release-automation.md`](../../docs/architecture/e4-controlled-update-release-automation.md) — E4.1–E4.6
- [x] [`docs/ops/e4-release-controller-runbook.md`](../../docs/ops/e4-release-controller-runbook.md) — operator skeleton
- [x] Project status updates

## Out of scope

- `release-ctl` code
- Telegram bot deployment
- Runtime / compose / workflow changes
- nginx / firewall changes

## Success criteria (design)

Documented gates: approval → staging PASS → backup tag → prod confirm → audit.

## Next implementation slice

**E4-R1:** `release-ctl` CLI + SQLite audit + state machine (no Telegram).
