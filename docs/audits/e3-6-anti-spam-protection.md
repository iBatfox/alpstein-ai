# E3.6 — Anti-spam protection (implementation)

**Branch:** `stabilization/runtime-baseline`  
**Phase:** E3 — Multi-Channel Operational Hardening  
**Status:** **Implemented — awaiting human review (do not enable flag in prod)**  
**Design:** [`e3-6-anti-spam-protection-design.md`](e3-6-anti-spam-protection-design.md)

---

## Summary

E3.6 adds backend-owned deterministic anti-spam protection for MVP adapters `telegram` and `website_chat`. It stacks after E3.5 rate limiting and before E3.4 ingress containment / AI orchestration.

| Slice | Deliverable | Status |
|-------|-------------|--------|
| E3.6a | Spam detection model — `spam_indicator_buckets`, SHA-256 payload fingerprint, five rules | Done |
| E3.6b | Reversible containment — `spam_containments`, webhook enforcement | Done |
| E3.6c | Observability — `spam_decisions` audit + list APIs | Done |

**Alembic:** `0019` (`spam_indicator_buckets`), `0020` (`spam_containments`), `0021` (`spam_decisions`)

---

## Approved rules

| Rule ID | Signal |
|---------|--------|
| `payload_repeat` | Same normalized payload hash repeated in conversation window |
| `conversation_burst` | High message count in conversation window |
| `adapter_fanout` | Many distinct conversations on same adapter in window |
| `retry_abuse` | High replay event count per conversation |
| `replay_storm` | High replay-ignored count per adapter channel |

No AI/ML, no external anti-spam services, no Redis/queues.

---

## Feature flags

| Variable | Default | Notes |
|----------|---------|-------|
| `ALPSTEIN_AI_SPAM_PROTECTION_ENABLED` | `false` | Master switch — **keep false until rollout gate passes** |
| `ALPSTEIN_AI_SPAM_PRODUCTION_SAFE_MODE` | `true` | When true, downgrades `throttle` / `temporary_block` to `mark_suspicious` |

Per-rule thresholds/actions are env-configurable (`ALPSTEIN_AI_SPAM_RULE_*`).

---

## Rollout gate (mandatory)

Keep `ALPSTEIN_AI_SPAM_PROTECTION_ENABLED=false` until:

1. E3.6 implementation tests are green
2. E3.5d PostgreSQL concurrency validation is green
3. E3.6 staging validation is completed

Migrations (`0019`–`0021`) may be applied while the flag stays off.

---

## Webhook placement

```text
duplicate detection → E3.5 rate limit → E3.6 spam → E3.4 gate → AI orchestration
```

**Error codes:** `SPAM_THROTTLED` (429), `SPAM_CONTAINED` (403)

---

## Observability APIs

- `GET /api/v1/observability/spam-decisions`
- `GET /api/v1/observability/spam-containments`

Adapter monitoring extended with `spam_decision_count` / `spam_containment_count` (optional, low-risk).

---

## Privacy / storage rules

- Payload repeat uses **SHA-256 hex fingerprint** of normalized message text
- **Do not** store raw message text, prompts, secrets, or tokens in spam tables or API responses
- `metadata` is sanitized via `sanitize_spam_metadata()`

---

## Verification

```bash
cd backend && .venv/bin/python -m pytest tests/test_e3_6_spam_policy.py tests/test_e3_6_spam_protection.py -q
cd backend && .venv/bin/python -m pytest tests/ -q
PYTHONPATH=backend python3 scripts/verify/e2_observability_verification.py --run-pytest
```

---

## Deployment notes

1. `alembic upgrade head` (through `0021`)
2. Restart backend
3. Leave `ALPSTEIN_AI_SPAM_PROTECTION_ENABLED=false`
4. After E3.5d + staging validation: enable in staging with `SPAM_PRODUCTION_SAFE_MODE=true` first

Ops runbook: [`../ops/ingress-spam-protection.md`](../ops/ingress-spam-protection.md)

---

## Risks / follow-up

- `adapter_fanout` bucket count is not fully race-safe (acceptable for `mark_suspicious` posture)
- `retry_abuse` / `replay_storm` derive counts from `replay_events` (read-only, non-atomic)
- Blocking actions require explicit staging validation before disabling production safe mode
- E3.5d concurrency test still open — blocks rate-limit flag enablement as well
