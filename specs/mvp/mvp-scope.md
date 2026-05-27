# Alpstein AI — MVP Scope

## 1. Purpose

This document defines the exact scope of the Alpstein AI MVP.

The purpose of the MVP is:

- validate the product idea;
- demonstrate working AI business automation;
- acquire first local clients;
- prove business value;
- avoid overengineering;
- build a stable foundation for future SaaS scaling.

This document explicitly defines:

- what IS included in MVP;
- what is NOT included in MVP;
- what is considered successful MVP delivery.

---

# 2. MVP Goal

The main goal of the MVP is:

```text
Allow a small business to receive customer messages through WhatsApp or website chat,
automatically respond using AI,
store conversations and leads,
and notify the business owner.
```

The MVP must be simple, stable, and demonstrable to local businesses.

---

# 3. Target Clients

Initial target clients:

- restaurants;
- barbershops;
- local shops;
- cafes;
- small service businesses;
- shawarma shops;
- local SMB businesses.

Initial market:

```text
Switzerland
Local city launch first
```

---

# 4. MVP Core Features

## 4.1 Incoming Message Processing

The system must support:

- receiving incoming messages;
- normalized webhook processing;
- multi-channel-ready architecture.

MVP channels:

```text
WhatsApp Cloud API
Test Webhook
```

---

## 4.2 AI Customer Communication

The AI must:

- answer customer questions;
- collect lead information;
- ask clarifying questions;
- use business-specific context;
- use configurable communication style;
- escalate uncertain situations to human owner.

The AI must not:

- invent business information;
- promise unavailable services;
- override platform safety rules.

---

## 4.3 Lead Creation

The MVP must:

- create leads from incoming messages;
- prevent duplicate leads;
- update existing active leads;
- connect leads to conversations and customers.

Lead creation must support:

```text
tenant_id
business_id
customer_id
conversation_id
```

---

## 4.4 Conversation Storage

The system must store:

- conversations;
- messages;
- timestamps;
- AI responses;
- lead relations.

PostgreSQL is the primary storage.

---

## 4.5 AI Configuration Architecture

The MVP must support configurable AI behavior.

Architecture:

```text
Tenant
↓
Business Profile
↓
AI Behavior Profile
↓
Knowledge Base
↓
Prompt Builder
↓
AI Response
```

The system must not use one hardcoded prompt.

---

## 4.6 Prompt Builder

The MVP must dynamically assemble prompts from:

- platform rules;
- tenant business context;
- tenant AI behavior profile;
- relevant knowledge;
- channel rules;
- conversation history.

---

## 4.7 Knowledge Base

The MVP knowledge base may use:

```text
PostgreSQL text storage
PostgreSQL full-text search
```

The MVP does not require vector databases.

Knowledge examples:

- FAQ;
- services;
- pricing;
- policies;
- instructions.

---

## 4.8 PromptRun Logging

Every AI execution must create a PromptRun record.

PromptRun must store:

- model;
- tokens;
- latency;
- result;
- prompt version;
- errors.

This is required for:

- debugging;
- AI quality control;
- analytics;
- future billing.

---

## 4.9 Notifications

The MVP must support notifications for:

- new lead;
- urgent lead;
- human handoff;
- AI failure.

Recommended MVP notification channel:

```text
Telegram
```

---

## 4.10 n8n Integration Layer

n8n must handle:

- webhooks;
- integrations;
- lead routing;
- notifications;
- provider communication.

n8n must not contain:

- AI business logic;
- database business logic;
- prompt logic.

---

## 4.11 Tenant Isolation

All client-owned data must be isolated by:

```text
tenant_id
business_id
```

This is mandatory.

---

## 4.12 External Lead Destinations

The architecture must support future lead routing to:

- CRM;
- spreadsheets;
- customer-owned databases;
- webhooks.

MVP may initially store leads only in Alpstein AI PostgreSQL.

---

# 5. MVP Technical Stack

