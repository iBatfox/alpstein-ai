# Alpstein AI — n8n Architecture

## 1. Purpose

This document describes the role and architecture of n8n inside Alpstein AI MVP.

n8n acts as the automation and integration layer of the system.

Its main purpose is to:

- receive incoming messages from external channels;
- normalize message payloads;
- send requests to backend;
- receive backend responses;
- send replies back to customers;
- notify business owners;
- orchestrate automation workflows.

n8n must remain separate from core business logic.

---

# 2. Role of n8n In The System

n8n is responsible for communication and automation.

The backend is responsible for business logic.

n8n should:

- connect external APIs;
- receive webhooks;
- process workflows;
- call backend endpoints;
- send notifications;
- trigger integrations.

n8n should NOT:

- contain AI prompt logic;
- directly create database records;
- contain business decision logic;
- replace backend responsibilities.

---

# 3. Main System Flow

```text
Customer Message
      ↓
Messenger / Website Chat / WhatsApp
      ↓
n8n receives webhook
      ↓
n8n normalizes message
      ↓
n8n sends request to backend
      ↓
backend processes message
      ↓
backend returns structured response
      ↓
n8n sends reply to customer
      ↓
n8n sends owner notification
```

---

# 4. Main Responsibilities

## 4.1 Incoming Webhooks

n8n receives:

- WhatsApp webhooks;
- website chat webhooks;
- future Telegram webhooks;
- future Instagram webhooks.

---

## 4.2 Message Normalization

Different providers return different payload formats.

n8n converts all external payloads into one normalized structure before sending to backend.

Example normalized payload:

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

---

# 5. Backend Communication

n8n communicates with backend through HTTP API.

Main backend endpoint:

```http
POST /webhook/message
```

n8n sends normalized payload.

Backend returns structured response.

Example response:

```json
{
  "success": true,
  "reply_to_customer": "Hello! Sure. What service would you like to book and what time works best for you?",
  "lead_created": true,
  "notify_owner": true
}
```

---

# 6. Customer Reply Handling

After backend response:

n8n sends AI-generated reply back to customer using the appropriate channel API.

Examples:

- WhatsApp reply;
- Telegram message;
- Website chat response.

The backend does not communicate directly with external messaging APIs.

---

# 7. Owner Notifications

n8n is responsible for notifying business owners.

Possible notification channels:

- Telegram;
- email;
- WhatsApp;
- internal workflow.

Example notification:

```text
New Lead Created

Name: John
Phone: +41790000000
Service: Haircut
```

---

# 8. Future Workflow Automation

Future versions of n8n workflows may include:

- CRM integrations;
- Google Sheets logging;
- follow-up reminders;
- analytics;
- appointment reminders;
- AI escalation flows;
- customer tagging;
- lead scoring.

These features are NOT part of MVP.

---

# 9. n8n Deployment

n8n runs inside Docker.

Container responsibilities:

- workflow execution;
- webhook handling;
- API integrations;
- automation orchestration.

n8n service runs on:

```text
port 5678
```

---

# 10. n8n Security

n8n admin panel must be protected with authentication.

Requirements:

- basic auth;
- HTTPS;
- no public unrestricted admin access.

Credentials must be stored in `.env`.

---

# 11. Persistence

n8n workflows and credentials must persist between container restarts.

Persistent Docker volume is required.

---

# 12. Logging

n8n should log:

- incoming webhooks;
- failed workflows;
- backend connection failures;
- notification failures.

Sensitive credentials must not appear in logs.

---

# 13. Workflow Design Principles

n8n workflows should remain:

- simple;
- modular;
- reusable;
- channel-independent.

Business logic should not move into workflows.

---

# 14. What n8n Must NOT Do

n8n must not:

- directly manipulate PostgreSQL data;
- contain AI decision logic;
- contain complex lead qualification logic;
- replace backend services;
- store conversation state permanently.

These responsibilities belong to backend.

---

# 15. MVP Workflows

Initial MVP workflows:

## Workflow 1 — Incoming Message

Responsibilities:

- receive webhook;
- normalize payload;
- send request to backend;
- send response to customer.

---

## Workflow 2 — Owner Notification

Responsibilities:

- receive backend response;
- check `notify_owner`;
- send notification.

---

# 16. Future Scalability

Future improvements may include:

- separate workflows per channel;
- workflow templates;
- queue systems;
- async processing;
- distributed workers;
- advanced monitoring.

The MVP should remain simple and stable first.

---

# 17. Success Criteria

n8n architecture is successful if:

- incoming webhooks work;
- normalized payloads are generated;
- backend communication works;
- replies are sent correctly;
- owner notifications work;
- workflows survive restart;
- workflows remain understandable and maintainable.