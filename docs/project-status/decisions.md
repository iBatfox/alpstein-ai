**Doc status:** canonical (architecture decisions)  
**Tier:** project-status/current

# Alpstein AI — Architecture Decisions

---

## 2026-05-24 — Spec-Driven Development

Decision:
Use specs-first development workflow.

Description:
All implementation must follow specs/ documentation before coding.

Reason:
Reduce architecture drift and uncontrolled AI-generated code.

Implications:
- implementation follows specs
- agents must read specs before coding
- database schema must be documented before migrations

Review later:
after MVP completion

---

## 2026-05-24 — Multi-Tenant Architecture

Decision:
Use tenant-based architecture from MVP start.

Description:
All client-owned data must include tenant_id.
Business-scoped entities also include business_id.

Reason:
Avoid future migration complexity and cross-tenant leakage.

Alternatives rejected:
- single-tenant MVP
- business-only isolation

Review later:
after first production clients

---

## 2026-05-24 — Backend-Centric AI Orchestration

Decision:
Backend owns AI orchestration.

Description:
AI configuration, prompt building, knowledge retrieval, and AI provider calls are handled inside backend services.

n8n only handles:
- transport
- normalization
- notifications

Reason:
Prevent prompt logic duplication and transport coupling.

Alternatives rejected:
- prompt assembly in n8n
- AI orchestration in workflows

---

## 2026-05-24 — Shared PostgreSQL MVP

Decision:
Use shared PostgreSQL architecture for MVP.

Description:
All tenants use the same PostgreSQL database during MVP.

Future support for:
- dedicated DB
- external DB
- customer-owned DB

Reason:
Simpler deployment and faster MVP iteration.

Review later:
after scaling requirements appear

---

## 2026-05-24 — AI Safety Boundary

Decision:
Tenant configuration cannot override platform safety rules.

Description:
The platform owns the core system prompt and safety behavior.
Tenant AI profiles can customize:
- tone
- language
- business context
- escalation rules

Reason:
Prevent unsafe or broken tenant prompts.

---

## 2026-05-24 — Normalized Backend Contracts

Decision:
Backend accepts normalized payloads only.

Description:
Raw provider payloads are normalized in n8n before backend processing.

Reason:
Keep backend provider-independent.

Alternatives rejected:
- direct WhatsApp payload processing in backend
- provider-specific backend routes