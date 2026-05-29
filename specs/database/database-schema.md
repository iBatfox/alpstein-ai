# Alpstein AI — Database Schema

## 1. Purpose

This document describes the PostgreSQL database schema for Alpstein AI MVP.

The database must support:

- tenants;
- businesses;
- customers;
- conversations;
- messages;
- leads;
- future external database connections;
- tenant-based data separation;
- future SaaS scalability.

---

# 2. General Rules

## 2.1 Tenant Isolation

Every table that contains client-owned data must include:

```text
tenant_id
business_id
```

This is required for security and future multi-tenant architecture.

---

## 2.2 Primary Keys

Primary keys should use UUID.

Recommended type:

```text
UUID
```

Reason:

- safer for public APIs;
- harder to guess;
- better for future distributed systems.

---

## 2.3 Timestamps

Every main table should include:

```text
created_at
updated_at
```

For immutable event-like records, only `created_at` is required.

---

## 2.4 Soft Delete

MVP does not require soft delete.

Future versions may add:

```text
deleted_at
```

---

## 2.5 Naming

Table names use plural snake_case.

Examples:

```text
tenants
businesses
customers
conversations
messages
leads
database_connections
```

---

# 3. Tables Overview

Core MVP tables:

```text
tenants
businesses
customers
conversations
messages
leads
database_connections
```

Future tables:

```text
events
audit_logs
users
subscriptions
integrations
```

Core AI configuration tables:

```text
tenant_business_profiles
tenant_ai_profiles
tenant_knowledge_sources
tenant_channel_settings
prompt_templates
prompt_runs
```
---

# 4. tenants

## Purpose

Stores tenant accounts.

A tenant represents the owner of business data.

In MVP:

```text
1 tenant = 1 business
```

In the future:

```text
1 tenant = multiple businesses
```

## Fields

```text
id UUID PRIMARY KEY
name VARCHAR(255) NOT NULL
slug VARCHAR(255) UNIQUE NOT NULL
email VARCHAR(255)
phone VARCHAR(50)
status VARCHAR(50) NOT NULL DEFAULT 'active'
created_at TIMESTAMP NOT NULL
updated_at TIMESTAMP NOT NULL
```

## Status values

```text
active
inactive
suspended
```

---

# 5. businesses

## Purpose

Stores business profiles.

A business represents a company, location, restaurant, barbershop, shop, or service provider.

Each business belongs to one tenant.

## Fields

```text
id UUID PRIMARY KEY
tenant_id UUID NOT NULL REFERENCES tenants(id)

external_id VARCHAR(255) UNIQUE NOT NULL
name VARCHAR(255) NOT NULL
business_type VARCHAR(100)
description TEXT

phone VARCHAR(50)
email VARCHAR(255)
website VARCHAR(255)
address TEXT

working_hours JSONB
language VARCHAR(20) DEFAULT 'de'
timezone VARCHAR(100) DEFAULT 'Europe/Zurich'

ai_prompt TEXT
ai_tone VARCHAR(100)
ai_language VARCHAR(20)

storage_mode VARCHAR(50) NOT NULL DEFAULT 'shared'
database_connection_id UUID REFERENCES database_connections(id)

status VARCHAR(50) NOT NULL DEFAULT 'active'

created_at TIMESTAMP NOT NULL
updated_at TIMESTAMP NOT NULL
```

## storage_mode values

```text
shared
dedicated
external
```

## status values

```text
active
inactive
suspended
```

---

# 6. customers

## Purpose

Stores end customers who communicate with a business.

Each customer belongs to one tenant and one business.

## Fields

```text
id UUID PRIMARY KEY
tenant_id UUID NOT NULL REFERENCES tenants(id)
business_id UUID NOT NULL REFERENCES businesses(id)

name VARCHAR(255)
phone VARCHAR(50)
email VARCHAR(255)
language VARCHAR(20)

external_customer_id VARCHAR(255)
source_channel VARCHAR(50)

created_at TIMESTAMP NOT NULL
updated_at TIMESTAMP NOT NULL
```

## Notes

Phone number should be normalized when possible.

A customer may be identified by:

```text
business_id + phone
```

Recommended unique constraint:

