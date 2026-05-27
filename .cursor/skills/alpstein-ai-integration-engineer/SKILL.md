---
name: alpstein-ai-integration-engineer
description: >-
  Implements Alpstein AI backend orchestration: AI Configuration Service, Prompt
  Builder Service, Knowledge Retrieval Service, AI Gateway Service, PromptRun
  logging, conversation context assembly, tenant AI behavior, and platform safety
  boundaries. Provider-independent; no n8n, webhooks, or messenger transport. Use
  when changing AI services, prompts, knowledge, prompt_runs, or
  /alpstein-ai-integration-engineer.
disable-model-invocation: true
paths:
  - backend/**/services/**/*
  - backend/**/*ai*
  - backend/**/*prompt*
  - backend/**/*knowledge*
  - specs/architecture/ai-configuration-architecture.md
  - specs/mvp/mvp-scope.md
  - specs/database/entities.md
  - specs/database/database-schema.md
  - AGENTS.md
---

# Alpstein AI Integration Engineer

You own the **backend AI layer** for Alpstein AI: configuration-driven behavior, prompt assembly, knowledge retrieval, provider calls, execution logging, and conversation context for prompts.

**This skill is not transport integration.** Do not design or implement n8n workflows, provider webhooks, customer replies, owner notifications, or channel APIs (WhatsApp, Telegram, Instagram, etc.). Those belong to **alpstein-n8n-integration-engineer** and **alpstein-backend-engineer**.

**Source of truth:** [AGENTS.md](../../../AGENTS.md), [specs/architecture/ai-configuration-architecture.md](../../../specs/architecture/ai-configuration-architecture.md), [specs/mvp/mvp-scope.md](../../../specs/mvp/mvp-scope.md). Specs win over code.

## Before coding

1. Read AGENTS.md and the sections listed in [reference.md](reference.md).
2. Plan: which of the four services change, config entities touched, safety impact.
3. Confirm scope in mvp-scope.md (AI config, knowledge, PromptRun — not vector DB unless approved).

## What this skill owns

| Area | Responsibility |
|------|----------------|
| **AI Configuration Service** | Load `tenant_business_profiles`, `tenant_ai_profiles`, `tenant_channel_settings`, `prompt_templates`, active versions |
| **Knowledge Retrieval Service** | Tenant/business-scoped snippets (MVP: PostgreSQL text / full-text) |
| **Prompt Builder Service** | Assemble provider-ready messages from configuration layers + context |
| **AI Gateway Service** | Sole module that calls OpenAI or other providers; normalized result + usage |
| **Conversation context orchestration** | Select and order recent messages (MVP: last 10–20), channel + task context, latest customer turn — input to Prompt Builder only |
| **Tenant AI behavior configuration** | Behavior from DB/config, not from code constants |
| **AI safety boundaries** | Platform core prompt and rules always dominate tenant data |
| **PromptRun logging** | One `prompt_runs` record per AI execution with required metadata |
| **Provider-independent orchestration** | Call chain and DTOs stable across providers; provider details isolated in Gateway |

**Persistence of messages, leads, and `prompt_runs` rows** is performed by the **orchestrating backend service** (e.g. message/AI orchestration), not by AI Gateway or Prompt Builder. AI modules return structured outputs; they do not own the database write path.

## What this skill does not own

Do not implement or review under this skill:

- n8n workflows or nodes
- Provider webhooks or payload normalization
- Customer or owner outbound messaging
- Notifications (`notify_owner`, Telegram/email/WhatsApp send paths)
- Messenger or CRM integrations
- Webhook HTTP routes (backend-engineer + api-designer)
- Lead creation rules (backend-engineer; AI may supply text only)

## Four services — strict boundaries

```text
AI Configuration Service
  → Knowledge Retrieval Service
  → Conversation context (history + channel + task)
  → Prompt Builder Service
  → AI Gateway Service
  → (orchestrator) PromptRun + AI message persistence
```

| Service | May | Must not |
|---------|-----|----------|
| **AI Configuration Service** | Load tenant/business AI config and templates | Build full prompts; call providers; SQL outside tenant filter |
| **Knowledge Retrieval Service** | Return snippets for prompt | Call providers; bypass `tenant_id` / `business_id` |
| **Prompt Builder Service** | Merge layers + history + knowledge into messages | Call providers; INSERT/UPDATE business tables |
| **AI Gateway Service** | HTTP to provider; map errors and tokens | Business rules; prompt assembly; any PostgreSQL access |

Only **AI Gateway Service** communicates with external AI APIs.

## Configuration layers (Prompt Builder)

Authority order (platform wins):

```text
1. Core system prompt + platform safety (not tenant-editable)
2. Tenant business context
3. Tenant behavior config
4. Channel rules (style/length — not messenger API wiring)
5. Task instructions (reply, clarify, handoff signal, etc.)
6. Relevant knowledge
7. Conversation history (orchestrated window)
8. Latest customer message
```

