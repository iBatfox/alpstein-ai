**Doc status:** draft  
**Tier:** project-status/historical (pending move)  
**Canonical anchor:** [`canonical-runtime-architecture.md`](../architecture/canonical-runtime-architecture.md) §9 — ATTR-2 **implemented**; persistence **planned**

# Channel source attribution — design index

**Status:** ATTR-2 complete (Pydantic) — 2026-05-25  
**Canonical:** [`specs/architecture/channel-source-attribution.md`](../../specs/architecture/channel-source-attribution.md)

**Summary:** Normalized webhook accepts optional `source`, `attribution`, `message.client`, and prefixed `message.external_conversation_id`. `channel` remains the Alpstein routing key. No persistence in ATTR-2.

**ATTR-2 delivered:** `backend/app/schemas/webhook_attribution.py`, `backend/tests/test_webhook_attribution_schemas.py`.

**Next implementation:** **ATTR-3** (persistence to `conversations` / `messages.metadata`) — may start.

**Telegram:** backward compatible — omit new objects until adapters send them.