```text
UNIQUE (business_id, phone)
```

---

# 7. conversations

## Purpose

Stores conversation sessions between customers and the AI/business.

Each conversation belongs to:

```text
tenant
business
customer
```

## Fields

```text
id UUID PRIMARY KEY
tenant_id UUID NOT NULL REFERENCES tenants(id)
business_id UUID NOT NULL REFERENCES businesses(id)
customer_id UUID NOT NULL REFERENCES customers(id)

channel VARCHAR(50) NOT NULL
external_conversation_id VARCHAR(255)

status VARCHAR(50) NOT NULL DEFAULT 'open'
is_ai_active BOOLEAN NOT NULL DEFAULT true

last_message_at TIMESTAMP
created_at TIMESTAMP NOT NULL
updated_at TIMESTAMP NOT NULL
```

## channel values

```text
whatsapp
telegram
instagram
website_chat
test
```

## status values

```text
open
waiting_for_customer
waiting_for_owner
closed
archived
```

---

# 8. messages

## Purpose

Stores all incoming and outgoing messages.

Messages may be from:

- customer;
- AI;
- business owner;
- system.

## Fields

```text
id UUID PRIMARY KEY
tenant_id UUID NOT NULL REFERENCES tenants(id)
business_id UUID NOT NULL REFERENCES businesses(id)
conversation_id UUID NOT NULL REFERENCES conversations(id)

sender_type VARCHAR(50) NOT NULL
direction VARCHAR(50) NOT NULL
channel VARCHAR(50) NOT NULL

message_text TEXT NOT NULL
message_type VARCHAR(50) NOT NULL DEFAULT 'text'

external_message_id VARCHAR(255)
raw_payload JSONB
ai_metadata JSONB
metadata JSONB

created_at TIMESTAMP NOT NULL
```

## sender_type values

```text
customer
ai
owner
system
```

## message_type values

```text
text
image
audio
file
system
```

## Notes

For MVP, only text messages are required.

`raw_payload` can be used to store original provider payload if needed.

`external_message_id` is nullable. When a channel supplies a provider message identifier (for example WhatsApp `wamid`), it is stored here for idempotent ingestion.

### Idempotency (business-scoped)

At most one message row per `(business_id, external_message_id)` is allowed when `external_message_id` is set. Uniqueness is enforced by a partial unique index (see Indexes — messages):

```text
UNIQUE messages_business_external_message_id_unique ON messages(business_id, external_message_id)
WHERE external_message_id IS NOT NULL
```

Purpose:

- prevent duplicate rows for the same provider message within a business;
- protect against concurrent duplicate inserts on webhook retries (database-level guard alongside service-layer deduplication).

Scope is `business_id`, not tenant alone: the same `external_message_id` may exist on different businesses.

Rows with `external_message_id IS NULL` are outside the partial unique index. Multiple messages with NULL `external_message_id` per business are allowed.

---

# 9. leads

## Purpose

Stores business opportunities extracted from conversations.

A lead is created when the customer shows interest in a service, booking, order, or consultation.

## Fields

```text
id UUID PRIMARY KEY
tenant_id UUID NOT NULL REFERENCES tenants(id)
business_id UUID NOT NULL REFERENCES businesses(id)
customer_id UUID NOT NULL REFERENCES customers(id)
conversation_id UUID NOT NULL REFERENCES conversations(id)

service_requested VARCHAR(255)
preferred_date DATE
preferred_time TIME
customer_note TEXT

status VARCHAR(50) NOT NULL DEFAULT 'new'
priority VARCHAR(50) DEFAULT 'normal'

source_channel VARCHAR(50)
ai_summary TEXT

created_at TIMESTAMP NOT NULL
updated_at TIMESTAMP NOT NULL
```

## status values

```text
new
in_progress
contacted
closed
lost
```

## priority values

```text
low
normal
high
urgent
```

---

# 10. database_connections

## Purpose

Stores metadata for future dedicated or external database connections.

This table prepares the system for:

- dedicated database per client;
- customer-owned database;
- cloud database providers.

This feature is not implemented in MVP but the schema supports it.

## Fields

