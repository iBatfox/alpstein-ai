# Alpstein AI — Backend Architecture

## 1. Purpose

This document describes the backend architecture of Alpstein AI MVP.

The backend is the core business logic layer of the system.

It receives normalized messages from n8n, processes them, communicates with AI, stores data in PostgreSQL, creates leads, and returns structured responses back to n8n.

The backend must stay clean, modular, testable, and independent from specific messenger APIs.

---

# 2. Backend Role In The System

The backend does not communicate directly with WhatsApp, Telegram, Instagram, or website chat widgets.

External communication channels are handled by n8n.

The backend receives only normalized JSON payloads from n8n.

Main backend responsibilities:

- validate incoming requests;
- identify business;
- identify or create customer;
- create or update conversation;
- store incoming messages;
- prepare AI context;
- call AI provider;
- store AI response;
- detect lead information;
- create or update lead;
- return structured result to n8n.

---

# 3. Backend Technology Stack

The backend uses:

- Python 3.11+
- FastAPI
- Pydantic
- SQLAlchemy
- Alembic
- PostgreSQL
- asyncpg
- httpx
- python-dotenv
- pydantic-settings

The backend should be prepared for Docker deployment.

---

# 4. Backend Project Structure

Recommended structure:

```text
backend/
├── app/
│   ├── main.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── health.py
│   │   │   ├── messages.py
│   │   │   ├── businesses.py
│   │   │   ├── leads.py
│   │   │   └── conversations.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   └── security.py
│   ├── db/
│   │   ├── __init__.py
│   │   ├── session.py
│   │   └── base.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── business.py
│   │   ├── customer.py
│   │   ├── conversation.py
│   │   ├── message.py
│   │   └── lead.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── business.py
│   │   ├── customer.py
│   │   ├── conversation.py
│   │   ├── message.py
│   │   ├── lead.py
│   │   └── webhook.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ai_service.py
│   │   ├── message_service.py
│   │   ├── lead_service.py
│   │   └── business_service.py
│   └── utils/
│       ├── __init__.py
│       └── logger.py
├── alembic/
├── alembic.ini
├── requirements.txt
├── Dockerfile
└── README.md
```

---

# 5. Backend Layers

## 5.1 API Layer

The API layer contains FastAPI routes.

Responsibilities:

- receive HTTP requests;
- validate request schemas;
- call service layer;
- return response schemas.

The API layer must not contain business logic.

Example route files:

- `health.py`
- `messages.py`
- `businesses.py`
- `leads.py`
- `conversations.py`

---

## 5.2 Schema Layer

The schema layer contains Pydantic models.

Responsibilities:

- define request formats;
- define response formats;
- validate input data;
- keep API contracts explicit.

Schemas should be placed in:

```text
app/schemas/
```

Important schema files:

- `webhook.py`
- `business.py`
- `customer.py`
- `message.py`
- `lead.py`
- `conversation.py`

---

## 5.3 Service Layer

The service layer contains business logic.

Responsibilities:

- process incoming messages;
- manage conversations;
- prepare AI context;
- call AI service;
- detect lead intent;
- create or update leads;
- return structured result.

Services should be placed in:

```text
app/services/
```

Important service files:

- `message_service.py`
- `ai_service.py`
- `lead_service.py`
- `business_service.py`

---

## 5.4 Database Layer

The database layer contains:

- SQLAlchemy models;
- database session;
- base metadata;
- Alembic migrations.

Database files:

```text
app/db/session.py
app/db/base.py
app/models/
```

Only backend services should access the database.

n8n must not write directly to PostgreSQL in MVP.

---

## 5.5 Core Layer

The core layer contains application configuration and security helpers.

Files:

```text
app/core/config.py
app/core/security.py
```

Config should load values from environment variables.

---

# 6. Backend API Endpoints

## 6.1 Health Check

```http
GET /health
```

Purpose:

Check that backend is running.

Example response:

```json
{
  "status": "ok",
  "service": "alpstein-ai-backend"
}
```

---

## 6.2 Incoming Message Webhook

```http
POST /webhook/message
```

Purpose:

Main endpoint used by n8n to send normalized incoming messages.

Request example:

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

Response example:

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

---

## 6.3 Create Business

```http
POST /businesses
```

Purpose:

Create a test business profile.

---

## 6.4 Get Business

```http
GET /businesses/{business_id}
```

Purpose:

Return business data by internal or external ID.

---

## 6.5 Get Leads

```http
GET /leads
```

Purpose:

Return created leads.

---

## 6.6 Get Conversation

```http
GET /conversations/{conversation_id}
```

