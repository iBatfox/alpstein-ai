# Alpstein AI — Database Architecture

## 1. Purpose

This document describes the database architecture for Alpstein AI MVP and future versions.

The database architecture must support:

- secure storage of customer conversations;
- lead management;
- business separation;
- future multi-tenant SaaS model;
- future dedicated database per client;
- future customer-owned database option.

The main goal is to store customer communication data safely and in a structured way.

---

# 2. Database Technology

The MVP uses:

```text
PostgreSQL
```

PostgreSQL is selected because it supports:

- relational data;
- strong consistency;
- transactions;
- indexes;
- JSON fields if needed;
- future scalability;
- managed cloud options such as AWS RDS, Google Cloud SQL, Azure PostgreSQL.

---

# 3. MVP Storage Model

The MVP uses one shared PostgreSQL database.

```text
Alpstein AI PostgreSQL
├── tenant A data
├── tenant B data
└── tenant C data
```

In MVP, all customer data is stored in one database, but every client-owned record must be separated by `tenant_id`.

This allows future migration to:

- dedicated database per client;
- customer-owned database;
- cloud-managed database.

---

# 4. Multi-Tenant Principle

Alpstein AI must be designed as a multi-tenant system.

A tenant represents the owner of business data.

Example:

```text
Tenant: Restaurant Group AG
├── Business: Zurich branch
├── Business: St. Gallen branch
└── Business: Appenzell branch
```

In the simplest MVP case:

```text
1 tenant = 1 business
```

But the database must not assume that this will always be true.

---

# 5. Tenant Isolation

Every table that stores client-owned data must include:

```text
tenant_id
business_id
```

Required tables with tenant isolation:

- businesses
- customers
- conversations
- messages
- leads
- events

The system must never query customer data without tenant filtering.

Bad example:

```sql
SELECT * FROM messages;
```

Good example:

```sql
SELECT * FROM messages WHERE tenant_id = :tenant_id;
```

This rule is critical for customer data protection.

---

# 6. Storage Modes

The system should support three future storage modes.

## 6.1 Shared Database

Default MVP mode.

All clients use one Alpstein AI database.

Data is separated by:

```text
tenant_id
business_id
```

Best for:

- MVP;
- small businesses;
- low-cost plans;
- fast onboarding.

---

## 6.2 Dedicated Database Per Client

Each client gets a separate database.

Example:

```text
alpstein_client_001_db
alpstein_client_002_db
```

Best for:

- medium-sized businesses;
- higher security requirements;
- easier per-client backup;
- better client trust.

This is not implemented in MVP, but architecture must allow it later.

---

## 6.3 Customer-Owned Database

The client provides their own database.

Possible providers:

- AWS RDS PostgreSQL;
- Google Cloud SQL PostgreSQL;
- Azure Database for PostgreSQL;
- self-hosted PostgreSQL;
- other managed PostgreSQL providers.

In this mode, Alpstein AI backend connects to the customer database through a secure connection.

Best for:

- clients with strict data policies;
- clients who want full control over their data;
- larger companies;
- compliance-sensitive businesses.

This is not implemented in MVP, but the architecture must be prepared for it.

---

# 7. Recommended Storage Strategy

## MVP

Use:

```text
shared PostgreSQL database with tenant isolation
```

Implemented now.

---

## Future Standard Plan

Use:

```text
shared PostgreSQL database
```

For small clients.

---

## Future Business Plan

Use:

```text
dedicated database per client
```

For clients who need stronger isolation.

---

## Future Enterprise / Custom Plan

Use:

```text
customer-owned database
```

For clients who require control over their data infrastructure.

---

# 8. Required Core Entities

The database must include the following core entities:

```text
tenants
businesses
customers
conversations
messages
leads
database_connections
```

Future entities may include:

```text
events
audit_logs
users
subscriptions
integrations
```

---

# 9. Core Entity Responsibilities

## 9.1 tenants

Represents a client account or data owner.

A tenant can own one or more businesses.

---

## 9.2 businesses

Represents a specific business location, brand, or service.

Example:

```text
Barbershop A
Restaurant B
Shawarma Shop C
```

Each business belongs to a tenant.

---

## 9.3 customers

Represents end customers who write messages to the business.

Each customer belongs to:

```text
tenant_id
business_id
```

---

## 9.4 conversations

Represents communication sessions between customers and AI/business.

Each conversation belongs to:

```text
tenant_id
business_id
customer_id
```

---

## 9.5 messages

Stores incoming and outgoing messages.

Messages may come from:

```text
customer
ai
owner
system
```

Each message belongs to:

```text
tenant_id
business_id
conversation_id
```

