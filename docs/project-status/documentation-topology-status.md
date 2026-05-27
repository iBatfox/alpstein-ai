# Documentation Topology Status

**Doc status:** canonical  
**As-of:** 2026-05-27  
**Phase:** 1.2 — documentation topology stabilization

Primary anchor: [`../architecture/canonical-runtime-architecture.md`](../architecture/canonical-runtime-architecture.md)

Navigation: [`../README.md`](../README.md) · Migration plan: [`../MIGRATION-PLAN.md`](../MIGRATION-PLAN.md) · Deprecated index: [`../architecture/deprecated/README.md`](../architecture/deprecated/README.md)

---

## 1. Summary

| Metric | Count / state |
|--------|----------------|
| Total `docs/` markdown files (pre–Phase 1.2) | 29 content + tier READMEs added |
| **Canonical** runtime architecture doc | 1 ([`canonical-runtime-architecture.md`](../architecture/canonical-runtime-architecture.md)) |
| **Canonical** navigation / index docs | 4 (`docs/README.md`, `architecture/README.md`, `ops/README.md`, `project-status/README.md`) |
| **Runtime-derived** architecture + ops docs | 14 |
| **Deprecated** / obsolete | 3 marked |
| **Archived** / historical slice plans | 5 |
| **Draft** | 1 |
| **Experimental** | 1 (n8n export, not in docs/) |
| Physical file moves in Phase 1.2 | **0** (structure + markers only) |
| Tier placeholder directories created | 15 |

**Stabilization result:** **Pass with known unstable clusters** — entrypoints exist; large doc sets remain at legacy paths until Phase 1.3+.

---

## 2. Current canonical documents

| Document | Path | Role |
|----------|------|------|
| **Canonical runtime architecture** | `architecture/canonical-runtime-architecture.md` | **Primary** runtime truth map |
| Documentation index | `docs/README.md` | Top-level navigation + truth hierarchy |
| Architecture index | `architecture/README.md` | Architecture tier guide |
| Ops index | `ops/README.md` | Runbook index |
| Project status index | `project-status/README.md` | Status tier guide |
| Migration plan | `MIGRATION-PLAN.md` | Tier migration phases |
| Deprecated index | `architecture/deprecated/README.md` | Archive candidates |
| Open work queue | `project-status/next-steps.md` | Single queue |
| Shipped changelog | `project-status/completed.md` | Accepted work |
| Architecture decisions | `project-status/decisions.md` | ADR log |
| Ops credentials checklist | `ops/n8n-env-credential-checklist.md` | Env/credential names |
| This report | `project-status/documentation-topology-status.md` | Topology inventory |

**Contracts (outside `docs/`):** `specs/` — canonical for **intended** API/DB/architecture contracts; runtime behavior drift documented in canonical map §12.

---

## 3. Runtime-derived documents (supporting)

Verified against code; must stay aligned with canonical map.

### Architecture

| Document | Implementation alignment | Risk if stale |
|----------|-------------------------|---------------|
| `greeting-orchestration-mvp.md` | **implemented** | Low |
| `conversation-intent-policy-mvp.md` | **partial** (CIP-C/D open) | Medium |
| `operator-business-context-n8n.md` | **implemented** | Low |
| `pre-sales-contact-ownership.md` | backend **done**, n8n **partial** | Medium |
| `langfuse-tracing.md` | **partial** (intent metadata gap) | Medium |
| `telegram-channel-credentials.md` | **implemented** | Low |

### Project status

| Document | Role |
|----------|------|
| `current-state.md` | Regeneratable snapshot — must track canonical map |

### Ops

| Document | Role |
|----------|------|
| `n8n-workflow1-test-webhook.md` | T13 test path |
| `n8n-workflow-telegram-customer-ingress.md` | T14 Telegram path |
| `telegram-customer-ingress.md` | Mapping (duplicate cluster) |
| `n8n-runtime-start.md` | Runtime |
| `n8n-https-reverse-proxy.md` | Edge |
| `database-recovery.md` | Recovery |

---

## 4. Unstable areas

