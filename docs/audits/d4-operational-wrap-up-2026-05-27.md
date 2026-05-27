# Phase D4 — Operational wrap-up (D4.5)

**Date:** 2026-05-27  
**Branch:** `stabilization/runtime-baseline`  
**Phase:** D4.5 — Operational wrap-up (documentation only)  
**Prior slices:** D4.1, D4.2, D4.3, D4.4; U1 metadata JSON-safe fix; OPS-C1 stale ingress mitigation

**Related audits:**

| ID | Report |
|----|--------|
| D4.1 | [`d4-1-live-trace-validation-2026-05-27.md`](d4-1-live-trace-validation-2026-05-27.md) |
| D4.2 | [`d4-2-compose-e2e-hardening-2026-05-28.md`](d4-2-compose-e2e-hardening-2026-05-28.md) |
| D4.3 | [`d4-3-db-replay-verification-2026-05-27.md`](d4-3-db-replay-verification-2026-05-27.md) |
| D4.4 | [`d4-4-production-safety-audit-2026-05-27.md`](d4-4-production-safety-audit-2026-05-27.md) |

**Contracts:** [`specs/architecture/observability-metadata.md`](../../specs/architecture/observability-metadata.md) §3.4, §16 · [`docs/deployment/deployment-contract.md`](../deployment/deployment-contract.md)

---

## Executive summary

Phase **D4** verified that the **portable Docker Compose stack** (`postgres` → `backend` with migrate-then-serve → `n8n`) is the **operational source of truth** for backend behavior, observability lineage, and replay. Evidence is **compose-scoped** on a Contabo-class host — not a separate production cluster audit and **not** enterprise-scale validation.

| Question | Answer |
|----------|--------|
| Is D4 operationally complete? | **Yes** for the defined verification scope (trace, compose E2E, DB replay, production-safety code review, ingress mitigation). |
| Final verdict | **STABLE WITH KNOWN OPERATIONAL LIMITS** |
| Ready for Phase E? | **Yes, with discipline** — controlled expansion only; see § Phase E readiness |

Do **not** interpret this as “production-hardened SaaS” or “validated at scale.”

---

## 1. What was verified (evidence-backed)

| Capability | Evidence | Trust level |
|------------|----------|-------------|
| **Compose as runtime SoT** | D4.2 clean-volume drill; D4.3 webhooks via `alpstein_backend` | **Verified** on portable stack |
| **Migrate-before-serve** | D4.2 logs: `alembic upgrade head` before uvicorn; `alembic_version` = `0007` | **Verified** |
| **Deterministic backend startup** | D4.2 health gates, restart drills | **Verified** (compose) |
| **Readiness endpoint** | `GET /api/v1/health/ready` + `SELECT 1` (B2.4) | **Verified** in compose drills |
| **Correlation reconstruction** | D4.1/D4.3: `correlation_id` in metadata + webhook path | **Verified** on compose |
| **Replay lineage** | D4.3 SQL from `correlation_id` → message → `prompt_runs` | **Verified** |
| **Duplicate / retry semantics** | D4.3: no extra PromptRun on duplicate; new PromptRun on retry | **Verified** |
| **`prompt_runs.metadata` JSON-safe** | U1 `json_safe_metadata()`; D4.2 E2E unblocked; D4.3 DB sample | **Verified** |
| **Metadata envelope production-safe** | D4.4 code + tests + D4.3 sample (no forbidden keys) | **Verified** by design + sample |
| **Tracing governance (§16)** | D4.4: flat metadata omits sensitive text in prod/staging | **Verified** in code/tests |
| **Production tracing defaults** | `langfuse_tracing_active()` + env gating; prod off unless explicit enable | **Verified** in code |
| **Single active compose ingress** | OPS-C1 mitigation (operator); D4.3+ used compose only | **Accepted** post-mitigation; legacy `:8010` documented as hazard if revived |
| **n8n export governance** | C1/C2 done (parity policy + scrub gate) | **Implemented**; runtime parity diff (C3) **not** verified |

---

## 2. What is operationally trusted (post-D4)

Operators may rely on the following **when using the portable compose project** (`docker-compose -p alpstein-ai`, internal `http://backend:8000`):

1. **Schema version** follows Alembic chain `0001`–`0007` after backend start.
2. **Webhook AI path** persists `prompt_runs` with scalar, JSON-safe `metadata` suitable for incident replay.
3. **Correlation IDs** are stable enough to join webhook → DB without pulling `final_prompt` by default.
4. **Observability metadata** does not store full prompts, operator context blobs, or raw secrets in `metadata` (redaction + caps).
5. **Langfuse flat metadata** respects §16.2 in production/staging when tracing is on.
6. **Legacy dual-ingress confusion** is mitigated by policy: **do not** route live validation through stale host `:8010` without a restarted binary at current baseline.