---

## 9.6 leads

Stores business opportunities created from conversations.

A lead belongs to:

```text
tenant_id
business_id
customer_id
conversation_id
```

---

## 9.7 database_connections

Stores metadata about external or dedicated database connections.

This table is for future storage modes.

Sensitive credentials must not be stored as plain text.

---

# 10. Data Ownership

All customer data belongs to the business client.

Customer data includes:

- customer phone number;
- customer name;
- conversation history;
- messages;
- lead details;
- notes;
- service requests.

Alpstein AI processes this data only to provide the service.

---

# 11. Data Security Principles

The database architecture must follow these principles:

- data must be separated by tenant;
- PostgreSQL must not be publicly accessible;
- all database credentials must be stored securely;
- access must be limited to backend service;
- n8n must not write directly to PostgreSQL in MVP;
- AI must not access database directly;
- backups must be protected;
- logs must not expose sensitive data.

---

# 12. Direct Database Access Rules

Allowed:

```text
Python Backend → PostgreSQL
```

Not allowed in MVP:

```text
n8n → PostgreSQL direct write
AI → PostgreSQL direct access
External channel → PostgreSQL
```

Reason:

- avoid duplicated business logic;
- reduce risk of inconsistent data;
- improve security;
- simplify debugging.

---

# 13. Sensitive Data Handling

Sensitive data may include:

- phone numbers;
- emails;
- conversation text;
- customer names;
- addresses;
- business credentials;
- external database credentials.

Rules:

- never store secrets in source code;
- never commit `.env`;
- never store database passwords as plain text;
- mask sensitive data in logs;
- restrict database access;
- use SSL where possible.

---

# 14. External Database Connection Strategy

Future external database connections should be described using metadata.

Example fields:

```text
id
tenant_id
business_id
provider
connection_type
host
port
database_name
username
encrypted_password_reference
ssl_required
status
created_at
updated_at
```

Important:

The database should not store raw passwords directly.

Use one of:

- encrypted secret storage;
- external secret manager;
- environment variables;
- AWS Secrets Manager;
- HashiCorp Vault;
- Doppler;
- Infisical.

For MVP, external database support is only documented, not implemented.

---

# 15. Data Processing Flow

## Default MVP Flow

```text
n8n receives message
      ↓
n8n sends normalized payload to backend
      ↓
backend writes data to shared PostgreSQL
      ↓
backend processes AI response
      ↓
backend creates lead if needed
      ↓
backend returns response to n8n
```

---

## Future External Database Flow

```text
n8n receives message
      ↓
n8n sends normalized payload to backend
      ↓
backend identifies tenant storage_mode
      ↓
backend selects correct database connection
      ↓
backend writes data to customer-owned database
      ↓
backend processes AI response
      ↓
backend returns response to n8n
```

---

# 16. Backup Strategy

## MVP Backup

Minimum requirements:

- daily PostgreSQL dump;
- backup stored outside container;
- backup not stored only inside Docker volume;
- restore process documented.

---

## Future Backup Options

Future options:

- per-tenant backup;
- per-client database backup;
- cloud-managed automated backups;
- encrypted backups;
- backup retention policy.

---

# 17. Data Retention

The MVP should store data until manually deleted.

Future versions should support:

- configurable data retention;
- delete old conversations;
- export tenant data;
- delete tenant data;
- customer data removal requests.

---

# 18. Compliance Direction

The system should be designed with privacy and data protection in mind.

Important future considerations:

- Swiss data protection requirements;
- GDPR-style data rights;
- right to export data;
- right to delete data;
- clear client data ownership;
- processing only necessary data.

MVP does not implement full compliance automation, but architecture must not block it.

---

# 19. What Is Implemented In MVP

Implemented in MVP:

- shared PostgreSQL database;
- tenant_id-based data separation;
- business_id-based data separation;
- core tables;
- backend-only database writes;
- no public database access.

---

# 20. What Is Not Implemented In MVP

Not implemented in MVP:

- customer-owned database connection;
- dedicated database per client;
- automatic database provisioning;
- secret manager integration;
- per-tenant backup automation;
- data retention UI;
- advanced compliance tools;
- encryption at application field level.

These features may be added after the MVP is stable.

---

# 21. Database Architecture Success Criteria

Database architecture is successful if:

- all client-owned data has `tenant_id`;
- all business-specific data has `business_id`;
- backend can store customers, conversations, messages, and leads;
- n8n does not write directly to database;
- PostgreSQL is not publicly accessible;
- future storage modes are not blocked by current schema;
- data can be separated by tenant;
- backup strategy is possible;
- customer security can be explained clearly during sales.