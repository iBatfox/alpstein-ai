# Alpstein AI — Deployment Architecture

> **Portability (B2.1):** Env variable names, startup sequence, health semantics, and network boundaries are defined in [`docs/deployment/deployment-contract.md`](../../docs/deployment/deployment-contract.md). This spec remains the product/deployment vision; where names differ below (`DATABASE_URL`, `ENVIRONMENT`, host port `8010`), the **contract** is authoritative for clean-clone and Docker work.

## 1. Purpose

This document describes the deployment architecture for Alpstein AI MVP.

The MVP is deployed on a single production server using Docker Compose.

The deployment architecture is designed for:

- simplicity;
- fast MVP iteration;
- easy maintenance;
- future scalability.

---

# 2. Production Server

## Server Provider

```text
Contabo
```

## Server IP

```text
144.91.113.184
```

## Operating System

```text
Ubuntu Server 24.04 LTS
```

---

# 3. Production Domain

Main production domain:

```text
https://alpstein-ai.ch/
```

Future subdomains may include:

```text
api.alpstein-ai.ch
n8n.alpstein-ai.ch
admin.alpstein-ai.ch
```

---

# 4. Main Services

The MVP deployment includes:

```text
nginx
backend
postgres
n8n
```

Optional future services:

```text
redis
worker
frontend
monitoring
```

---

# 5. Docker Architecture

The project uses Docker Compose.

Recommended structure:

```text
alpstein-ai/
├── backend/
├── specs/
├── infrastructure/
├── docker/
├── docs/
├── docker-compose.yml
└── .env
```

---

# 6. Container Structure

```text
Docker Compose
├── nginx
├── backend
├── postgres
└── n8n
```

---

# 7. Service Responsibilities

## nginx

Responsibilities:

- reverse proxy;
- SSL termination;
- routing requests;
- security headers;
- future static frontend hosting.

---

## backend

Responsibilities:

- business logic;
- AI processing;
- database operations;
- API endpoints;
- lead management.

Runs on:

```text
port 8000
```

Internal only.

---

## postgres

Responsibilities:

- persistent relational storage;
- conversations;
- customers;
- leads;
- businesses.

Must not be publicly accessible.

---

## n8n

Responsibilities:

- webhook processing;
- automation workflows;
- integrations;
- notifications;
- message orchestration.

Runs on:

```text
port 5678
```

Should be protected with authentication.

---

# 8. Network Architecture

## Public Traffic

```text
Internet
    ↓
Nginx
    ↓
backend / n8n
```

---

## Internal Docker Network

```text
n8n → backend
backend → postgres
```

PostgreSQL must only be accessible inside Docker network.

---

# 9. HTTPS / SSL

SSL is required for production.

SSL certificates should be managed with:

```text
Let's Encrypt
Certbot
```

Main domain:

```text
https://alpstein-ai.ch
```

Nginx is responsible for SSL termination.

---

# 10. Environment Variables

Sensitive configuration must be stored in `.env`. **Canonical names:** see [`docs/deployment/deployment-contract.md`](../../docs/deployment/deployment-contract.md) §5 and git templates `backend/.env.example`, `n8n/.env.example`.

Example (portable baseline):

```env
ALPSTEIN_AI_DATABASE_URL=postgresql+asyncpg://alpstein:password@postgres:5432/alpstein_ai
ALPSTEIN_AI_ENVIRONMENT=production
N8N_BACKEND_API_TOKEN=
OPENAI_API_KEY=
```

n8n admin (separate `n8n/.env`): `N8N_BASIC_AUTH_USER`, `N8N_BASIC_AUTH_PASSWORD`, `BACKEND_BASE_URL=http://backend:8000`.

**Deprecated (do not use in new deploys):** `DATABASE_URL`, `ENVIRONMENT`, `SECRET_KEY` (not implemented in backend `Settings`).

`.env` must never be committed to git.

---

# 11. Backend Deployment

Backend runs inside Docker container.

Start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Backend should not be exposed directly to the internet.

All public access should go through nginx.

---

# 12. Database Deployment

PostgreSQL runs in Docker container with persistent volume.

Requirements:

- persistent storage;
- automatic restart;
- regular backups;
- private internal network only.

---

# 13. n8n Deployment

n8n runs in Docker container.

Requirements:

- persistent workflows;
- basic authentication;
- webhook support;
- internal communication with backend.

n8n admin panel should not remain publicly unprotected.

---

# 14. Logging

The deployment should support logs for:

- nginx;
- backend;
- postgres;
- n8n.

Docker logs are acceptable for MVP.

Future versions may include centralized logging.

---

# 15. Backup Strategy

Minimum MVP backup requirements:

- PostgreSQL database backups;
- n8n workflow backups;
- `.env` secure storage.

Backups should be stored outside the main container filesystem.

---

# 16. Security Principles

The production environment must follow basic security rules:

- HTTPS only;
- protected n8n admin;
- private PostgreSQL;
- Docker network isolation;
- no hardcoded secrets;
- environment variables for credentials;
- firewall configuration;
- regular updates.

---

# 17. Scalability Principles

The MVP starts as a single-server deployment.

Future scaling options:

- separate backend server;
- dedicated database server;
- Redis queue;
- background workers;
- Kubernetes;
- load balancer;
- monitoring stack.

The initial architecture should allow gradual scaling without complete rewrite.

---

# 18. Deployment Success Criteria

Deployment is successful if:

- domain resolves correctly;
- HTTPS works;
- nginx routes requests correctly;
- backend is reachable internally;
- n8n workflows run correctly;
- PostgreSQL persists data;
- Docker containers restart automatically;
- system survives reboot;
- production demo is stable.