```text
id UUID PRIMARY KEY
tenant_id UUID NOT NULL REFERENCES tenants(id)
business_id UUID REFERENCES businesses(id)

provider VARCHAR(100) NOT NULL
connection_type VARCHAR(100) NOT NULL

host VARCHAR(255)
port INTEGER
database_name VARCHAR(255)
username VARCHAR(255)

encrypted_password_reference TEXT
ssl_required BOOLEAN NOT NULL DEFAULT true

status VARCHAR(50) NOT NULL DEFAULT 'inactive'

created_at TIMESTAMP NOT NULL
updated_at TIMESTAMP NOT NULL
```

## provider values

```text
alpstein_shared
aws_rds
google_cloud_sql
azure_postgresql
supabase
self_hosted
other
```

## connection_type values

```text
shared
dedicated
external
```

## status values

```text
active
inactive
failed
pending
```

## Security rule

Do not store raw database passwords in this table.

Use:

- encrypted secret storage;
- secret manager;
- environment variables;
- external vault.

---

---

# 11. tenant_business_profiles

## Purpose

Stores structured business context for AI.

This table separates business operational context from core business entity.

The purpose is to avoid hardcoding business logic into prompts or backend code.

## Fields

```text
id UUID PRIMARY KEY

tenant_id UUID NOT NULL REFERENCES tenants(id)
business_id UUID NOT NULL REFERENCES businesses(id)

business_description TEXT
services JSONB
pricing JSONB
working_hours JSONB

target_audience TEXT
business_limitations TEXT

city VARCHAR(255)
region VARCHAR(255)
country VARCHAR(255)

metadata JSONB

created_at TIMESTAMP NOT NULL
updated_at TIMESTAMP NOT NULL
```

## Notes

Example services JSON:

```json
{
  "haircut": {
    "price": 35,
    "currency": "CHF"
  }
}
```

---

# 12. tenant_ai_profiles

## Purpose

Stores AI behavior configuration for a tenant/business.

This table defines how the AI should communicate.

The platform still controls the core system prompt and safety rules.

## Fields

```text
id UUID PRIMARY KEY

tenant_id UUID NOT NULL REFERENCES tenants(id)
business_id UUID NOT NULL REFERENCES businesses(id)

profile_name VARCHAR(255)

tone VARCHAR(100)
response_style VARCHAR(100)
language VARCHAR(20)

ask_for_name BOOLEAN DEFAULT true
ask_for_phone BOOLEAN DEFAULT true
ask_for_email BOOLEAN DEFAULT false

handoff_enabled BOOLEAN DEFAULT true
handoff_keywords JSONB

forbidden_promises JSONB

fallback_response TEXT

metadata JSONB

created_at TIMESTAMP NOT NULL
updated_at TIMESTAMP NOT NULL
```

## Example tone values

```text
friendly
professional
minimal
luxury
casual
```

---

# 13. tenant_knowledge_sources

## Purpose

Stores business knowledge used by AI.

Examples:

- FAQ;
- pricing;
- policies;
- instructions;
- service descriptions.

In MVP, knowledge can be stored directly in PostgreSQL.

Future versions may use vector retrieval.

## Fields

```text
id UUID PRIMARY KEY

tenant_id UUID NOT NULL REFERENCES tenants(id)
business_id UUID NOT NULL REFERENCES businesses(id)

source_type VARCHAR(100) NOT NULL
title VARCHAR(255)

content TEXT NOT NULL

tags JSONB
metadata JSONB

is_active BOOLEAN NOT NULL DEFAULT true

created_at TIMESTAMP NOT NULL
updated_at TIMESTAMP NOT NULL
```

## source_type values

```text
faq
policy
service
instruction
pricing
document
other
```

---

# 14. tenant_channel_settings

## Purpose

Stores channel-specific communication rules.

Different channels may require different AI behavior.

## Fields

```text
id UUID PRIMARY KEY

tenant_id UUID NOT NULL REFERENCES tenants(id)
business_id UUID NOT NULL REFERENCES businesses(id)

channel VARCHAR(50) NOT NULL

response_style VARCHAR(100)
max_response_length INTEGER

allow_emojis BOOLEAN DEFAULT false
allow_links BOOLEAN DEFAULT false

metadata JSONB

created_at TIMESTAMP NOT NULL
updated_at TIMESTAMP NOT NULL
```

