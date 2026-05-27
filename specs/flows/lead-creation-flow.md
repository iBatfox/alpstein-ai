# Alpstein AI — Lead Creation Flow

## 1. Purpose

This document describes how Alpstein AI creates, updates, deduplicates, and routes leads.

Lead creation is one of the core business functions of the platform.

The goal is to make sure that every incoming customer contact is captured, stored, and optionally sent to the business owner's preferred system.

A lead may be stored in:

- Alpstein AI database;
- external CRM;
- Google Sheets / spreadsheet;
- customer-owned database;
- another integration selected by the client.

---

# 2. Main Principle

Every first customer contact should create or update a lead record.

However, the system must avoid duplicate leads.

The lead must be linked to:

- tenant;
- business;
- customer;
- conversation;
- channel;
- source platform.

---

# 3. High-Level Flow

```text
Customer sends first message
      ↓
n8n receives and normalizes message
      ↓
backend identifies tenant and business
      ↓
backend identifies or creates customer
      ↓
backend identifies or creates conversation
      ↓
backend checks for existing lead
      ↓
backend creates or updates lead
      ↓
backend stores lead in Alpstein AI database
      ↓
backend returns lead event
      ↓
n8n routes lead to selected client platform
      ↓
owner receives notification
```

---

# 4. When To Create A Lead

A lead should be created when:

- a customer sends the first incoming message;
- customer shows interest in a service;
- customer asks about booking;
- customer asks about price;
- customer asks about availability;
- customer asks for consultation;
- customer sends order-related message.

For MVP, the first incoming customer message should create a lead even if the intent is not fully clear yet.

Initial lead status may be:

```text
new
```

or:

```text
in_progress
```

---

# 5. When Not To Create A New Lead

A new lead should NOT be created when:

- the same message was already processed;
- an open lead already exists for the same customer and business;
- the message is part of an existing active conversation;
- the message is a duplicate webhook event;
- the message is from AI, owner, or system;
- the conversation is already linked to an active lead.

Instead of creating a new lead, the system should update the existing lead.

---

# 6. Duplicate Detection Rules

The system must check duplicates before creating a lead.

## 6.1 Message Deduplication

Use:

```text
external_message_id
```

If the same external message was already processed:

```text
do not create duplicate message
do not create duplicate lead
do not trigger duplicate notification
```

---

## 6.2 Customer Deduplication

MVP customer identity rule:

```text
business_id + phone
```

If a customer with the same phone already exists for the business, reuse existing customer.

---

## 6.3 Conversation Deduplication

Before creating a new conversation, check for an active conversation using:

```text
tenant_id
business_id
customer_id
channel
status != archived
```

If found, reuse the active conversation.

---

## 6.4 Lead Deduplication

Before creating a new lead, check for an existing active lead using:

```text
tenant_id
business_id
customer_id
conversation_id
status IN ('new', 'in_progress', 'contacted')
```

If active lead exists:

```text
update existing lead
```

If no active lead exists:

```text
create new lead
```

---

# 7. Lead Creation Logic

## Step 1 — Incoming Message Arrives

Backend receives normalized payload from n8n.

---

## Step 2 — Customer Is Created Or Reused

Backend finds customer by:

```text
business_id + phone
```

If not found, create new customer.

---

## Step 3 — Conversation Is Created Or Reused

Backend finds active conversation.

If not found, create new conversation.

---

## Step 4 — Lead Check

Backend checks whether an active lead already exists.

---

## Step 5 — Lead Create Or Update

If no active lead exists, create lead.

If active lead exists, update it with new information.

---

# 8. Initial Lead Fields

When lead is created, set:

```text
tenant_id
business_id
customer_id
conversation_id
source_channel
status
priority
customer_note
created_at
updated_at
```

Optional fields:

```text
service_requested
preferred_date
preferred_time
ai_summary
metadata
```

---

# 9. Lead Status Rules

## new

Lead was created but not yet processed.

Use when:

- first customer contact happened;
- not enough information is collected yet;
- owner has not contacted customer.

---

## in_progress

Lead is being qualified.

Use when:

- AI is asking clarifying questions;
- customer has not provided all required information.

---

## contacted

Business owner has contacted the customer.

---

## closed

Lead successfully converted into booking, order, or customer.

---

## lost

Lead did not convert.

---

# 10. Lead Priority Rules

Default priority:

```text
normal
```

Possible values:

```text
low
normal
high
urgent
```

Use `urgent` only when customer message indicates immediate action.

Example:

```text
I need help today.
Can you call me now?
Emergency request.
```

---

# 11. Lead Destination Strategy

A lead must always be stored in Alpstein AI database first.

After that, the lead may be routed to the client's selected destination.

Supported destination types:

```text
alpstein_database
crm
spreadsheet
customer_database
webhook
email
```

