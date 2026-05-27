**Doc status:** runtime-derived  
**Tier:** conversational/policies (pending move)  
**Canonical anchor:** [`canonical-runtime-architecture.md`](canonical-runtime-architecture.md) §6 — backend **done**, n8n ops **partial**

# Pre-sales contact ownership

**Status:** Active (2026-05-24)

## Split of responsibility

| Layer | Owns | Must not |
|-------|------|----------|
| **Backend prompts** | Behavior: when to share contacts, ask for customer phone/email, name preservation | Hardcoded personal names, phones, emails |
| **Operator / workflow** | Runtime contact values in `operator_business_context` (n8n Set node) | Prompt assembly, OpenAI calls |
| **Tenant DB** (future) | Optional `business_contact` profile fields | Override platform safety |

## Backend rules (summary)

- Share business contact details only when the customer asks or shows implementation interest **and** details appear in **OPERATOR BUSINESS NOTES** (or other reference data).
- If missing, ask the customer to leave phone or email — **do not invent** contacts.
- **Do not translate** personal names, emails, phones, URLs, CRM names, or product names; copy exactly from reference data.

## Where to put contact data (ops)

Add to the n8n **Add Business Context** Set node (`operator_business_context`), for example:

```text
Business contact (share only when customer asks):
Name: …
Phone: …
Email: …
```

Preserve exact spelling; the model is instructed not to translate these strings.

See also: [`operator-business-context-n8n.md`](operator-business-context-n8n.md), [`conversation-intent-policy-mvp.md`](conversation-intent-policy-mvp.md).
