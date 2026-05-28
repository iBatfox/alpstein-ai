# T-e1.4 — Multi-channel identity strategy (spec-only)

## Status

Done (spec-only)

## Goal

Define conservative identity reasoning across Telegram, Website Chat, and future channels before any real identity merge or CRM automation expansion.

## Delivered

- **`docs/architecture/multi-channel-identity-strategy.md`**
  - Canonical identity concepts (`external_user_id`, `external_conversation_id`, `visitor_id`, `session_id`)
  - Telegram identity strength rules (in-channel strong only)
  - Website pseudonymous identity rules and anonymous-first support
  - Anonymous -> identified transition rules
  - Optional PII handling (`name`, `email`, `phone`) with non-forcing merge policy
  - CRM linkage preparation strategy (no implementation)
  - Identity confidence levels and explainability requirements
  - Cross-channel ambiguity and explicit non-merge rules
  - Consent/privacy and metadata retention boundaries
  - Observability requirements for identity reasoning
  - Future-proofing matrix for WhatsApp/Instagram/forms/CRM webhook

- **`docs/project-status/current-state.md`**, **`next-steps.md`**

## Constraints honored

- Documentation/spec only
- No backend code, n8n workflow, DB migration, CRM automation, or endpoint changes
- No Telegram runtime changes
- No Website Chat dependency on CRM identity
- No assumption that email/phone is always present
- Identity matching strategy remains conservative and explainable

## Acceptance

PASS:

- E1.4 identity strategy documented with clear non-merge guardrails
- Aligned with E1.2 normalized contract and E1.3 website-chat architecture
- Future CRM/linkage path prepared without implementation
- Project status updated

## Handoff

| Area | Next task type |
|------|----------------|
| Website Chat runtime | E1.5+ implementation planning with channel-scoped identity preserved |
| CRM linkage | Separate design and approval workflow before any merge logic |
| Backend | Optional non-merge confidence metadata (future, explicit approval) |