## Backend

```text
Python
FastAPI
SQLAlchemy
Alembic
```

---

## Database

```text
PostgreSQL
```

---

## Automation Layer

```text
n8n
```

---

## Infrastructure

```text
Docker Compose
Nginx
Contabo VPS
```

Server:

```text
144.91.113.184
```

Domain:

```text
https://alpstein-ai.ch
```

---

## AI Provider

Initial provider:

```text
OpenAI
```

Future providers may be added later.

---

# 6. MVP Required Database Entities

Required entities:

```text
tenants
businesses
customers
conversations
messages
leads

tenant_business_profiles
tenant_ai_profiles
tenant_knowledge_sources
tenant_channel_settings

prompt_templates
prompt_runs
```

---

# 7. MVP Required Backend Services

Required services:

```text
Webhook Processing Service
Conversation Service
Lead Service
AI Configuration Service
Prompt Builder Service
Knowledge Retrieval Service
AI Gateway Service
Notification Service
```

---

# 8. MVP Required API Endpoints

Required endpoints:

```text
POST /api/v1/webhook/message
GET /api/v1/health

POST /api/v1/tenants
POST /api/v1/businesses

GET /api/v1/leads
GET /api/v1/conversations/{id}
```

---

# 9. MVP Required Flows

Required flows:

```text
incoming-message-flow
lead-creation-flow
notification-flow
```

---

# 10. MVP Required Security Rules

The MVP must enforce:

- HTTPS;
- tenant isolation;
- API token between n8n and backend;
- protected PostgreSQL access;
- no secrets in logs;
- no direct DB writes from n8n;
- protected AI system prompts.

---

# 11. What Is NOT Included In MVP

The MVP explicitly does NOT include:

- frontend dashboard;
- self-service onboarding;
- billing system;
- Stripe integration;
- vector database;
- semantic RAG;
- embeddings infrastructure;
- AI memory systems;
- voice assistant;
- phone calls;
- mobile app;
- Kubernetes;
- microservices;
- Redis queues;
- async distributed workers;
- advanced analytics;
- AI training;
- AI self-learning;
- multi-agent orchestration;
- enterprise RBAC;
- advanced CRM sync;
- multi-region infrastructure.

---

# 12. Allowed MVP Simplifications

Allowed simplifications:

```text
Single VPS deployment
Single PostgreSQL instance
Single OpenAI model
Simple Prompt Builder
Simple knowledge retrieval
Telegram-only notifications
Synchronous processing
```

These simplifications are acceptable for MVP.

---

# 13. MVP Business Demonstration Scenario

The MVP must support this demonstration:

```text
Customer sends WhatsApp message
      ↓
AI responds automatically
      ↓
Conversation is stored
      ↓
Lead is created
      ↓
Business owner receives Telegram notification
```

This scenario must work reliably.

---

# 14. MVP Success Criteria

The MVP is considered successful if:

- incoming messages work;
- AI responses work;
- lead creation works;
- duplicate prevention works;
- notifications work;
- tenant isolation works;
- AI configuration works;
- PromptRuns are logged;
- the product can be demonstrated to local businesses;
- first real clients can onboard manually.

---

# 15. MVP Launch Strategy

Initial launch strategy:

```text
Start locally
Acquire first businesses manually
Demonstrate live AI assistant
Collect feedback
Improve flows
Add integrations later
```

Initial onboarding may be fully manual.

---

# 16. Main MVP Philosophy

The MVP must prioritize:

```text
working product
stable architecture
real business value
fast iteration
simple deployment
```

The MVP must avoid:

```text
overengineering
premature scaling
enterprise complexity
infinite architecture work
```

---

# 17. Final MVP Definition

The MVP is NOT:

```text
full SaaS platform
enterprise AI system
fully automated onboarding system
```

The MVP IS:

```text
a working AI communication assistant for small businesses
with lead capture,
conversation storage,
AI responses,
and scalable architecture foundations.
```