---

# 12. Client-Selected Lead Destination

Each business may choose where leads should be sent.

Examples:

## Alpstein AI only

```text
Lead stored only in Alpstein AI PostgreSQL.
```

## CRM

```text
Lead stored in Alpstein AI and sent to client's CRM.
```

Possible CRMs:

```text
Bitrix24
HubSpot
Pipedrive
Zoho
Other
```

## Spreadsheet

```text
Lead stored in Alpstein AI and added to Google Sheets / Excel / Airtable.
```

## Customer-Owned Database

```text
Lead stored in Alpstein AI and copied or routed to customer-owned database.
```

## Webhook

```text
Lead stored in Alpstein AI and sent to external webhook.
```

---

# 13. Routing Responsibility

Backend is responsible for:

- creating lead;
- saving lead;
- returning structured lead event.

n8n is responsible for:

- routing lead to CRM;
- routing lead to spreadsheet;
- routing lead to external webhook;
- sending owner notification.

This keeps backend clean and n8n focused on integrations.

---

# 14. Lead Event Returned To n8n

Backend should return lead event data.

Example:

```json
{
  "success": true,
  "data": {
    "reply_to_customer": "Thank you. I will ask a few questions to prepare your request.",
    "lead_created": true,
    "lead_updated": false,
    "lead": {
      "id": "8a6a3a5e-6c02-4b87-b8d4-12d10c86c111",
      "status": "new",
      "priority": "normal",
      "service_requested": null,
      "source_channel": "whatsapp"
    },
    "routing": {
      "destination_type": "crm",
      "destination_name": "HubSpot"
    },
    "notify_owner": true
  }
}
```

---

# 15. Lead Update Event

If duplicate active lead exists, backend should update it.

Example:

```json
{
  "success": true,
  "data": {
    "lead_created": false,
    "lead_updated": true,
    "lead": {
      "id": "8a6a3a5e-6c02-4b87-b8d4-12d10c86c111",
      "status": "in_progress"
    },
    "notify_owner": false
  }
}
```

---

# 16. Required Future Configuration

To support selected lead destinations, the system will need business-level configuration.

Future tables may include:

```text
tenant_integrations
lead_routing_rules
```

MVP can store basic routing settings inside:

```text
businesses.metadata
```

or:

```text
tenant_channel_settings.metadata
```

But future architecture should move routing configuration into a dedicated table.

---

# 17. Recommended Future Table: lead_routing_rules

Future table:

```text
lead_routing_rules
```

Purpose:

Defines where leads should be sent for each business.

Possible fields:

```text
id UUID PRIMARY KEY

tenant_id UUID NOT NULL
business_id UUID NOT NULL

destination_type VARCHAR(100) NOT NULL
destination_name VARCHAR(255)

is_active BOOLEAN DEFAULT true

settings JSONB

created_at TIMESTAMP NOT NULL
updated_at TIMESTAMP NOT NULL
```

Destination types:

```text
alpstein_database
crm
spreadsheet
customer_database
webhook
email
```

---

# 18. CRM / Spreadsheet / External Routing

For MVP, routing may be simulated or handled manually through n8n.

Future n8n workflows may include:

- create CRM lead;
- add row to Google Sheets;
- send email notification;
- call customer webhook;
- send data to external database.

---

# 19. Lead Notification Rules

Owner notification should be triggered when:

- a new lead is created;
- lead priority is urgent;
- AI needs human help;
- customer explicitly asks for human contact.

Owner notification may be skipped when:

- existing lead is only slightly updated;
- duplicate webhook event is detected;
- message does not require human attention.

---

# 20. AI Role In Lead Creation

AI can help extract:

- service_requested;
- preferred_date;
- preferred_time;
- customer_note;
- urgency;
- summary.

AI must not be the only source of truth for database decisions.

Backend business logic must decide whether to create or update the lead.

---

# 21. MVP Simplification

For MVP:

- create lead on first incoming customer message;
- deduplicate by customer + active conversation + active lead;
- store lead in Alpstein AI PostgreSQL;
- return lead event to n8n;
- use n8n for notification;
- external CRM/spreadsheet routing may be added later.

---

# 22. What Is Not Required In MVP

Not required in MVP:

- full CRM integration;
- Google Sheets automation;
- external database routing;
- complex lead scoring;
- advanced sales pipeline;
- assignment to real users;
- payment-based routing rules.

---

# 23. Success Criteria

Lead creation flow is successful if:

- first incoming message creates a lead;
- duplicate webhook messages do not create duplicate leads;
- active conversations reuse existing leads;
- leads are linked to tenant, business, customer, and conversation;
- lead status is predictable;
- n8n receives lead event;
- owner can be notified;
- future CRM/spreadsheet/customer database routing is not blocked.