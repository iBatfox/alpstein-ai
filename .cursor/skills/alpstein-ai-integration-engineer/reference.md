# Alpstein AI Layer — Reference

Read only what applies to the current task. Do not use this skill for n8n or messenger transport specs.

## Mandatory reads

| Document | Use for |
|----------|---------|
| [AGENTS.md](../../../AGENTS.md) | AI rules, no AI DB writes, Gateway-only provider calls |
| [specs/architecture/ai-configuration-architecture.md](../../../specs/architecture/ai-configuration-architecture.md) | Layers, four services, safety, flow, `prompt_runs` |
| [specs/mvp/mvp-scope.md](../../../specs/mvp/mvp-scope.md) | MVP AI config, knowledge, PromptRun requirements |

## Supporting database specs

| Document | Use for |
|----------|---------|
| [specs/database/entities.md](../../../specs/database/entities.md) | AI profiles, knowledge, templates, PromptRun |
| [specs/database/database-schema.md](../../../specs/database/database-schema.md) | Column definitions |

For end-to-end webhook sequencing (who calls the AI chain), see incoming-message flow only as **context** — implement transport in backend-engineer / n8n skills, not here.

## Service map (backend)

```text
ai_configuration_service.py   # load profiles, channel settings, templates
knowledge_retrieval_service.py  # tenant/business snippets
prompt_builder_service.py       # merge platform rules, tenant config, knowledge, history, and task context into provider-ready messages
ai_gateway_service.py           # provider HTTP only
```

Orchestrator (outside this skill’s ownership): invokes chain, writes `messages` + `prompt_runs`.

## Configuration entities

```text
tenant_business_profiles
tenant_ai_profiles
tenant_knowledge_sources
tenant_channel_settings
prompt_templates
prompt_runs
```

## prompt_runs (MVP)

```text
tenant_id, business_id, conversation_id, message_id
prompt_template_id, prompt_version, model
input_tokens, output_tokens, result, error, created_at
```

Lifecycle: `created` → `completed` | `failed`. Queries always include `tenant_id`.

## Internal prompt block layout

From ai-configuration-architecture.md §14 — structure only; content from DB/templates:

```text
[CORE SYSTEM PROMPT]
[TENANT BUSINESS CONTEXT]
[TENANT BEHAVIOR CONFIG]
[CHANNEL RULES]
[RELEVANT KNOWLEDGE]
[CONVERSATION HISTORY]
[TASK]
```

## Conversation context (MVP)

- Window: last 10–20 messages (architecture default).
- Inputs: `conversation_id`, `tenant_id`, `business_id`, `channel`, current task.
- Output: ordered turns for Prompt Builder — not raw provider payloads.

## Gateway environment (names only)

```text
OPENAI_API_KEY
OPENAI_MODEL
AI_REQUEST_TIMEOUT
```

Future providers stay behind Gateway interface.

## Forbidden (quick reference)

1. Hardcoded global prompts  
2. AI services writing to PostgreSQL  
3. Direct SQL/ORM access inside Prompt Builder or AI Gateway  
4. Tenant config replacing platform safety / core system prompt  
5. Prompt assembly in n8n  

## Skill boundaries

| alpstein-ai-integration-engineer | alpstein-n8n-integration-engineer |
|----------------------------------|-----------------------------------|
| AI services, prompts, knowledge, Gateway, PromptRun, context for AI | Webhooks, normalize, HTTP to backend, replies, notify |
| Provider-independent AI orchestration | Provider-specific send/receive nodes |