## channel values

```text
whatsapp
telegram
instagram
website_chat
test
```

---

# 15. prompt_templates

## Purpose

Stores platform-controlled prompt templates.

Templates are controlled by Alpstein AI platform, not directly by tenants.

Templates may include:

- customer support;
- lead collection;
- summarization;
- escalation;
- fallback handling.

## Fields

```text
id UUID PRIMARY KEY

template_key VARCHAR(255) UNIQUE NOT NULL
template_name VARCHAR(255)

description TEXT

system_prompt TEXT NOT NULL

version VARCHAR(50)

is_active BOOLEAN NOT NULL DEFAULT true

created_at TIMESTAMP NOT NULL
updated_at TIMESTAMP NOT NULL
```

---

# 16. prompt_runs

## Purpose

Stores every AI prompt execution.

This table is critical for:

- debugging;
- token tracking;
- AI analytics;
- quality control;
- incident investigation;
- future billing.

## Fields

```text
id UUID PRIMARY KEY

tenant_id UUID NOT NULL REFERENCES tenants(id)
business_id UUID NOT NULL REFERENCES businesses(id)

conversation_id UUID REFERENCES conversations(id)
message_id UUID REFERENCES messages(id)

prompt_template_id UUID REFERENCES prompt_templates(id)

prompt_version VARCHAR(50)

model VARCHAR(100) NOT NULL

input_tokens INTEGER
output_tokens INTEGER

final_prompt TEXT
result TEXT

error TEXT

latency_ms INTEGER

provider VARCHAR(100)

metadata JSONB

created_at TIMESTAMP NOT NULL
```

## Notes

This table may grow very quickly.

Future versions may require:

- partitioning;
- retention policy;
- archive storage.

# 17. Recommended Indexes

## tenants

```text
INDEX tenants_slug_idx ON tenants(slug)
INDEX tenants_status_idx ON tenants(status)
```

## businesses

```text
INDEX businesses_tenant_id_idx ON businesses(tenant_id)
INDEX businesses_external_id_idx ON businesses(external_id)
INDEX businesses_status_idx ON businesses(status)
```

## customers

```text
INDEX customers_tenant_id_idx ON customers(tenant_id)
INDEX customers_business_id_idx ON customers(business_id)
INDEX customers_phone_idx ON customers(phone)
UNIQUE customers_business_phone_unique ON customers(business_id, phone)
```

## conversations

```text
INDEX conversations_tenant_id_idx ON conversations(tenant_id)
INDEX conversations_business_id_idx ON conversations(business_id)
INDEX conversations_customer_id_idx ON conversations(customer_id)
INDEX conversations_status_idx ON conversations(status)
```

## messages

```text
INDEX messages_tenant_id_idx ON messages(tenant_id)
INDEX messages_business_id_idx ON messages(business_id)
INDEX messages_conversation_id_idx ON messages(conversation_id)
INDEX messages_created_at_idx ON messages(created_at)
INDEX messages_external_message_id_idx ON messages(external_message_id)
UNIQUE messages_business_external_message_id_unique ON messages(business_id, external_message_id)
  WHERE external_message_id IS NOT NULL
```

## leads

```text
INDEX leads_tenant_id_idx ON leads(tenant_id)
INDEX leads_business_id_idx ON leads(business_id)
INDEX leads_customer_id_idx ON leads(customer_id)
INDEX leads_status_idx ON leads(status)
INDEX leads_created_at_idx ON leads(created_at)
```

## database_connections

```text
INDEX database_connections_tenant_id_idx ON database_connections(tenant_id)
INDEX database_connections_business_id_idx ON database_connections(business_id)
INDEX database_connections_status_idx ON database_connections(status)
```

---

# 18. Relationships

## tenants → businesses

```text
one tenant has many businesses
```

## tenants → customers

```text
one tenant has many customers
```

## businesses → customers

```text
one business has many customers
```

## customers → conversations

```text
one customer has many conversations
```

## conversations → messages

```text
one conversation has many messages
```

## conversations → leads

```text
one conversation can have many leads
```

## customers → leads

```text
one customer can have many leads
```

---

# 19. Data Access Rules

