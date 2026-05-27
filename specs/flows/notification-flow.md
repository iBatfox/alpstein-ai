# Alpstein AI — Notification Flow

## 1. Purpose

This document describes how notifications work inside Alpstein AI.

Notifications are responsible for informing business owners, operators, or external systems about important events.

The notification system must be:

- tenant-aware;
- configurable;
- channel-independent;
- event-driven;
- scalable.

The MVP notification system focuses on:

- new lead notifications;
- urgent lead notifications;
- human handoff notifications;
- AI failure notifications.

---

# 2. Main Principle

The backend generates notification events.

n8n is responsible for delivering notifications.

This separation keeps:

- backend focused on business logic;
- n8n focused on integrations and automation.

---

# 3. High-Level Flow

```text
Customer sends message
      ↓
Backend processes message
      ↓
Backend detects important event
      ↓
Backend returns notification event
      ↓
n8n receives event
      ↓
n8n checks notification rules
      ↓
n8n sends notification
      ↓
Business owner receives notification
```

---

# 4. Notification Types

The system should support different notification types.

## MVP Notification Types

```text
new_lead
urgent_lead
human_handoff
ai_failure
system_error
```

---

# 5. Notification Triggers

## 5.1 New Lead Notification

Triggered when:

```text
lead_created = true
```

Purpose:

Inform business owner that a new customer contact appeared.

---

## 5.2 Urgent Lead Notification

Triggered when:

```text
lead.priority = urgent
```

Examples:

```text
Emergency request
Need immediate help
Call me now
```

Urgent notifications should bypass delays.

---

## 5.3 Human Handoff Notification

Triggered when AI decides that human attention is required.

Examples:

- customer is angry;
- unclear business situation;
- unsupported request;
- customer explicitly asks for human.

Backend response example:

```json
{
  "notify_owner": true,
  "handoff_required": true
}
```

---

## 5.4 AI Failure Notification

Triggered when:

- AI provider unavailable;
- AI timeout;
- AI response invalid;
- prompt builder failed.

Purpose:

Allow owner or admin to react quickly.

---

## 5.5 System Error Notification

Triggered when critical backend/system errors occur.

Examples:

- database unavailable;
- webhook failure;
- repeated retries;
- integration failure.

---

# 6. Notification Architecture

## Backend Responsibilities

Backend is responsible for:

- detecting events;
- deciding notification importance;
- returning structured notification data.

Backend must not:

- directly send Telegram messages;
- directly send WhatsApp notifications;
- directly send emails.

---

## n8n Responsibilities

n8n is responsible for:

- routing notifications;
- formatting notifications;
- sending notifications;
- retrying failed notifications;
- integrating external services.

---

## 6.1 Telegram bots — owner notify vs customer channel (architecture)

Alpstein uses **two separate Telegram bot credentials** in n8n. They must not be shared.

| Role | Bot ownership | Used for | Token storage |
|------|---------------|----------|---------------|
| **Owner notification** | Alpstein-owned (deployment / ops) | `notify_owner` branch — alerts to business owner `chat_id` | n8n encrypted credential + env chat ID; **not** in PostgreSQL plaintext |
| **Customer ingress + reply** | Client-owned per business | Telegram Trigger + customer `sendMessage` | Client token at onboarding → n8n credential **reference only** in backend `tenant_channel_settings.metadata`; **no token in DB, repo, logs, or workflow JSON** |

Backend never calls Telegram APIs. Backend returns `notify_owner` and optional `notification` fields only.

Customer-facing bots must **not** reuse owner-notification bot tokens.

Canonical design: [`docs/architecture/telegram-channel-credentials.md`](../../docs/architecture/telegram-channel-credentials.md).

Token rotation: revoke in BotFather, update n8n credential; backend stores metadata reference only — no token column to migrate.

---

# 7. Notification Channels

## MVP Channels

```text
Telegram
Email
WhatsApp
```

Telegram is recommended for MVP because it is simple and fast.

---

## Future Channels

```text
Slack
Discord
SMS
Push notifications
CRM notifications
Mobile app notifications
```

---

# 8. Notification Configuration

Each tenant/business should configure:

- notification channels;
- notification types;
- notification recipients;
- urgency rules.

Future configuration may include:

```text
tenant_notification_settings
```

---

# 9. Notification Event Structure

Backend should return normalized notification event.

Example:

```json
{
  "success": true,
  "data": {
    "reply_to_customer": "Thank you. We will contact you shortly.",
    "lead_created": true,
    "notify_owner": true,
    "notification": {
      "type": "new_lead",
      "priority": "normal",
      "tenant_id": "tenant_001",
      "business_id": "business_001",
      "conversation_id": "conversation_001",
      "lead_id": "lead_001",
      "customer_name": "John",
      "customer_phone": "+41790000000",
      "message_preview": "Hello, I want to book tomorrow.",
      "channel": "whatsapp",
      "created_at": "2026-05-21T10:00:00Z"
    }
  }
}
```

---

# 10. Notification Priorities

Possible priorities:

```text
low
normal
high
urgent
critical
```

---

## low

Non-important informational event.

---

## normal

Default notification.

---

## high

Important lead or escalation.

---

## urgent

Immediate action required.

---

## critical

System-level failure requiring fast intervention.

---

# 11. Notification Routing

n8n decides where to send notification.

Routing may depend on:

- tenant;
- business;
- notification type;
- urgency;
- time of day;
- business hours.

---

# 12. Business Hours Rules

Future versions may support:

```text
business hours notification logic
```

Examples:

```text
urgent → always notify
normal → notify only during business hours
low → batch notification later
```

MVP can ignore business-hour logic initially.

---

# 13. Telegram Notification Example

Example message:

```text
🚨 New Lead

Business: Demo Barbershop
Customer: John
Phone: +41790000000
Channel: WhatsApp

Message:
"Hello, I want to book tomorrow."

Priority: normal
```

---

# 14. Email Notification Example

Example:

```text
Subject:
New Lead — Demo Barbershop

Body:
A new lead has been created.

Customer:
John
+41790000000

Message:
Hello, I want to book tomorrow.
```

---

# 15. WhatsApp Notification Example

Example:

```text
New Lead:
John
+41790000000

Message:
Hello, I want to book tomorrow.
```

---

# 16. Notification Deduplication

The system must avoid duplicate notifications.

Duplicate prevention should use:

```text
external_message_id
lead_id
notification_type
```

Duplicate webhook retries must not generate multiple owner notifications.

---

# 17. Notification Retry Strategy

n8n should retry failed notification delivery.

Examples:

- Telegram unavailable;
- email provider timeout;
- WhatsApp API unavailable.

Future retry strategy:

```text
retry 3 times
exponential backoff
dead-letter handling
```

MVP may use simpler retry logic.

---

# 18. Notification Logging

Notification delivery attempts should be logged.

Future table:

```text
notification_logs
```

Possible fields:

```text
tenant_id
business_id
notification_type
channel
recipient
status
error
created_at
```

MVP may use n8n execution logs instead.

---

# 19. AI Escalation Rules

AI should request human help when:

- customer becomes aggressive;
- business rules are unclear;
- pricing unavailable;
- scheduling uncertain;
- customer explicitly requests human;
- AI confidence is low.

Example backend response:

```json
{
  "notify_owner": true,
  "handoff_required": true,
  "notification": {
    "type": "human_handoff",
    "priority": "high"
  }
}
```

---

# 20. Notification Safety Rules

Notifications must not:

- expose internal prompts;
- expose API keys;
- expose system instructions;
- expose sensitive internal metadata.

Notifications should contain only operationally useful information.

---

# 21. Future Notification Tables

Future entities may include:

```text
tenant_notification_settings
notification_logs
notification_templates
notification_channels
```

---

# 22. Future Features

Future notification features may include:

- batching;
- quiet hours;
- escalation chains;
- operator assignment;
- CRM notifications;
- push notifications;
- mobile app alerts;
- AI-generated summaries.

---

# 23. MVP Simplification

For MVP:

- notifications may be handled only by Telegram;
- routing rules may be static;
- no batching required;
- no advanced scheduling required;
- no multi-operator support required.

---

# 24. What Is Not Required In MVP

Not required yet:

- advanced notification center;
- operator load balancing;
- SLA tracking;
- push notification infrastructure;
- notification analytics;
- escalation chains;
- AI notification scoring.

---

# 25. Success Criteria

Notification flow is successful if:

- important events trigger notifications;
- duplicate messages do not trigger duplicate notifications;
- owners receive lead alerts;
- urgent requests are prioritized;
- AI escalation works;
- backend remains notification-channel independent;
- n8n handles delivery and routing cleanly.