**Assumed (not re-proven in D4.5):** HTTPS edge, Telegram provider delivery, OpenAI availability, and live n8n workflow activation match ops runbooks.

---

## 3. Partially verified / not live-proven

| Item | Status | Notes |
|------|--------|-------|
| Failure-path webhook → `prompt_runs.error` | **Partial** | Unit tests only; no `error IS NOT NULL` rows in D4.3 DB |
| CIP intent fields in metadata | **Partial** | D4.3 used `demo_barbershop_001`; intent keys expected on `alpstein_ai_demo_001` |
| Langfuse UI end-to-end | **Partial** | D4.1 blocked on stale host; compose path trusted via code + D4.3 |
| n8n `X-Correlation-Id` / `X-N8n-Execution-Id` headers | **Deferred** | D3 scope; not closure criteria for D4 |
| Full portable n8n E2E in D4.2 | **Partial** | Postgres + backend hardened; n8n service ordering noted, not full matrix |
| Production/staging environment | **Not audited** | Code review + development compose only |
| Legacy Contabo host layout | **Documented, not retired** | Compatibility appendix; not portable SoT |

---

## 4. Operational architecture state (as-of D4 close)

```text
┌─────────────────────────────────────────────────────────────┐
│  Portable compose (SoT for D4 verification)                  │
│  alpstein_postgres → alpstein_backend (entrypoint+migrate)   │
│       → alpstein_n8n_compose  (BACKEND_BASE_URL=backend:8000)│
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Legacy Contabo (compatibility — do not mix with portable)   │
│  host uvicorn :8010, legacy alpstein_n8n @ 15679,            │
│  BACKEND_BASE_URL=http://172.20.0.1:8010                     │
└─────────────────────────────────────────────────────────────┘
```

| Layer | SoT for new ops work | Legacy |
|-------|----------------------|--------|
| Backend code + migrations | Git + compose image build | Host uvicorn if explicitly maintained |
| Runtime ingress for verification | Compose `backend:8000` | `:8010` — **stale-process risk** |
| DB for portable stack | `alpstein_ai` on `alpstein_postgres` | `backend_postgres` / shared DB |
| Workflow exports | `n8n/workflows/*.json` + scrub gate | Live UI edits require export reconcile |

---

## 5. Remaining operational risks (classified)

### P0 — must not regress before controlled expansion

| Risk | Description | Mitigation |
|------|-------------|------------|
| **Wrong ingress / stale process** | Host `:8010` process from pre-baseline tree serves old behavior (D4.1) | OPS-C1: single ingress policy; compose or restarted host at current SHA; [`operational-ingress-policy.md`](../ops/operational-ingress-policy.md) |
| **Mixing portable + legacy on one n8n instance** | `BACKEND_BASE_URL` points at wrong backend | One URL profile per n8n deployment; checklist in export parity doc |

### P1 — accept or harden before broad production tracing / DB access

| Risk | Description | Mitigation |
|------|-------------|------------|
| **Langfuse generation I/O** | Full OpenAI messages in generation input/output when tracing enabled | Keep `LANGFUSE_TRACING_ENABLED` false in production unless leadership accepts exposure |
| **`prompt_runs.final_prompt`** | Full assembled prompt in DB column (redacted, 16k) | DB RBAC; metadata-first replay runbooks |
| **`messages.raw_payload`** | May hold provider secrets if normalization fails | n8n normalization discipline; no raw dumps in logs |
| **Failure path not live-drilled** | Error column redaction not proven under real 5xx | Optional disposable failure drill (D4.3-R2) |
| **`staging` + tracing enabled** | Metadata text suppressed but generation I/O still full | Config review |

### P2 — process / quality gaps

| Risk | Description | Mitigation |
|------|-------------|------------|
| **Optional failure drills** | No periodic replay exercises | Schedule disposable-compose drill |
| **Ingress/domain normalization** | Future multi-host TLS and API routing | Phase E planning; not D4 scope |
| **n8n runtime vs export parity (C3–C5)** | Canonical export may drift from live UI | C3 diff tool; T14.5 regression |
| **CI metadata key scan on live DB** | Process gap (D4.4 O4) | Future automation |

### P3 — future hardening (does not block Phase E planning)

| Risk | Notes |
|------|-------|
| Proxy/access log review | Environment-dependent |
| Redact Langfuse generation `input` in production | Out of D4; requires explicit task |
| RBAC / break-glass access model | Not implemented |
| T10-F3 idempotency race | Known MVP gap |

---

## 6. Intentionally deferred (not D4 blockers)