All queries for client-owned data must filter by:

```text
tenant_id
```

Where relevant, also filter by:

```text
business_id
```

Example:

```sql
SELECT * FROM leads
WHERE tenant_id = :tenant_id
AND business_id = :business_id;
```

This is required for security and tenant isolation.

---

# 20. MVP Required Tables

The MVP must implement at minimum:

```text
tenants
businesses
customers
conversations
messages
leads
```

`database_connections` can be created in MVP as a future-ready table, but active external database support is not required.

---

# 21. What Is Not Required In MVP

The MVP does not require:

- users table;
- subscriptions table;
- payments;
- audit logs;
- analytics tables;
- vector database;
- file storage;
- direct external database routing;
- multi-region database setup.

These can be added later.

---

# 22. Observability and retry tables (E2–E3)

## delivery_events (E2.6, E3.2)

Outbound channel delivery lifecycle per `outbound_message_id`.

**status values:** `pending`, `delivered`, `failed`, `skipped`, `retrying`, `dead_letter` (E3.2 terminal).

**retry_count:** increments on each `failed` PATCH (including repeated `failed` without `retrying`) and on allowed `retrying` PATCH.

## replay_events (E3.1c)

Append-only duplicate/replay audit (`duplicate_retry`, `replay_ignored`, `illegal_transition`, `retry_exhausted`). Not the operational retry log.

## retry_attempts (E3.2a)

Append-only operational retry lifecycle per scope.

```text
id UUID PRIMARY KEY
tenant_id UUID NOT NULL REFERENCES tenants(id)
business_id UUID NOT NULL REFERENCES businesses(id)
scope_type TEXT NOT NULL          -- delivery | inbound
scope_id UUID NOT NULL
trace_id UUID NULL
conversation_id UUID NULL
attempt_number INTEGER NOT NULL
status TEXT NOT NULL              -- retrying | failed | exhausted
error_type TEXT NULL
error_message TEXT NULL
correlation_id TEXT NULL
metadata JSONB NULL
created_at TIMESTAMP NOT NULL
```

Indexes: `(business_id, scope_type, scope_id, created_at)`, `(business_id, conversation_id, created_at)`, `trace_id`.

## dead_letter_events (E3.2b)

Permanently failed operations after retry exhaustion or terminal delivery error.

```text
id UUID PRIMARY KEY
tenant_id UUID NOT NULL REFERENCES tenants(id)
business_id UUID NOT NULL REFERENCES businesses(id)
flow_id UUID NULL
conversation_id UUID NULL
trace_id UUID NULL
delivery_id UUID NULL
inbound_message_id UUID NULL
outbound_message_id UUID NULL
scope_type TEXT NOT NULL          -- delivery | inbound
scope_id UUID NOT NULL
event_type TEXT NOT NULL
failure_reason TEXT NOT NULL
error_type TEXT NULL
retry_count INTEGER NOT NULL
correlation_id TEXT NULL
metadata JSONB NULL
resolved_at TIMESTAMP NULL
created_at TIMESTAMP NOT NULL
last_seen_at TIMESTAMP NOT NULL
```

**Unique (active):** `(business_id, scope_type, scope_id)` WHERE `resolved_at IS NULL`.

## inbound_processing_locks (E3.1a)

Single-owner lock per `(business_id, conversation_id, idempotency_key)`; `replay_count` for provider redelivery cap (E3.2).

## rate_limit_buckets (E3.5a)

Atomic ingress counters per scope and fixed time window. Backend-only writes.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| tenant_id | UUID FK | required |
| business_id | UUID FK | required |
| scope_type | VARCHAR(50) | `tenant` \| `business` \| `adapter` \| `conversation` |
| scope_key | VARCHAR(255) | deterministic key (e.g. `{business_id}:{channel}` for adapter) |
| channel | VARCHAR(50) NULL | set for adapter scope |
| window_start | TIMESTAMP | UTC bucket start |
| window_seconds | INT | window size (default 60) |
| request_count | INT | monotonic within window |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

**Unique:** `(tenant_id, business_id, scope_type, scope_key, window_start)`

## rate_limit_violations (E3.5c)

