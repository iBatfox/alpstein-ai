# F.2.1 — ERPNext Lead sync via n8n (audit)

**Date:** 2026-05-29  
**Slice:** n8n workflow only — no backend / DB changes  
**Export `versionId`:** `f2.1-erpnext-lead-sync-v1`

## Implementation summary

| Item | Detail |
|------|--------|
| Workflow | `alpstein-customer-ingress` |
| Trigger point | Parallel branch from **POST Backend** success output (same as owner notify) |
| Blocking? | **No** — all ERP HTTP nodes `continueOnFail: true` |
| SoT | Alpstein PostgreSQL unchanged |
| CRM | ERPNext Lead create/update via REST |

## Dedupe logic

Documented in [`n8n-erpnext-lead-sync.md`](../ops/n8n-erpnext-lead-sync.md). Unit-style checks: `scripts/n8n/test_erpnext_lead_dedupe.py`.

## Error handling

| Failure | Customer reply | Logger |
|---------|----------------|--------|
| ERPNext timeout | Continues | `outcome: failed`, `error_message` truncated |
| 401/403 auth | Continues | `outcome: failed` |
| Search empty | Continues | `outcome: created` on successful POST |
| Search hit | Continues | `outcome: updated` on successful PUT |
| Kill switch off | Continues | Branch not executed |

## Test evidence (operator)

| # | Scenario | Date | Exec ID | Result | Notes |
|---|----------|------|---------|--------|-------|
| 1 | New Telegram → one Lead | | | pending | |
| 2 | Same Telegram → no duplicate | | | pending | |
| 3 | New Website → one Lead | | | pending | |
| 4 | Missing phone/email → ext id dedupe | | | pending | |
| 5 | ERPNext unavailable | | | pending | Stop `alpstein-erpnext-frontend-1` briefly |
| 6 | Invalid API credential | | | pending | Wrong header in test cred |

**Automated (repo, 2026-05-29):** `backend/.venv/bin/python -m pytest scripts/n8n/test_erpnext_lead_dedupe.py -q` → **4 passed**

## Reviewer findings (alpstein-reviewer)

### Review summary

**Pass with notes** for F.2.1 design — promote to staging with kill switch off by default; complete live evidence before production flag.

### Findings

| Severity | Finding | Mitigation |
|----------|---------|------------|
| **Important** | Description-based dedupe for `external_id` relies on LIKE — rare collision if marker substring appears elsewhere | Marker prefix `alpstein:dedupe:` is namespaced |
| **Important** | ERPNext OOM on shared VPS could slow HTTP tail (not customer path) | Monitor; keep sync timeout 15s |
| **Suggestion** | Future: custom ERPNext field `alpstein_external_key` for indexed dedupe | F.2.2+ spec |
| **LOW** | `console.log` only — no central observability yet | Accept for F.2.1 |

### Scope check

- **MVP alignment:** partial — CRM sync is post-MVP but approved in Phase F charter.
- No PostgreSQL ownership change.
- No backend contract change.

### Specs consulted

- `AGENTS.md` (n8n orchestration, no n8n→PG writes)
- `docs/architecture/f1-erpnext-installation-operational-architecture.md`

### What was not reviewed

- Live ERPNext API on production (operator)
- n8n execution after import