| Item | Owner phase |
|------|-------------|
| Kubernetes / horizontal scale | Out of MVP contract |
| CRM expansion | Out of scope |
| Observability redesign | Frozen post-D4 |
| ATTR-3 attribution persistence | Backend feature slice |
| WhatsApp / new channels | Phase E (controlled) |
| n8n correlation headers (D3) | Optional hardening |
| C3/C4 export parity automation | Phase C continuation |
| Legacy host decommission | Operator timeline; not required for Phase E **planning** |

---

## 7. D4 completion state

| Criterion | Status |
|-----------|--------|
| D4.1 Live trace validation | **Complete** (findings drove OPS-C1; compose path supersedes blocked host run) |
| D4.2 Compose E2E hardening | **Complete** (U1 fix applied) |
| D4.3 DB replay verification | **Complete** (failure path skipped by policy) |
| D4.4 Production safety audit | **Complete** — PASS WITH NOTES |
| OPS-C1 Stale ingress mitigation | **Complete** (operator acceptance) |
| D4.5 Documentation wrap-up | **This document** |

**Does not block Phase E:** ATTR-3, C3/C4 automation, failure drill, Langfuse generation I/O policy change, legacy host retirement.

**Should be addressed early in Phase E:** T14.5 Telegram regression on portable path; optional D4.3-R2 failure drill; confirm no stale `:8010` in active ops.

---

## 8. Phase E readiness

**Phase E (defined here):** **Controlled expansion** — add operational surface (channels, businesses, environments) **without** architecture redesign, observability contract changes, or infra migration.

### Operational readiness assessment

| Dimension | Assessment |
|-----------|------------|
| Reproducible runtime | **Adequate** for controlled expansion on compose |
| Incident replay | **Adequate** (metadata-first; `final_prompt` break-glass only) |
| Deployment rollback | **Adequate** (RBU/RDU documented B2 + D4.2) |
| Channel ops maturity | **Partial** — Telegram path live; T14.5 gate open |
| Security / access control | **Limited** — no enterprise RBAC |
| Scale validation | **None claimed** |

### Recommended first controlled expansion (discipline)

1. **T14.5 / C5** — Telegram owner-notify + duplicate regression on **canonical export**, against **compose** backend (`http://backend:8000`), with export scrub (G-EXP-2) in the commit path.
2. **CIP-D** — Live smoke on `alpstein_ai_demo_001` for intent metadata in `prompt_runs.metadata` (closes D4.3-R3 gap).
3. **Only then** — plan second channel (e.g. WhatsApp) as a **new ingress workflow + normalization contract** task slice; no parallel architecture work.

### Engineering discipline going forward

- **One ingress profile** per environment; document in ops runbooks before any live test.
- **RDU/RBU:** compose file hash + image tag + workflow `versionId` when changing ops surface.
- **Metadata-first debugging**; treat `final_prompt` and Langfuse generation I/O as sensitive.
- **No silent n8n UI edits** on production-shaped instances (Phase C policy).
- **Specs win** — expansion tasks must cite `specs/api/webhooks.md` and observability-metadata §16.

### Boundaries (Phase E must not)

- Redesign observability or PromptBuilder contracts.
- Introduce Kubernetes, CRM sync, or frontend.
- Enable production Langfuse without explicit acceptance of generation I/O exposure.
- Mix legacy `:8010` and compose backends on one n8n instance.

---

## 9. Readiness verdict

| Verdict | **STABLE WITH KNOWN OPERATIONAL LIMITS** |
|---------|------------------------------------------|
| Meaning | Portable compose baseline is **trusted for controlled expansion** under documented P0/P1 risks. |
| Not claimed | Enterprise maturity, multi-region HA, load testing, full production Langfuse safety, automated parity CI. |
| Alternative if P0 regresses | Would downgrade to **NOT READY** — e.g. stale `:8010` again serving traffic without label. |

---

## 10. Technical debt closed (E0)

| ID | Resolution |
|----|------------|
| **TD-D4-n8n-script-layout** | **Closed** — ownership documented in [`repository-layout-n8n-scripts.md`](../ops/repository-layout-n8n-scripts.md). No file moves: `scripts/n8n/` = workflow JSON gates; `n8n/scripts/` = live n8n container ops; `scripts/verify/` = cross-cutting harnesses. |

---

## 11. Document maintenance

| Action | Owner |
|--------|-------|
| Append D4 bullets to `completed.md` | Archivist (this sweep) |
| Patch `current-state.md` / `next-steps.md` | Archivist (this sweep) |
| E0 n8n script layout note | Archivist (E0) |
| Human review before git commit | Operator |

**Report status:** Draft for review — **not committed** per project rules.