Append-only audit when ingress is rejected for rate limiting. No message text, secrets, or PII in `metadata`.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| tenant_id | UUID FK | |
| business_id | UUID FK | |
| scope_type | VARCHAR(50) | exceeded scope |
| scope_key | VARCHAR(255) | |
| channel | VARCHAR(50) NULL | adapter context |
| conversation_id | UUID NULL | when applicable |
| limit_value | INT | configured limit |
| window_seconds | INT | |
| window_start | TIMESTAMP | |
| observed_count | INT | count at rejection |
| correlation_id | TEXT NULL | observability correlation |
| metadata | JSONB NULL | safe fields only |
| created_at | TIMESTAMP | |

**Indexes:** `(business_id, created_at)`, `(business_id, channel, created_at)`, `(scope_type, created_at)`

## spam_indicator_buckets (E3.6a)

Deterministic spam signal counters per rule, scope, and fixed time window. Backend-only writes. No message text — payload repeat uses SHA-256 hash in `scope_key`.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| tenant_id | UUID FK | required |
| business_id | UUID FK | required |
| rule_id | VARCHAR(64) | `payload_repeat` \| `conversation_burst` \| `adapter_fanout` \| `retry_abuse` \| `replay_storm` |
| scope_type | VARCHAR(32) | `conversation` \| `adapter` |
| scope_key | VARCHAR(255) | deterministic key (e.g. `{conversation_id}:{payload_hash}`) |
| channel | VARCHAR(50) NULL | adapter context |
| window_start | TIMESTAMP | UTC bucket start |
| window_seconds | INT | window size |
| signal_count | INT | monotonic within window |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

**Unique:** `(tenant_id, business_id, rule_id, scope_type, scope_key, window_start)`

## spam_containments (E3.6b)

Reversible active containment state (TTL-based). No permanent bans; no tenant-wide auto-blocks.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| tenant_id | UUID FK | required |
| business_id | UUID FK | required |
| rule_id | VARCHAR(64) | triggering rule |
| scope_type | VARCHAR(32) | containment scope |
| scope_key | VARCHAR(255) | deterministic key |
| channel | VARCHAR(50) NULL | |
| conversation_id | UUID NULL | when conversation-scoped |
| action | VARCHAR(32) | `throttle` \| `temporary_block` |
| expires_at | TIMESTAMP | TTL expiry (required) |
| released_at | TIMESTAMP NULL | manual/ops release (optional) |
| correlation_id | TEXT NULL | observability correlation |
| metadata | JSONB NULL | safe fields only — no message text, prompts, secrets |
| created_at | TIMESTAMP | |

**Unique (active):** `(tenant_id, business_id, scope_type, scope_key, rule_id)` WHERE `released_at IS NULL`

## spam_decisions (E3.6c)

Append-only spam decision audit stream. No separate `spam_events` table.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| tenant_id | UUID FK | required |
| business_id | UUID FK | required |
| rule_id | VARCHAR(64) | |
| scope_type | VARCHAR(32) | |
| scope_key | VARCHAR(255) | |
| channel | VARCHAR(50) NULL | |
| conversation_id | UUID NULL | |
| decision | VARCHAR(32) | `allow` \| `mark_suspicious` \| `throttle` \| `temporary_block` \| `ignore` |
| outcome | VARCHAR(32) | `passed` \| `applied` \| `already_contained` \| `skipped_duplicate` |
| observed_count | INT NULL | count at decision |
| threshold | INT NULL | configured threshold |
| window_seconds | INT NULL | rule window |
| containment_id | UUID NULL FK → `spam_containments.id` | when containment applied |
| correlation_id | TEXT NULL | |
| metadata | JSONB NULL | safe fields only (e.g. `payload_hash_prefix`) |
| created_at | TIMESTAMP | |

**Indexes:** `(business_id, created_at)`, `(business_id, channel, created_at)`, `(rule_id, created_at)`

---

# 23. Success Criteria

The database schema is successful if:

- tenants can be created;
- businesses belong to tenants;
- customers belong to businesses and tenants;
- conversations can be stored;
- messages can be stored;
- leads can be created;
- every client-owned table supports tenant separation;
- future dedicated or external storage is not blocked;
- indexes support basic MVP queries;
- schema is clear enough for backend implementation.
