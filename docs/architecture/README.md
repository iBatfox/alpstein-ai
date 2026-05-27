# Architecture Documentation

**Doc status:** canonical (navigation layer)  
**As-of:** 2026-05-27

---

## Primary canonical document

**[`canonical-runtime-architecture.md`](canonical-runtime-architecture.md)**

**START HERE →** [`canonical-runtime-architecture.md`](canonical-runtime-architecture.md)

- **Tier:** canonical
- **Scope:** Actual runtime architecture only (backend, n8n, PromptBuilder, DB, Telegram, observability)
- **Use when:** Onboarding engineers, auditing drift, resolving doc conflicts
- **Does not:** Describe planned systems as shipped; replace `specs/` contracts

All other architecture docs in this folder are **supporting** — verify against the canonical map.

---

## Runtime truth hierarchy (architecture)

1. Runtime code (`backend/app/services/`, `n8n/workflows/`)
2. Backend orchestration + prompt assembly entrypoints (services) and n8n workflow shapes (how code is exercised)
3. [`canonical-runtime-architecture.md`](canonical-runtime-architecture.md) (canonical runtime map)
4. Runtime-derived docs below (behavior detail; must match the map)
5. [`specs/architecture/`](../../specs/architecture/) — contract; drift → map §12

---

## Current documents (physical paths)

| Document | Doc status | Relationship to canonical map |
|----------|------------|----------------------------------|
| [`canonical-runtime-architecture.md`](canonical-runtime-architecture.md) | **canonical** | Primary source |
| [`greeting-orchestration-mvp.md`](greeting-orchestration-mvp.md) | runtime-derived | §6 greeting — **implemented** |
| [`conversation-intent-policy-mvp.md`](conversation-intent-policy-mvp.md) | runtime-derived | §6 intent — **partial** (one business) |
| [`operator-business-context-n8n.md`](operator-business-context-n8n.md) | runtime-derived | §4 operator context — **implemented** |
| [`pre-sales-contact-ownership.md`](pre-sales-contact-ownership.md) | runtime-derived | Contact rules — backend **done**, n8n ops **partial** |
| [`langfuse-tracing.md`](langfuse-tracing.md) | runtime-derived | §11 observability — **partial** (CIP-C D2) |
| [`../../specs/architecture/observability-metadata.md`](../../specs/architecture/observability-metadata.md) | **canonical (D1)** | Correlation, lineage, Langfuse mapping — **spec only** |
| [`telegram-channel-credentials.md`](telegram-channel-credentials.md) | runtime-derived | §8 Telegram — dual-bot model |
| [`technical-pre-sales-behavior-mvp.md`](technical-pre-sales-behavior-mvp.md) | **deprecated** | Legacy appendix era; see CIP + canonical §5 |

---

## Tier directories (target; migration pending)

| Directory | Purpose |
|-----------|---------|
| [`canonical/`](canonical/) | Stable platform architecture (future splits from runtime map) |
| [`runtime/`](runtime/) | Runtime-derived supplements moved from root |
| [`deprecated/`](deprecated/) | Obsolete and superseded architecture notes — [**index**](deprecated/README.md) |
| [`experiments/`](experiments/) | Non-production experiments and drafts |

See [`../MIGRATION-PLAN.md`](../MIGRATION-PLAN.md).

---

## Deprecated / do not use for runtime truth

Listed in [`deprecated/README.md`](deprecated/README.md), including:

- `deprecated/t11-prompt-builder-design.md` (superseded by spec)
- `technical-pre-sales-behavior-mvp.md` (partially obsolete after CIP-B)
- Early slice plans in `../project-status/t11-*`, `t12-*`, `t13-*`

---

## Specs (outside this folder)

Contract source of truth: [`specs/architecture/`](../../specs/architecture/), [`specs/api/webhooks.md`](../../specs/api/webhooks.md).

If spec ≠ runtime, canonical map §12 drift table wins for **behavior**; spec wins for **intended contract** until amended.