Purpose:

Return conversation history.

---

# 7. Incoming Message Processing Flow

The backend must process incoming message requests in the following order:

1. Receive request from n8n.
2. Validate payload with Pydantic schema.
3. Find business by `business_id`.
4. Find or create customer by phone and business.
5. Find or create conversation.
6. Save incoming customer message.
7. Load recent conversation history.
8. Build AI context.
9. Send context to AI provider.
10. Receive AI response.
11. Save AI response as message.
12. Detect whether lead should be created or updated.
13. Create or update lead.
14. Return structured response to n8n.

---

# 8. AI Service Responsibilities

The AI service should be responsible only for AI-related operations.

Responsibilities:

- build AI prompt;
- include business context;
- include recent conversation history;
- send request to OpenAI API;
- receive AI response;
- return normalized AI result to message service.

The AI service must not:

- access database directly;
- send messages to customers;
- notify business owner;
- create leads directly.

---

# 9. Message Service Responsibilities

The message service is the main orchestration service for incoming messages.

Responsibilities:

- receive validated message payload;
- coordinate business service;
- coordinate customer/conversation logic;
- call AI service;
- call lead service;
- return final response.

The message service is the main backend entry point after the API route.

---

# 10. Lead Service Responsibilities

The lead service manages lead creation and updates.

Responsibilities:

- detect if enough information exists to create a lead;
- create new lead;
- update existing lead;
- assign lead status;
- return lead summary.

Initial lead statuses:

```text
new
in_progress
contacted
closed
lost
```

---

# 11. Business Service Responsibilities

The business service manages business data.

Responsibilities:

- create business;
- get business by ID;
- provide business context for AI;
- provide business prompt;
- manage business settings in future versions.

---

# 12. Database Access Rules

Backend is the only component allowed to write to PostgreSQL.

Rules:

- API routes must not write to database directly;
- services use database session;
- AI service should not write to database directly;
- n8n should not write to database directly;
- all database changes should happen through backend service logic.

---

# 13. Error Handling

The backend must handle common error cases.

Examples:

- invalid payload;
- missing business;
- database unavailable;
- AI provider unavailable;
- empty message text;
- unsupported channel.

Error responses should be structured.

Example:

```json
{
  "success": false,
  "error": {
    "code": "BUSINESS_NOT_FOUND",
    "message": "Business was not found"
  }
}
```

---

# 14. Logging

The backend must log:

- incoming webhook requests;
- validation errors;
- database errors;
- AI provider errors;
- lead creation events;
- unexpected exceptions.

Logs must not expose:

- OpenAI API keys;
- database passwords;
- private credentials.

---

# 15. Configuration

Configuration must be loaded from environment variables. **Canonical template:** `backend/.env.example` and [`docs/deployment/deployment-contract.md`](../../docs/deployment/deployment-contract.md) §5.

Required values:

```env
ALPSTEIN_AI_DATABASE_URL=postgresql+asyncpg://alpstein:password@postgres:5432/alpstein_ai
ALPSTEIN_AI_ENVIRONMENT=development
N8N_BACKEND_API_TOKEN=
OPENAI_API_KEY=
```

**Deprecated:** `DATABASE_URL`, `ENVIRONMENT`, `SECRET_KEY` (reserved — not in `app.core.config.Settings`).

---

# 16. Docker Requirements

The backend must be runnable in Docker.

Backend Dockerfile should:

- use Python 3.11+ image;
- install requirements;
- copy application code;
- expose port 8000;
- run FastAPI with Uvicorn.

Run command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

# 17. MVP Limitations

The backend MVP must not include:

- frontend dashboard;
- billing logic;
- direct WhatsApp integration;
- direct Telegram integration;
- direct Instagram integration;
- advanced authentication;
- vector database;
- multi-agent system;
- background job queue;
- complex analytics;
- self-service onboarding.

These features can be added later.

---

# 18. Backend Success Criteria

The backend architecture is successful if:

- FastAPI application starts correctly;
- `/health` returns status ok;
- `/webhook/message` accepts normalized n8n payload;
- backend returns structured response;
- database models are defined;
- messages can be stored;
- leads can be created;
- code structure follows the architecture;
- n8n can call backend without knowing internal business logic.

---

# 19. Development Rule

Do not implement future features before the MVP message flow works.

Backend development priority:

1. Project structure.
2. Health endpoint.
3. Database connection.
4. Basic models.
5. Webhook message endpoint.
6. Message storage.
7. Mock AI response.
8. Lead creation.
9. Real AI integration.
10. n8n integration test.