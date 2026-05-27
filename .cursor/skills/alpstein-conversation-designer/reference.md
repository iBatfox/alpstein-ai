# Conversation Designer — Reference

Read only the sections relevant to the current design task.

## Governing specs

| Document | Use when |
|----------|----------|
| [ai-configuration-architecture.md](../../../specs/architecture/ai-configuration-architecture.md) | Config layers, platform vs tenant control, entities |
| [prompt-builder-rules.md](../../../specs/architecture/prompt-builder-rules.md) | §1–§8 ordering, truncation, operator context placement |
| [incoming-message-flow.md](../../../specs/flows/incoming-message-flow.md) | Where AI config, history, and prompt build sit in the pipeline |
| [entities.md](../../../specs/database/entities.md) | Field-level entity definitions |
| [mvp-scope.md](../../../specs/mvp/mvp-scope.md) | In/out of MVP |

## Architecture behavior docs (project)

| Document | Topic |
|----------|-------|
| [conversation-intent-policy-mvp.md](../../../docs/architecture/conversation-intent-policy-mvp.md) | Intent enum, heuristics, §2 refactor, behavior tables |
| [greeting-orchestration-mvp.md](../../../docs/architecture/greeting-orchestration-mvp.md) | Lifecycle modes, language detection |
| [pre-sales-contact-ownership.md](../../../docs/architecture/pre-sales-contact-ownership.md) | Contact values vs contact behavior |
| [technical-pre-sales-behavior-mvp.md](../../../docs/architecture/technical-pre-sales-behavior-mvp.md) | Pre-sales persona goals |
| [operator-business-context-n8n.md](../../../docs/architecture/operator-business-context-n8n.md) | Runtime operator notes field |

## Prompt section quick map

```text
1. platform_system          → prompt_templates.system_prompt
2. task_instructions        → registry + core charter + ONE intent slice + greeting (optional)
3. tenant_business_context  → tenant_business_profiles + operator_business_context
4. tenant_behavior          → tenant_ai_profiles
5. channel_rules            → tenant_channel_settings[channel]
6. knowledge                → tenant_knowledge_sources (retrieved snippets)
7. conversation_history     → last 10–20 messages
8. current_customer_message → message.text
```

## MVP intent enum (Alpstein demo persona)

| Intent | Typical trigger |
|--------|-----------------|
| `social_greeting` | Pure hello/thanks/bye, no technical/pricing tokens |
| `technical_interest` | Default; product/how/integration questions |
| `implementation_interest` | Buy, deploy, start, book a call |
| `pricing_interest` | Price, cost, budget keywords |
| `unsupported_system` | Named CRM/ERP + support/feasibility framing |
| `confused_customer` | “Don’t understand”, vague contradiction |
| `off_topic` | Clearly outside scope (conservative list) |

Detection: priority order, first match wins; short replies may inherit from previous customer message.

## Greeting lifecycle modes

| Mode | When | Assistant behavior |
|------|------|-------------------|
| `first_contact` | No prior `ai` messages | Full greet + intro + how can I help |
| `follow_up` | Prior `ai` messages exist | No full intro; answer directly |
| `soft_return` | Prior `ai` + gap ≥ 24h | Short greeting; no full intro |

Language: detect from current message → Telegram `language_code` → English. Supported: DE, EN, RU, FR, IT, ES, UK.

## Config entity — design fields

### tenant_business_profiles

Design content for: business name/type, services, prices, region, hours, contact info (factual), limitations, audience.

Role in prompt: **§3 reference data**. Not instructions.

### tenant_ai_profiles

Design content for: tone, language, response_style, questions_to_ask, handoff_enabled, fallback_response, prohibited_promises (as data hints).

Role in prompt: **§4 reference data**. Does not replace §2 intent or greeting rules.

### tenant_knowledge_sources

Design content for: FAQ entries, policies, service descriptions, booking rules — chunked for retrieval.

Role in prompt: **§6**. Avoid duplicating full §2 behavior rules in knowledge text.

### tenant_channel_settings

Design content for: response length, formality, channel-specific formatting — not provider API details.

Role in prompt: **§5**.

## §2 assembly order (inside task_instructions)

```text
[core task from PLATFORM_TASK_REGISTRY]
[core charter — short, always on]
[exactly ONE intent_behavior slice]
[greeting block if GreetingPolicy present]
```

## Size budget (MVP soft caps)

| Block | Target |
|-------|--------|
| Core charter | ~1,200 chars |
| Active intent slice | ~900 chars |
| Total §2 | ~3,500 chars soft cap |

Net §2 must shrink vs monolithic appendix when refactoring.

## Detection spec template

```markdown
### Priority order (first match wins)

| Priority | Intent | Heuristic summary |
|----------|--------|-------------------|
| 1 | … | … |

### Short-reply inheritance

If current message ≤ 4 words or ≤ 30 chars and previous customer message set:
- Re-run priorities … on previous message only
- Else default …

### Outputs

- intent (enum)
- matched_rule (string, for tracing)
- used_previous_message (bool)
```

## Acceptance test categories

1. **Detection unit tests** — one expected intent per message (+ short-reply cases)
2. **Prompt composition** — exactly one intent block; legacy appendix absent
3. **Negative fragments** — pricing slice has no fake currency; social has no CRM list
4. **Regression** — greeting tests unchanged; operator context not duplicated in §2

## Skill boundaries (quick)

| Need | Skill |
|------|-------|
| Write behavior spec | **alpstein-conversation-designer** |
| Implement ConversationIntentService / prompt slices | alpstein-ai-integration-engineer |
| Wire orchestration, Langfuse metadata | alpstein-backend-engineer |
| Webhook operator_business_context contract | alpstein-api-designer |
| n8n Set node for operator context | alpstein-n8n-integration-engineer |
| Migration/seed for profile tables | alpstein-database-architect |
