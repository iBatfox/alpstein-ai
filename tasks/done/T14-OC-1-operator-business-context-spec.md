# T14-OC-1 — Spec `operator_business_context` webhook field

**Status:** done (2026-05-25)

**Goal:** Document optional top-level `operator_business_context` on `POST /api/v1/webhook/message` for n8n-editable business notes (no runtime change).

**Specs updated:**

- `specs/api/webhooks.md` — §4.2, §7 field definition, precedence, security, n8n placement, T14-OC-2 gate
- `specs/api/api-endpoints.md` — request example + cross-ref
- `specs/architecture/prompt-builder-rules.md` — §4.5 overlay; section 3 source; precedence
- `specs/flows/incoming-message-flow.md` — Steps 4, 6, 12

**Next:** **T14-OC-2** — Pydantic + Prompt Builder wire (backend may start).

**Not in scope:** n8n workflow (T14-OC-3), DB migration, OpenAI in n8n.
