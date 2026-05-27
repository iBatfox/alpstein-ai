# Alpstein Reviewer — Spec Reference

Read only sections relevant to the change under review.

## Source of truth

| Document | Review when |
|----------|-------------|
| [AGENTS.md](../../../AGENTS.md) | Every review |
| [specs/mvp/mvp-scope.md](../../../specs/mvp/mvp-scope.md) | Scope, in/out of MVP, success criteria |
| [specs/project/vision.md](../../../specs/project/vision.md) | Product direction disputes |
| [specs/architecture/system-architecture.md](../../../specs/architecture/system-architecture.md) | System boundaries |
| [specs/architecture/backend-architecture.md](../../../specs/architecture/backend-architecture.md) | Backend layers, services, structure |
| [specs/architecture/n8n-architecture.md](../../../specs/architecture/n8n-architecture.md) | n8n workflows and responsibilities |
| [specs/architecture/ai-configuration-architecture.md](../../../specs/architecture/ai-configuration-architecture.md) | AI services, prompts, config |
| [specs/database/database-architecture.md](../../../specs/database/database-architecture.md) | Who may access DB |
| [specs/database/database-schema.md](../../../specs/database/database-schema.md) | Columns, types, constraints |
| [specs/database/entities.md](../../../specs/database/entities.md) | Entity lifecycle and rules |
| [specs/api/api-endpoints.md](../../../specs/api/api-endpoints.md) | REST contracts |
| [specs/api/webhooks.md](../../../specs/api/webhooks.md) | Normalized webhook payloads |
| [specs/flows/incoming-message-flow.md](../../../specs/flows/incoming-message-flow.md) | Message pipeline order |
| [specs/flows/lead-creation-flow.md](../../../specs/flows/lead-creation-flow.md) | Lead create/update/dedup |
| [specs/flows/notification-flow.md](../../../specs/flows/notification-flow.md) | Owner notification flags |

## Architecture quick checklist

- [ ] Backend owns validation, business logic, AI orchestration, DB writes
- [ ] n8n normalizes payloads; no core business logic or prompts in n8n
- [ ] No raw channel payloads consumed by backend services
- [ ] AI isolated from transport; Gateway-only provider calls
- [ ] No n8n or AI direct PostgreSQL writes (MVP)
- [ ] API token between n8n and backend where applicable
- [ ] HTTPS / no public PostgreSQL (deployment assumptions)
- [ ] No provider-specific transport fields leaked into backend contracts
- [ ] Tenant AI configuration cannot override platform safety/system rules

## Database quick checklist

- [ ] Schema matches `database-schema.md`
- [ ] Entity behavior matches `entities.md`
- [ ] `tenant_id` on client-owned data; `business_id` where business-scoped
- [ ] All queries filter by `tenant_id`
- [ ] UUID primary keys unless spec exception
- [ ] No secrets in DB or logs
- [ ] `prompt_runs` recorded for AI executions where applicable

## Spec drift checks

- [ ] New fields reflected in schema/contracts/flows consistently
- [ ] Endpoint changes reflected in api-endpoints.md and webhooks.md
- [ ] New entities reflected in entities.md and database-schema.md
- [ ] Response shape changes reflected across backend and n8n references

## MVP scope quick checklist

**Included (should be supported):**

- WhatsApp Cloud API + test webhook
- AI customer replies with business context and escalation
- Conversations and messages stored
- Leads with dedup/active lead updates
- Owner notifications (e.g. Telegram)
- Tenant AI configuration (not overriding platform safety)
- Manual tenant/business onboarding APIs

**Excluded (flag if implemented without approval):**

- Dashboard, billing, Stripe
- Vector DB, semantic RAG, embeddings, AI memory
- Redis/queues, async workers, microservices, Kubernetes
- Voice, phone, mobile app
- Enterprise RBAC, advanced CRM sync, multi-region
- n8n → PostgreSQL writes

## Tenant isolation spot checks

Search the diff for:

- `SELECT` / `update` / `delete` without `tenant_id` in WHERE
- Endpoints accepting `tenant_id` from client without server-side resolution
- Global queries on `messages`, `leads`, `conversations`, `customers`
- Shared caches or singletons keyed only by `conversation_id`
- webhook/message processing without `external_message_id` dedup handling

## Edge cases by flow

| Flow | Typical edges |
|------|----------------|
| Incoming message | Unknown tenant/channel; duplicate `external_message_id`; conversation closed |
| AI reply | Empty/malformed JSON; timeout; policy violation; no knowledge match |
| Lead | Duplicate customer; inactive lead; missing `conversation_id` link |
| Notification | `notify_owner` true but no lead; owner channel misconfigured |
| Migrations | Nullable `tenant_id` on existing rows; enum value not in spec |

## Overengineering signals

- New base classes or generic pipelines for one call site
- Repository interfaces with a single implementation
- Feature flags or plugin registry for MVP-only behavior
- Config files or env vars not in spec
- Parallel “v2” APIs without spec update
- Generic plugin/event systems without an active MVP use case

## MVP demonstration path (regression sanity)

End-to-end scenario from [mvp-scope.md](../../../specs/mvp/mvp-scope.md):

```text
Customer WhatsApp message → AI reply → conversation stored → lead created → owner Telegram notification
```

If the change touches this path, confirm each step still holds logically (even without running E2E).
