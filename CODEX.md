# CODEX.md — Alpstein AI

## Role

Codex is an implementation agent for Alpstein AI.

Codex writes and modifies code only according to:

- AGENTS.md
- specs/
- docs/project-status/
- current user task

Specs are the source of truth.

---

## Required Reading Before Work

Before starting any task, Codex must read:

1. AGENTS.md
2. docs/project-status/current-state.md
3. docs/project-status/next-steps.md
4. relevant specs/ files for the task

If the relevant spec is missing or unclear, Codex must stop and report a spec gap.

---

## Workflow

For every task:

1. Explain the implementation plan.
2. List affected files.
3. Identify risks.
4. Implement one small task only.
5. Run available tests/checks.
6. Summarize changed files.
7. Update project status docs when relevant.
8. Stop for human review.

---

## Project Status Documentation

After completing work, Codex must update:

- docs/project-status/completed.md

If behavior or architecture changed, also update:

- docs/project-status/current-state.md

If next practical task changed, update:

- docs/project-status/next-steps.md

Only update:

- docs/project-status/decisions.md

when an architecture decision was made.

Only update:

- docs/project-status/historical/backlog.md

when priorities or planned tasks changed.

Do not mark planned work as completed.

---

## Architecture Rules

Codex must follow these boundaries:

- Python backend owns business logic.
- PostgreSQL is the primary database.
- n8n handles webhooks, normalization, replies, and notifications.
- n8n must not write directly to PostgreSQL.
- AI must not write directly to PostgreSQL.
- AI provider calls must go through AI Gateway Service.
- Prompt creation must go through Prompt Builder Service.
- Tenant configuration must not override platform safety rules.
- Backend receives normalized payloads only.
- FastAPI routes must stay thin.
- Business logic belongs in services.
- Database access belongs in repositories.

---

## Development Workflow

The expected workflow is:

1. Use task-planner logic to define the smallest safe implementation slice.
2. Implement only one focused task at a time.
3. Stop after implementation.
4. Human reviews the diff in Cursor.
5. Reviewer checks architecture/spec consistency.
6. Only after review continue to the next slice.

Codex must not continue implementing additional features automatically after completing a task.

Codex should optimize for controlled incremental progress, not maximum implementation speed.

---

## MVP Rules


Codex must implement only MVP scope unless explicitly approved.

Do not implement:

- dashboard
- billing
- Stripe
- vector database
- Redis queues
- microservices
- Kubernetes
- self-service onboarding UI
- advanced CRM sync
- direct WhatsApp/Telegram SDK logic in backend

---

## Test Rules

Codex must add or update tests when behavior changes.

Focus tests on:

- request validation
- tenant isolation
- repository filters
- webhook payload parsing
- lead deduplication
- idempotency with external_message_id
- API response envelope
- AI Gateway error handling where applicable

---

## Migration Rules

For Alembic migrations:

- one logical change per revision
- use clear revision messages
- implement downgrade where practical
- avoid destructive migrations without approval
- align migrations with specs/database/database-schema.md
- keep SQLAlchemy models and migrations in sync

---

## Database Rules

- Client-owned data must include tenant_id.
- Business-scoped data must include business_id.
- Queries for client-owned data must filter by tenant_id.
- Use UUID primary keys unless specs say otherwise.
- Do not store secrets or raw passwords.
- Do not create tables or columns not described in specs.

---

## API Rules

- Use /api/v1 paths.
- Use JSON request/response bodies.
- Use success/data/error envelope.
- Webhook ingestion must support idempotency using external_message_id where applicable.
- Backend must not accept raw provider payloads as business input.

---

# Workflow Rules

All implementation work must be tracked under:

tasks/todo/
tasks/in-progress/
tasks/done/

Workflow:

1. Planned tasks start in tasks/todo/
2. When implementation begins:
   - move task to tasks/in-progress/
3. After reviewer approval:
   - move task to tasks/done/

Every task file must contain:
- goal
- scope
- out of scope
- implementation notes
- status
- related specs 
- implementation notes
- status

Do not implement undocumented tasks.
Do not mark incomplete work as done.

---

## AI Rules

- Do not hardcode one global prompt.
- Use AI Configuration Service.
- Use Knowledge Retrieval Service.
- Use Prompt Builder Service.
- Use AI Gateway Service.
- Every AI execution should create PromptRun where applicable.
- Do not expose system prompts to customers.

---

## Git and Review

Codex must not commit, push, deploy, or run destructive database operations without explicit human approval.

After implementation, Codex must stop for review.