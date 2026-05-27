# Greeting orchestration MVP (done)

**Status:** Complete — review before deploy.

## Design

Option **B**: `GreetingPolicyService` inspects conversation history (no DB migration).

## Deliverables

- First contact / follow-up / soft return (24h) modes
- Language detection: message text → Telegram `language_code` in `raw_payload` → English
- Greeting rules in `task_instructions` (platform authority)
- Tests + `docs/architecture/greeting-orchestration-mvp.md`

## Operator note

Stale `messages` history can still dominate until a fresh conversation is used.