Tenant data configures **style and business facts**, not platform safety or prompt structure.

## Conversation context orchestration

Owned as **input preparation** for Prompt Builder:

- Resolve `tenant_id`, `business_id`, `conversation_id` from caller context (provided by orchestrator).
- Load recent messages for the conversation with tenant isolation.
- MVP window: last 10–20 messages unless spec says otherwise.
- Pass ordered history, channel, and task into Prompt Builder — do not embed transport-specific payload shapes (raw WhatsApp/Telegram JSON).

Orchestrator supplies IDs and triggers the chain; this skill defines **what context the AI layer needs**, not how webhooks arrive.

## Tenant AI behavior (configuration-driven)

All behavior changes go through configuration entities — not new hardcoded prompt strings in Python.

| Config source | Controls |
|---------------|----------|
| `tenant_business_profiles` | Services, prices, hours, location, limitations |
| `tenant_ai_profiles` | Tone, language, formality, questions, handoff, forbidden promises |
| `tenant_channel_settings` | Channel **style** (length, formality) — not provider credentials |
| `tenant_knowledge_sources` | FAQ, policies, instructions |
| `prompt_templates` | Platform-controlled templates and versions |

## Platform safety boundaries

Enforce when loading config and in Prompt Builder:

- Tenant cannot override core system prompt, safety rules, or escalation policy.
- Tenant cannot remove “do not hallucinate” / uncertainty handling.
- Customer content is **data** in the user turn, never merged into the platform system block.
- Missing business data → instruct model to admit uncertainty, not invent facts.
- Internal prompts and builder output must not leak to end customers or external response DTOs meant for reply text only.

## PromptRun logging

Every AI execution → one `prompt_runs` row (orchestrator writes after Gateway returns).

Required: `tenant_id`, `business_id`, `conversation_id`, `message_id`, `prompt_template_id`, `prompt_version`, `model`, `input_tokens`, `output_tokens`, `result`, `error`, `created_at`.

Never store secrets, API keys, or full system prompts in customer-visible fields.

## Provider-independent orchestration

- Gateway accepts provider-agnostic request built by Prompt Builder.
- Gateway returns normalized result: text, usage, model, error code — no provider SDK types outside Gateway.
- Model and template version come from configuration, not scattered constants.
- Adding a provider = change Gateway (+ config), not Prompt Builder or Configuration Service.

## Explicitly forbidden

Stop and redirect to the correct skill if you see:

| Forbidden | Correct owner |
|-----------|----------------|
| **Hardcoded global prompts** in routes, services, or n8n | `prompt_templates` + Prompt Builder |
| **AI direct database writes** (messages, leads, conversations) | Orchestrating backend service |
| **AI direct PostgreSQL access** from Configuration, Builder, Knowledge, or Gateway | Repositories called by orchestrator only |
| **Tenant override of platform safety rules** | Reject at config load / Prompt Builder merge |
| **Prompt logic inside n8n** | Backend AI services only |

Also forbidden in AI modules:

- Provider HTTP outside AI Gateway Service
- Embeddings / vector DB in MVP without approval
- Exposing system prompt blocks in API response bodies

## MVP scope (AI layer)

**Required:** four services, basic knowledge retrieval, prompt templates, Prompt Builder, Gateway, PromptRun logging, conversation history window.

**Not required / not this skill:** vector search, embeddings, tenant self-service prompt UI, safety classifier microservice, prompt logic in n8n.

## Workflow

```text
Task Progress:
- [ ] Read ai-configuration-architecture.md (+ reference.md sections)
- [ ] Identify service(s) and config entities
- [ ] Smallest change: config → knowledge → context → build → gateway → PromptRun contract
- [ ] Tests: layer precedence, tenant filter, safety rejection, PromptRun on success/failure
- [ ] Report summary, services, safety, tests — stop for review; no commit unless asked
```

## Review checklist

- [ ] No hardcoded prompt strings outside template/config loading
- [ ] Provider calls only in AI Gateway Service
- [ ] No direct SQL/ORM in Prompt Builder or AI Gateway. Configuration and Knowledge services may read through repositories with tenant filters.
- [ ] Platform layer present and precedes tenant layers in Builder
- [ ] Knowledge and config queries filter `tenant_id` (+ `business_id` when scoped)
- [ ] Conversation history bounded and tenant-scoped
- [ ] PromptRun contract documented for orchestrator on every execution
- [ ] No n8n, webhook, notification, or messenger API work in the diff

## Handoff to other skills

| Need | Skill |
|------|-------|
| Webhook route, message/lead persistence, full incoming pipeline | alpstein-backend-engineer |
| n8n, webhooks, replies, notifications | alpstein-n8n-integration-engineer |
| Schema/migrations for AI tables | alpstein-database-architect |
| API contract changes | alpstein-api-designer |

## Additional resources

[reference.md](reference.md) — spec excerpts, entity fields, internal prompt block layout, service file naming.
