# Alpstein AI — Database Entities

## 1. Purpose

This document describes the business meaning, lifecycle, and rules of the main database entities in Alpstein AI.

While `database-schema.md` defines tables and fields, this document explains what each entity means in the product.

The purpose is to ensure that backend logic, AI logic, n8n workflows, and future frontend development understand the same business model.

---

# 2. Entity Overview

## Core MVP entities

```text
Tenant
Business
Customer
Conversation
Message
Lead
DatabaseConnection
````

## AI configuration entities

```text
TenantBusinessProfile
TenantAIProfile
TenantKnowledgeSource
TenantChannelSetting
PromptTemplate
PromptRun
```

## Future entities

```text
User
Integration
Subscription
AuditLog
Event
```

---

# 3. Tenant

## Meaning

A tenant represents the owner of data inside Alpstein AI.

Usually, a tenant is a company or business owner who uses Alpstein AI.

In MVP:

```text
1 tenant = 1 business
```

Future versions may support:

```text
1 tenant = multiple businesses
```

Example:

```text
Tenant: Restaurant Group AG
├── Business: Zurich Branch
├── Business: St. Gallen Branch
└── Business: Appenzell Branch
```

---

## Responsibilities

Tenant groups and isolates all client-owned data:

* businesses;
* customers;
* conversations;
* messages;
* leads;
* AI profiles;
* knowledge sources;
* prompt runs;
* database connections.

---

## Lifecycle

```text
created → active → inactive / suspended
```

---

## Rules

* Every business must belong to a tenant.
* Every client-owned record must include `tenant_id`.
* Tenant data must never mix with another tenant.
* All tenant queries must filter by `tenant_id`.

---

# 4. Business

## Meaning

A business represents a specific company, branch, restaurant, barbershop, or service provider.

Examples:

```text
Barbershop Alpstein
Shawarma Shop St. Gallen
Restaurant Appenzell
```

A business belongs to one tenant.

---

## Responsibilities

Business defines operational context:

* business type;
* contact information;
* working hours;
* timezone;
* storage mode;
* communication channels.

Business itself should remain lightweight.

Detailed AI-related context belongs in:

```text
TenantBusinessProfile
TenantAIProfile
```

---

## Lifecycle

```text
created → active → inactive / suspended
```

---

## Rules

* Business belongs to exactly one tenant.
* Business may have many customers.
* Business may have many conversations.
* Business may have many leads.
* Business-specific data must filter by `business_id`.

---

## Important Notes

`external_id` is used by:

* n8n;
* webhooks;
* external integrations.

Example:

```text
demo_barbershop_001
```

---

# 5. Customer

## Meaning

A customer is an end user who communicates with a business.

Channels may include:

* WhatsApp;
* Telegram;
* Instagram;
* Website Chat;
* future channels.

---

## Responsibilities

Customer stores:

* identity;
* phone;
* email;
* preferred language;
* external provider IDs;
* relation to business.

---

## Lifecycle

```text
created → active → updated → archived
```

---

## Rules

* Customer belongs to one tenant.
* Customer belongs to one business.
* Customer may have many conversations.
* Customer may have many leads.

---

## Identity Rule

MVP identity rule:

```text
business_id + phone = unique customer
```

---

# 6. Conversation

## Meaning

A conversation represents a communication thread between customer and business AI/human.

A conversation groups multiple messages.

---

## Responsibilities

Conversation stores:

* channel;
* state;
* customer relation;
* AI activity state;
* last activity time;
* current lead status.

---

## Lifecycle

```text
open
↔ waiting_for_customer
↔ waiting_for_owner
→ closed
→ archived
```

Statuses are not a strict linear state machine in MVP: a conversation may move between `open`, `waiting_for_customer`, and `waiting_for_owner` while the thread remains active. `closed` and `archived` are terminal for new customer traffic.

Allowed values (see [database-schema.md](database-schema.md)):

```text
open
waiting_for_customer
waiting_for_owner
closed
archived
```

---

## Rules

* Conversation belongs to one tenant.
* Conversation belongs to one business.
* Conversation belongs to one customer.
* Conversation may contain many messages.
* Conversation may create one or more leads.
* Conversation history is part of AI context.

---

## Incoming message reuse

When a normalized incoming message arrives (see [incoming-message-flow.md](../flows/incoming-message-flow.md)), the backend resolves the conversation using:

```text
tenant_id + business_id + customer_id + channel
```

### Reusable for new customer messages

```text
open
waiting_for_customer
waiting_for_owner
```

If a matching conversation exists with any of these statuses, the incoming message **must** be stored on that conversation. The backend **must not** create a second active conversation for the same scope.

### Not reusable

```text
closed
archived
```

Customer messages **must not** be appended to `closed` or `archived` conversations. The backend **must** create a new conversation with `status = open` instead.

### Multiple matches

If more than one reusable conversation exists for the same scope, select one deterministically (latest `last_message_at`, then latest `created_at`) and treat duplicates as exceptional data, not as a signal to start another thread.

---

## AI Activity

`is_ai_active`

Controls whether AI is allowed to continue responding automatically.

Example:

```text
true  → AI responds automatically
false → conversation handled manually
```

---

# 7. Message

## Meaning

A message is a single communication unit inside a conversation.

Messages may come from:

* customer;
* AI;
* owner;
* system.

---

## Responsibilities

Message stores:

* sender type;
* direction;
* message text;
* provider payload;
* AI metadata;
* timestamps.

---

## Lifecycle

```text
created → stored
```

Messages are immutable in MVP.

---

## Rules

* Message belongs to one tenant.
* Message belongs to one business.
* Message belongs to one conversation.
* Messages must be ordered by `created_at`.
* Duplicate external messages must be prevented.

---

## Sender Types

```text
customer
ai
owner
system
```

---

## Direction Types

```text
incoming
outgoing
internal
```

---

## AI Metadata

`ai_metadata`

Stores AI-related execution data.

Example:

```json
{
  "model": "gpt-4.1-mini",
  "input_tokens": 321,
  "output_tokens": 87,
  "latency_ms": 1200
}
```

---

# 8. Lead

## Meaning

A lead represents a business opportunity detected during conversation.

Examples:

* booking request;
* order request;
* consultation request;
* service inquiry;
* pricing inquiry.

---

## Responsibilities

Lead stores:

* requested service;
* preferred date/time;
* AI summary;
* customer notes;
* status;
* priority;
* assignment.

---

## Lifecycle

```text
new
→ in_progress
→ contacted
→ closed / lost
```

---

## Rules

* Lead belongs to one tenant.
* Lead belongs to one business.
* Lead belongs to one customer.
* Lead belongs to one conversation.
* Lead should only be created when business intent exists.

---

## Priority Values

```text
low
normal
high
urgent
```

---

# 9. DatabaseConnection

## Meaning

DatabaseConnection defines where tenant/business data is stored.

Supports future modes:

* shared database;
* dedicated database;
* customer-owned database.

---

## Responsibilities

Stores:

* provider;
* host;
* database metadata;
* SSL requirements;
* secret references;
* connection state.

---

## Lifecycle

```text
created
→ pending
→ active
→ failed / inactive
```

---

## Rules

* DatabaseConnection belongs to tenant.
* Passwords must never be stored raw.
* Only encrypted references or secret managers are allowed.

---

## Storage Modes

```text
shared
dedicated
external
```

---

# 10. TenantBusinessProfile

## Meaning

Stores structured business context used by AI.

This separates business knowledge from backend code and prompts.

---

## Responsibilities

Stores:

* business description;
* services;
* pricing;
* working hours;
* target audience;
* location;
* business limitations.

---

## Rules

* One business may have one active business profile.
* Business profile is part of AI context generation.
* Business profile must not override platform safety rules.

---

## Example

```text
Business: Barbershop
Services:
- haircut
- beard trim