| Area | Issue | Severity |
|------|-------|----------|
| **Flat `docs/architecture/`** | Runtime-derived + canonical map + deprecated content mixed at one level | Important |
| **Flat `docs/project-status/`** | Living + historical + deprecated without physical separation | Important |
| **Telegram ops duplicate cluster** | `telegram-customer-ingress.md` vs `n8n-workflow-telegram-customer-ingress.md` | Minor |
| **Langfuse doc vs code** | Tag mapping `demo_barbershop_001` → `alpstein_ai_demo_001` | Important |
| **Intent spec vs specs/** | CIP in `docs/architecture/`; prompt-builder-rules may lack intent amendment | Minor |
| **n8n repo vs runtime** | Exports `active: false`; T14.6 export gate open | Important |
| **No `docs/ops/README` before Phase 1.2** | Ops entrypoint missing | **Resolved** |

---

## 5. Duplicate clusters

| Cluster | Members | Recommendation |
|---------|---------|----------------|
| Telegram ingress | `ops/telegram-customer-ingress.md`, `ops/n8n-workflow-telegram-customer-ingress.md` | Keep workflow doc canonical; mapping as appendix or merge Phase 1.5 |
| Pre-sales behavior | `technical-pre-sales-behavior-mvp.md`, `conversation-intent-policy-mvp.md`, `PRE_SALES_CORE_CHARTER` + intent slices | Deprecate technical-pre-sales doc; map §5 documents Alpstein vs non-Alpstein §2 paths |
| Project snapshot | `current-state.md`, `engineering-archive.md`, `canonical-runtime-architecture.md` | **Map** = architecture; **current-state** = snapshot; **archive** = history |
| T13 task breakdown | `tasks/done/t13-n8n-workflow-slice.md`, `project-status/t13-n8n-workflow-plan.md` | Plan → historical/; done task stays in `tasks/done/` |
| Test webhook docs | `n8n-workflow1-test-webhook.md`, `t13-n8n-workflow-plan.md` | Cross-link only; archive plan |

---

## 6. Deprecated areas

| Document | Marker | Action |
|----------|--------|--------|
| `project-status/backlog.md` | deprecated | Move Phase 1.3 → `historical/` |
| `project-status/t11-prompt-builder-design.md` | deprecated | Move Phase 1.3 → `architecture/deprecated/` |
| `architecture/technical-pre-sales-behavior-mvp.md` | deprecated | Move Phase 1.4 → `architecture/deprecated/` |
| `ops/n8n-deployment-plan.md` | deprecated | Move Phase 1.5 → `ops/archived/` |

Full list: [`architecture/deprecated/README.md`](../architecture/deprecated/README.md)

---

## 7. Archived / historical (not deprecated — retain for audit)

| Document | Reason |
|----------|--------|
| `engineering-archive.md` | Long-form engineering history |
| `engineering-audit-report.md` | 2026-05 drift audit |
| `t11-ai-orchestration-plan.md` | Completed slice |
| `t12-lead-notification-plan.md` | Completed slice |
| `t13-n8n-workflow-plan.md` | Completed slice; deferred items noted |
| `ops/post-t13-5-stabilization.md` | One-time gate |

---

## 8. Draft / experimental

| Item | Status |
|------|--------|
| `project-status/channel-source-attribution-design.md` | **draft** — ATTR-2 implemented; ATTR-3+ not |
| `n8n/workflows/My_workflow.json` | **experimental** — non-canonical export |

---

## 9. Docs still violating runtime truth (known)

| Document | Violation | Fix owner |
|----------|-----------|-----------|
| `canonical-runtime-architecture.md` | §5.7 / §12 say HF-1 plan-only; code has HF-1 | Archivist: patch map §5.7 + §12 |
| `langfuse-tracing.md` | Demo tag may mismatch `langfuse_tracing_service.py` | Backend on CIP-C |
| `technical-pre-sales-behavior-mvp.md` | Describes always-on appendix as current for all businesses | Mark deprecated **done** |
| `t11-ai-orchestration-plan.md` | Says "Next: T12" | Mark archived **done** |
| `ops/n8n-deployment-plan.md` | "runtime not started" | Mark deprecated; point to `n8n-runtime-start.md` |

**Resolved in prior archivist sweep:** `next-steps.md` CIP "not implemented"; `current-state.md` n8n missing; stale test count.

---

## 10. Migration recommendations (ordered)

1. **Phase 1.3** — Move 5 low-risk historical/deprecated files ([`MIGRATION-PLAN.md`](../MIGRATION-PLAN.md)); leave stub redirects.
2. **Phase 1.4** — Conversational cluster under `docs/conversational/`.
3. **Phase 1.5** — Ops production/archived split; resolve Telegram duplicate cluster.
4. **Link sweep** — `rg` for moved paths across `docs/`, `tasks/`, `.cursor/skills/`.
5. **CIP-C** — Update runtime-derived docs when wired; refresh canonical map §11–§12.

**Not recommended yet:** Bulk move of `specs/`; delete deprecated files; merge `engineering-archive` into map.

---

## 11. Unresolved conflicts

| Conflict | Runtime truth | Doc/spec claim | Resolution path |
|----------|---------------|----------------|-----------------|
| HF-1 History Safety | **Implemented** in PromptBuilder §7 | Canonical map §5.7 still says plan-only | **Important** — patch canonical map |
| CIP-C Langfuse metadata | Constants only | Spec § CIP-C | Implement; update `langfuse-tracing.md` |
| ATTR persistence | Schema only | Design doc | ATTR-3 task |
| Intent policy scope | `alpstein_ai_demo_001` only | Spec may imply broader MVP | Open decision §16 canonical map |
| Legacy appendix | Active for other businesses | CIP "replacement" narrative | Open decision; map documents both paths |

---

## 12. Tier directory scaffold (Phase 1.2)

Created placeholder READMEs — **no content moves**:

```text
docs/architecture/{canonical,runtime,deprecated,experiments}/
docs/conversational/{prompts,orchestration,policies}/
docs/ops/{production,migration,archived}/
docs/project-status/{current,historical}/
```

---

## 13. Remaining risks

| Risk | Severity |
|------|----------|
| New contributors use flat paths and miss `docs/README.md` | Important — link from `AGENTS.md` / `current-state.md` |
| Historical plans linked from old tasks | Minor — Phase 1.3 link sweep |
| Duplicate Telegram docs diverge | Minor — consolidate Phase 1.5 |
| Canonical map not updated after HF-1/CIP-C | Critical when those ship |

---

## 14. Recommended next stabilization step

**Phase 1.3 low-risk moves:** relocate `backlog.md`, `t11-prompt-builder-design.md`, and completed slice plans to `historical/` / `deprecated/` with one-line stub files at old paths; run link sweep.

Command:

```
/alpstein-project-archivist Execute MIGRATION-PLAN.md Phase 1.3 only
```
