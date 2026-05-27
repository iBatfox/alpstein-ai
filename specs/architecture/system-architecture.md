````md
# Alpstein AI — System Architecture

## 1. Purpose

This document describes the system architecture of Alpstein AI MVP.

The goal of the architecture is to keep the system simple, modular, scalable, and easy to extend in the future.

The MVP must support the following core flow:

Customer Message → n8n → Python Backend → AI Processing → PostgreSQL → n8n → Customer / Business Owner

---

# 2. High-Level Architecture

Alpstein AI consists of four main layers:

1. Communication Layer
2. Automation Layer
3. Backend Business Logic Layer
4. Data Storage Layer

---

# 3. Main System Flow

```text
Client Message
      ↓
Messenger / Website Chat / WhatsApp
      ↓
n8n Automation receives and normalizes message
      ↓
Python Backend
      ↓
AI Processing
      ↓
PostgreSQL Database
      ↓
n8n Automation sends response / triggers actions
      ↓
Customer receives reply
      ↓
Business Owner receives notification if needed
```

---

# 4. Components

## 4.1 Communication Layer

The communication layer represents all external channels where customers can contact the business.

Initial MVP channel:

- WhatsApp Cloud API
- Test Webhook

Future planned channels:

- Telegram
- Instagram Direct
- Website Chat Widget

The communication layer must not contain business logic.

Its role is only:

- receiving messages;
- sending responses.

---

## 4.2 n8n Automation Layer

n8n acts as the integration and orchestration layer.

n8n responsibilities:

- receive incoming webhooks;
- normalize incoming message data;
- send normalized requests to Python backend;
- receive structured backend responses;
- send AI-generated replies back to customer;
- notify business owner;
- execute future automations and integrations.

n8n must not contain:

- AI business logic;
- database business logic;
- lead qualification logic.

n8n should remain focused on automation and integrations.

---

## 4.3 Python Backend Layer

Python Backend is the core business logic layer.

Backend responsibilities:

- validate incoming requests;
- identify business;
- identify or create customer;
- create or update conversations;
- store incoming messages;
- prepare AI context;
- send requests to AI provider;
- receive AI response;
- store AI responses;
- detect lead information;
- create leads;
- return structured responses to n8n.

The backend must remain independent from messenger APIs.

All channels must communicate with backend through one normalized data structure.

---

## 4.4 AI Processing Layer

AI processing is part of the backend service layer.

AI responsibilities:

- understand customer intent;
- generate replies;
- ask clarifying questions;
- collect lead information;
- stay within business context;
- escalate unclear situations to human owner.

AI must not:

- directly communicate with external APIs;
- access databases directly;
- control workflows.

AI receives structured context from backend and returns structured output.

---

## 4.5 PostgreSQL Database Layer

PostgreSQL is the primary persistent storage.

Database stores:

- businesses;
- customers;
- conversations;
- messages;
- leads.

Database access rules:

- backend can access database directly;
- n8n should not write directly to PostgreSQL in MVP;
- AI should not access database directly.

This keeps business logic centralized and easier to maintain.

---

# 5. Responsibility Separation

## n8n Responsibilities

n8n handles:

- external integrations;
- webhooks;
- automation flows;
- customer reply delivery;
- owner notifications;
- workflow orchestration.

---

## Backend Responsibilities

Backend handles:

- business logic;
- validation;
- AI processing;
- database operations;
- lead creation;
- structured responses.

---

## Database Responsibilities

PostgreSQL handles:

- relational data storage;
- conversation history;
- lead records;
- customer records;
- business records.

---

## AI Responsibilities

AI handles:

- generating replies;
- extracting intent;
- helping with lead collection;
- supporting first-line communication.

---

# 6. Normalized Message Contract

All incoming requests from n8n to backend must use one common structure.

Example:

```json
{
  "business_id": "demo_barbershop_001",
  "channel": "whatsapp",
  "customer": {
    "phone": "+41790000000",
    "name": null
  },
  "message": {
    "text": "Hello, can I book an appointment tomorrow?",
    "external_message_id": "wamid.example",
    "timestamp": "2026-05-21T10:00:00Z"
  }
}
```