Target audience:
- local men 20-45

Business limitation:
- appointments are not automatically confirmed
```

---

# 11. TenantAIProfile

## Meaning

Defines AI communication behavior for a tenant/business.

This is NOT the core system prompt.

Platform safety rules remain controlled by Alpstein AI.

---

## Responsibilities

Stores:

* tone;
* language;
* response style;
* escalation behavior;
* forbidden promises;
* required customer questions;
* fallback responses.

---

## Rules

* Tenant cannot override platform safety rules.
* Tenant cannot disable escalation logic.
* Tenant cannot force AI to invent information.
* AI profile affects Prompt Builder behavior.

---

## Example Tone Values

```text
friendly
professional
luxury
minimal
casual
```

---

# 12. TenantKnowledgeSource

## Meaning

Represents business knowledge used by AI.

Examples:

* FAQ;
* pricing;
* policies;
* instructions;
* service descriptions;
* business rules.

---

## Responsibilities

Stores retrievable business knowledge.

Knowledge is later injected into prompts.

---

## Rules

* Knowledge belongs to tenant.
* Knowledge may belong to one business.
* Only relevant knowledge should be injected into prompts.
* Future versions may use vector retrieval.

---

## MVP Simplification

MVP may use:

```text
PostgreSQL full-text search
```

instead of vector search.

---

# 13. TenantChannelSetting

## Meaning

Defines channel-specific AI behavior.

Different channels require different communication styles.

---

## Responsibilities

Stores:

* response length;
* emoji rules;
* formatting rules;
* channel behavior.

---

## Example

```text
WhatsApp:
- short replies
- conversational
- emoji allowed

