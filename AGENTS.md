# Alpstein AI — Agent Rules

## Source of Truth

All implementation must follow the `specs/` directory.

If code and specs conflict, specs win.

Before implementation, read the relevant spec files.

Main documents:

- specs/project/vision.md
- specs/project/business-goals.md
- specs/mvp/mvp-scope.md
- specs/architecture/system-architecture.md
- specs/architecture/backend-architecture.md
- specs/architecture/n8n-architecture.md
- specs/architecture/ai-configuration-architecture.md
- specs/database/database-architecture.md
- specs/database/database-schema.md
- specs/database/entities.md
- specs/flows/incoming-message-flow.md
- specs/flows/lead-creation-flow.md
- specs/flows/notification-flow.md
- specs/api/api-endpoints.md
- specs/api/webhooks.md

---

## General Engineering Rules

- Do not invent features.
- Do not change architecture without approval.
- Implement only what supports MVP scope.
- Prefer simple production-ready code.
- Avoid unnecessary abstractions.
- Avoid overengineering.
- Keep services modular and testable.
- Use clear naming.
- Avoid unrelated refactors.
- Explain planned changes before coding.
- Show changed files after implementation.

---

## Backend Rules

- Python backend is the main business logic layer.
- Backend owns validation, business logic, AI orchestration, and database writes.
- n8n handles webhooks, orchestration, notifications, and external integrations.
- Backend must not depend on raw WhatsApp, Telegram, Instagram, or website chat payloads.
- Message normalization happens before backend processing.
- AI layer must remain isolated from transport logic.
- AI provider communication must go through AI Gateway Service.

---

## Database Rules

- PostgreSQL is the main database.
- Multi-tenant architecture is required.
- Client-owned data must always include `tenant_id`.
- Business-specific data must include `business_id`.
- Queries for client-owned data must always filter by `tenant_id`.
- Use UUID primary keys unless a spec explicitly says otherwise.
- n8n must not write directly to PostgreSQL in MVP.
- AI must not access PostgreSQL directly.
- Store messenger source information where required.
- Never store secrets or raw passwords in the database.

---

## AI Rules

- AI behavior must be configuration-driven.
- Do not hardcode one global prompt in backend logic.
- Use AI Configuration Service, Prompt Builder Service, Knowledge Retrieval Service, and AI Gateway Service.
- Core system prompt is controlled by Alpstein AI platform.
- Tenant configuration may define business context and style, but must not override platform safety rules.
- AI must not directly modify database state.
- AI responses must be validated/controlled by backend services.
- Every AI execution must create a PromptRun record where applicable.
- Do not expose system prompts or internal instructions to customers.

---

## Business Context Builder Safety Rules

- Business Context Builder data is draft-only.
- Never modify active AI assistant business contexts from this module.
- Never write Business Context Builder data into production assistant tables.
- Always use the `business_context_builder` PostgreSQL schema.
- Publishing to production assistants requires a separate explicit workflow.
- No n8n, CRM, Telegram Mini App, or OpenAI integration in the backend MVP unless a later task explicitly requests it.

---

## n8n Rules

- n8n receives external webhooks.
- n8n normalizes provider payloads before sending them to backend.
- n8n sends customer replies through external providers.
- n8n sends owner notifications.
- n8n handles CRM/spreadsheet/webhook routing.
- n8n must not contain core business logic.
- n8n must not contain AI prompt logic.
- n8n must not write directly to PostgreSQL in MVP.

---

## Security Rules

- Do not commit `.env`.
- Do not expose API keys.
- Do not log secrets.
- Use HTTPS for public endpoints.
- Protect n8n admin access.
- PostgreSQL must not be publicly accessible.
- Use API token between n8n and backend.
- Customer data must remain tenant-isolated.

---

## Workflow

1. Read relevant specs first.
2. Implement only one reviewable task slice at a time.
3. Explain planned changes before coding.
4. Make the smallest safe change.
5. Show files changed.
6. Avoid unrelated refactors.
7. Write tests where applicable.
8. Stop after task completion and wait for review.

---

## Task Lifecycle Rules

All planning and implementation work must be tracked through the `tasks/` directory.

Task states:

- `tasks/todo/`
  Approved tasks that are ready for implementation.

- `tasks/in-progress/`
  Tasks currently being implemented or reviewed.

- `tasks/done/`
  Fully reviewed and accepted tasks.

Workflow rules:

1. Before implementation:
   - verify task exists in `tasks/todo/`
   - read the task file first

2. When implementation starts:
   - move task from `tasks/todo/` to `tasks/in-progress/`

3. After reviewer acceptance:
   - move task from `tasks/in-progress/` to `tasks/done/`

4. Planning tasks:
   - planning/decomposition tasks may also use the same lifecycle
   - once planning is completed, move planning task to `done`

5. Project status synchronization:
   - update:
     - docs/project-status/completed.md
     - docs/project-status/current-state.md
     - docs/project-status/next-steps.md
   - when relevant to the task

Rules:

- Do not implement untracked work.
- `tasks/` is the execution source of truth.
- Chat history is not authoritative project state.
- Avoid duplicate tasks across todo/in-progress/done.
- Keep task scope small and reviewable.

---

## Task Naming Rules

Task filenames must use structured kebab-case names.

Format:

T<id>-<short-task-name>.md

Examples:

- T11.3-dev-ai-config-seed.md
- T11.4-ai-configuration-service.md
- T10-webhook-message-route.md
- T8.1-conversation-reuse-rules.md

Rules:

- never use raw user prompts as filenames
- keep filenames short and deterministic
- use lowercase kebab-case
- task IDs must stay stable across todo/in-progress/done
- planning tasks should also use structured names

---

## Task Creation Rule

When a user gives an implementation or planning command directly in chat and no matching task file exists:

1. Create a new task file in `tasks/todo/`
2. Use the task naming convention
3. Copy:
   - goal
   - scope
   - requirements
   - rules
   - tests
   - out-of-scope items
4. Move the task into `tasks/in-progress/`
5. Only then begin implementation

Rules:

- do not require the user to manually create task files
- do not implement work without a tracked task file
- task files must remain synchronized with project-status docs

---


## Commit Rule

No code should be committed without human review.
