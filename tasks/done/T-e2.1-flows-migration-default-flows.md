# T-e2.1 — Flows migration + default flows

**Status:** done (awaiting human review; not committed unless requested)  
**Date:** 2026-05-28  
**Verdict:** **PASS WITH NOTES**

## Goal

Introduce first-class `flows` entity and backend flow resolution without changing conversation lookup, prompt behavior, or n8n workflows.

## Delivered

| Area | Detail |
|------|--------|
| Migration | `backend/alembic/versions/0008_create_flows.py` (`0007` → `0008`) |
| Model | `backend/app/models/flow.py` |
| Service | `backend/app/services/flow_service.py` — `resolve_for_webhook` |
| Webhook API | Optional `flow_key` on request; `data.flow` on success; `FLOW_NOT_FOUND` on unknown key |
| Tests | `test_flow_service.py`, migration/model tests updated; **400** pytest green |
| Docs | Spec bridge in `unified-conversation-model.md`; audit below |

## Default flows (demo DB after upgrade)

| Business | `flow_key` | `is_default` |
|----------|------------|--------------|
| `alpstein_ai_demo_001` | `default` | true |
| `demo_barbershop_001` | `barbershop_default` | true |

## Out of scope (unchanged)

- `conversations.flow_id`
- Flow-scoped conversation lookup
- `message_traces`
- n8n workflow changes
- Prompt / AI behavior changes

## Notes

- Rebuild or redeploy `alpstein_backend` image so container includes `0008` migration file and app code (hot `docker cp` used for validation only).
- `database-schema.md` not updated in E2.1 — follow-up if team wants schema doc parity.

## Audit

[`docs/audits/e2-1-flows-migration-default-flows-2026-05-28.md`](../../docs/audits/e2-1-flows-migration-default-flows-2026-05-28.md)