Website chat:
- slightly longer replies
- structured answers
```

---

# 14. PromptTemplate

## Meaning

Stores platform-controlled AI prompt templates.

Prompt templates are controlled by Alpstein AI platform.

Tenants must not directly control core system prompts.

---

## Responsibilities

Stores templates for:

* customer replies;
* lead extraction;
* summarization;
* escalation;
* fallback handling.

---

## Rules

* PromptTemplate is platform-controlled.
* Tenants may customize limited behavior only.
* Templates may be versioned.

---

## Example

```text
customer_support_v1
lead_collection_v2
fallback_reply_v1
```

---

# 15. PromptRun

## Meaning

Represents one AI execution event.

Every AI request should create one PromptRun.

---

## Responsibilities

Stores:

* prompt version;
* model;
* tokens;
* latency;
* AI result;
* errors;
* prompt metadata.

---

## Why PromptRun Is Critical

PromptRun enables:

* debugging;
* AI quality control;
* token accounting;
* billing;
* analytics;
* prompt version tracking;
* incident investigation.

---

## Lifecycle

```text
created → completed / failed
```

---

## Rules

* PromptRun belongs to tenant.
* PromptRun belongs to business.
* PromptRun may belong to conversation.
* PromptRun may belong to message.
* PromptRun should never expose secrets.

---

## Important Note

This table may grow very quickly.

Future versions may require:

* partitioning;
* archival;
* retention policy.

---

# 16. AI Architecture Relationships

The AI system works as:

```text
Tenant
   ↓
Business Profile
   ↓
AI Behavior Profile
   ↓
Knowledge Sources
   ↓
Prompt Builder
   ↓
Prompt Template
   ↓
Prompt Run
   ↓
AI Response
```

---

# 17. Data Ownership Rules

All communication data belongs to the business client.

This includes:

* customers;
* conversations;
* messages;
* leads;
* AI summaries;
* AI configurations;
* business knowledge.

Alpstein AI processes this data only to provide the service.

---

# 18. Access Rules

All access to client-owned entities must filter by:

```text
tenant_id
```

Where relevant:

```text
business_id
```

Example:

```sql
SELECT * FROM prompt_runs
WHERE tenant_id = :tenant_id
AND business_id = :business_id;
```

---

# 19. MVP Entity Rules

For MVP:

* one tenant may be created manually;
* one demo business may be created manually;
* customers are created automatically;
* conversations are created automatically;
* AI profiles may be created manually;
* knowledge sources may be stored in PostgreSQL;
* prompt runs must be logged.

---

# 20. Future Entity Extensions

Future entities may include:

## User

Owner/admin/operator accounts.

## Integration

Connected channels and external services.

## Subscription

Billing and payment plans.

## AuditLog

Tracks critical system actions.

## Event

Tracks workflows and async events.

---

# 21. Success Criteria

Entity design is successful if:

* AI behavior is configurable;
* backend logic is predictable;
* prompt generation is modular;
* tenant isolation is enforced;
* platform safety rules remain protected;
* future onboarding automation is possible;
* backend is not tied to one hardcoded prompt;
* AI requests can be debugged through PromptRun history.