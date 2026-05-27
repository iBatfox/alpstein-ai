**Doc status:** deprecated  
**Tier:** project-status/historical (pending move)

# Alpstein AI Backlog

**Status:** **obsolete** — pre-MVP checklist from early project phase. Do not use for planning. Canonical queue: [`next-steps.md`](../next-steps.md). Shipped work: [`completed.md`](../completed.md).

---

## P0 — Infrastructure

- [ ] Docker Compose base stack
- [ ] PostgreSQL container
- [ ] FastAPI service
- [ ] n8n service
- [ ] Nginx reverse proxy
- [ ] HTTPS for alpstein-ai.ch

---

## P0 — Database Foundation

- [ ] tenants table
- [ ] businesses table
- [ ] customers table
- [ ] conversations table
- [ ] messages table
- [ ] leads table
- [ ] indexes and tenant isolation

---

## P0 — Backend Core

- [ ] FastAPI app structure
- [ ] database session layer
- [ ] repositories
- [ ] webhook endpoint
- [ ] validation schemas
- [ ] error envelope

---

## P0 — AI Layer

- [ ] AI Gateway Service
- [ ] Prompt Builder Service
- [ ] AI Configuration Service
- [ ] Knowledge Retrieval Service
- [ ] PromptRun logging

---

## P0 — Message Flow

- [ ] incoming-message-flow
- [ ] conversation creation
- [ ] customer creation
- [ ] AI reply generation
- [ ] message persistence
- [ ] lead creation
- [ ] notification trigger

---

## P0 — n8n Integration

- [ ] WhatsApp webhook
- [ ] normalization flow
- [ ] backend HTTP call
- [ ] customer reply flow
- [ ] Telegram notification flow

---

## P1 — Business Features

- [ ] tenant AI profiles
- [ ] business profiles
- [ ] knowledge sources
- [ ] channel settings

---

## P1 — Stability

- [ ] duplicate message protection
- [ ] logging
- [ ] retries
- [ ] error handling
- [ ] monitoring

---

## P2 — Future

- [ ] CRM integrations
- [ ] dashboard
- [ ] analytics
- [ ] vector search