The backend must never depend on raw WhatsApp or Telegram payloads.

n8n is responsible for normalization.

---

# 7. Backend Response Contract

Backend returns structured JSON response to n8n.

Example:

```json
{
  "success": true,
  "reply_to_customer": "Hello! Sure. What service would you like to book and what time works best for you?",
  "lead_created": true,
  "lead": {
    "id": 123,
    "service_requested": "Barbershop appointment",
    "status": "new"
  },
  "notify_owner": true
}
```

n8n uses this response to:

- send reply to customer;
- notify business owner;
- trigger additional workflows.

---

# 8. Deployment Architecture

The MVP runs on one server.

Server:

```text
IP: 144.91.113.184
Provider: Contabo
```

Main services:

```text
nginx
backend
postgres
n8n
```

Recommended container structure:

```text
Docker Compose
├── nginx
├── backend
├── postgres
└── n8n
```

---

# 9. Network Architecture

Public access:

```text
Internet
  ↓
Nginx
  ↓
backend / n8n
```

Internal communication:

```text
n8n → backend
backend → postgres
```

PostgreSQL must not be publicly accessible.

Only backend should connect to PostgreSQL.

---

# 10. Security Principles

The MVP must follow basic security rules.

## Environment Variables

All secrets must be stored in `.env`.

Examples:

- database password;
- OpenAI API key;
- secret keys;
- n8n credentials.

`.env` must never be committed to git.

---

## HTTPS

Public endpoints must use SSL.

Nginx should terminate HTTPS connections.

---

## Database Security

PostgreSQL must remain private inside Docker network.

No public database exposure.

---

## n8n Security

n8n admin panel must be protected with authentication.

---

## Logging

The system must log:

- errors;
- webhook requests;
- failed AI responses;
- backend failures.

Sensitive credentials must never appear in logs.

---

## Validation

Backend must validate:

- incoming payload structure;
- required fields;
- message formats.

---

# 11. Scalability Principles

The MVP starts with:

- one server;
- one backend;
- one PostgreSQL database;
- one n8n instance.

However, architecture must allow future expansion:

- multiple businesses;
- multiple channels;
- reusable workflows;
- Redis queue;
- background workers;
- dashboard;
- analytics;
- billing;
- CRM integrations.

Future scaling should not require rewriting the system architecture.

---

# 12. Design Decisions

## Decision 1 — n8n as integration layer

n8n handles integrations because it allows:

- fast automation;
- easier webhook testing;
- faster MVP development;
- low-code workflow management.

---

## Decision 2 — Backend owns business logic

Business logic remains inside Python backend.

Reason:

- cleaner architecture;
- easier debugging;
- easier testing;
- future SaaS scalability.

---

## Decision 3 — PostgreSQL as primary database

PostgreSQL is chosen because the system requires structured relational data:

- businesses;
- customers;
- conversations;
- leads;
- messages.

---

## Decision 4 — Normalized message format

All communication channels must use one normalized contract.

Reason:

- backend independence from messenger APIs;
- easier future integrations;
- cleaner architecture.

---

## Decision 5 — No direct DB writes from n8n

n8n must not write directly into PostgreSQL during MVP.

Reason:

- avoid duplicated business logic;
- easier maintenance;
- cleaner data consistency.

---

# 13. What Is Not Included In MVP

The MVP architecture does not include:

- frontend dashboard;
- billing system;
- Stripe integration;
- vector database;
- multi-agent architecture;
- voice assistant;
- mobile application;
- advanced analytics;
- self-service onboarding;
- AI self-learning;
- enterprise RBAC system.

These features may be added later after the MVP flow is stable.

---

# 14. MVP Success Criteria

The architecture is considered successful if:

- n8n receives incoming messages;
- n8n sends normalized payloads to backend;
- backend processes requests correctly;
- PostgreSQL stores data correctly;
- backend returns structured responses;
- n8n sends replies to customers;
- business owner receives notifications;
- the system can be demonstrated to local businesses.
````
