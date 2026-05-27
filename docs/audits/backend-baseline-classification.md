# A4.2 — Canonical Backend Baseline Classification

**Status:** classification (pre-import, no staging/commit)  
**Date:** 2026-05-27  
**Phase:** A4.2 — Canonical Backend Baseline Definition  
**Inputs:** `runtime-reproducibility-audit.md`, `runtime-baseline-remediation-plan.md`, `phase-a4.1-git-truth-normalization.md`

## Goal

Define the canonical backend reproducibility baseline before any backend baseline import commit, without changing runtime behavior.

## Scope reviewed

- `backend/alembic/**` (9 files)
- `backend/app/**` (79 files)
- `backend/tests/**` (45 files)
- `backend/scripts/**` (3 files)
- `backend/requirements.txt`
- `backend/alembic.ini`

---

## 1) Canonical reproducibility-critical backend artifacts

These artifacts are required to reproduce current backend runtime behavior from git.

### Include (canonical)

- `backend/app/main.py`
- `backend/app/api/**`
- `backend/app/core/**`
- `backend/app/db/**`
- `backend/app/models/**`
- `backend/app/schemas/**`
- `backend/app/services/**`
- `backend/app/exceptions.py`
- `backend/app/__init__.py`
- `backend/alembic.ini`
- `backend/alembic/env.py`
- `backend/alembic/script.py.mako`
- `backend/alembic/versions/*.py` (0001..0007 chain)
- `backend/requirements.txt`

### Rationale

- These files form the executable webhook -> orchestration -> persistence path documented as runtime truth.
- Alembic chain and config are mandatory for schema replay and rollback integrity.
- `requirements.txt` is the dependency baseline required for deterministic test/runtime setup.

### Exclude (from this class)

- `backend/.venv/**`, `backend/.pytest_cache/**` and any cache-generated artifacts.

---

## 2) Generated/runtime-only artifacts

Artifacts generated locally during execution/testing and not suitable as canonical source.

### Exclude

- `backend/.venv/**`
- `backend/.pytest_cache/**`
- any `__pycache__/` or `*.pyc` under backend if present later

### Reproducibility rationale

- These are environment-specific and non-deterministic outputs.
- Tracking them increases merge noise and can mask real source-of-truth drift.

---

## 3) Local-only artifacts

Artifacts intended for local operator workflows, not baseline runtime source.

### Classify as local-only (manual handling, not baseline import by default)

- `backend/scripts/demo_business_separation.sql`
- `backend/scripts/update_alpstein_pre_sales_behavior.sql`

### Rationale

- Both are manual SQL data mutation scripts against development/runtime data state.
- They are not part of the migration chain and can change content without schema revision semantics.

### Notes

- Keep available for ops reference if needed, but do not mix with core baseline import commit unless explicitly approved as canonical operational tooling.

---

## 4) Experimental/deprecated artifacts

### Current finding

- No obviously experimental Python modules under `backend/app/**` were identified by naming.
- Potentially transitional/manual artifacts are concentrated in `backend/scripts/*.sql`.

### Classification decision

- Treat `backend/scripts/*.sql` as **manual/operational legacy helpers**, not canonical baseline runtime source.
- Revisit only in a dedicated docs/ops governance slice, not in backend baseline import.

---

## 5) Unsafe / no-go artifacts

Do not track these in backend baseline import.

- Any secret-bearing `.env` material (outside backend scope but relevant for reproducibility hygiene).
- Runtime/test caches (`.venv`, `.pytest_cache`, compiled bytecode).
- Any ad-hoc local files created during validation that are not part of source, migration chain, or test suite.

### Safety rationale

- Prevents secret leakage and non-reproducible machine-local state from entering git.

---

## 6) Migration-critical artifacts

### Include (must be in canonical baseline import)

- `backend/alembic.ini`
- `backend/alembic/env.py`
- `backend/alembic/script.py.mako`
- `backend/alembic/versions/0001_create_tenants_and_businesses.py`
- `backend/alembic/versions/0002_create_customers.py`
- `backend/alembic/versions/0003_create_conversations.py`
- `backend/alembic/versions/0004_create_messages.py`
- `backend/alembic/versions/0005_add_messages_business_external_message_id_unique.py`
- `backend/alembic/versions/0006_create_ai_configuration_and_prompt_runs.py`
- `backend/alembic/versions/0007_create_leads.py`

### Migration safety concerns

- Missing any single revision breaks replay continuity and invalidates rollback confidence.
- `alembic.ini` + `env.py` are required to resolve DB URL/runtime metadata wiring.
- Manual SQL scripts must **not** substitute for migration-chain state.

### Rollback concerns

- Rollback unit cannot be validated if chain/config are partially tracked.
- Downgrade posture must reference the tracked Alembic revisions only; manual data scripts are non-atomic to schema rollback.

---

## 7) Test reproducibility artifacts

### Include (reproducibility-critical test baseline)

- `backend/tests/conftest.py`
- all `backend/tests/test_*.py` currently present (45 files)

### Test reproducibility rationale

- This suite encodes behavioral and schema guardrails for webhook, AI orchestration, gating, prompt assembly, and migration integrity.
- Migration and model tests provide reproducibility evidence for schema/runtime contracts.

### Test reproducibility concerns

- Excluding migration tests (`test_alembic_migration.py`, model tests) weakens rollback/replay confidence.
- Selectively importing tests can create false green confidence by omitting integration regressions.

---

## Explicit inclusion/exclusion decisions (summary)

## Include in backend canonical baseline

- `backend/app/**` (source code)
- `backend/alembic/**` + `backend/alembic.ini`
- `backend/requirements.txt`
- `backend/tests/**`

## Exclude from backend canonical baseline

- `backend/.venv/**`
- `backend/.pytest_cache/**`
- generated caches/compiled artifacts

## Defer/manual-review class (do not mix into baseline import)

- `backend/scripts/demo_business_separation.sql`
- `backend/scripts/update_alpstein_pre_sales_behavior.sql`
- `backend/scripts/seed_dev_ai_configuration.py` (review as operational helper; not runtime-critical execution path)

---

## Proposed safe commit boundaries for backend baseline import

No staging/commit in this phase. Proposed boundaries for next phase:

1. **A4.2-B1 — Core backend source import**
   - `backend/app/**` only
   - Purpose: runtime code baseline without migration/test noise

2. **A4.2-B2 — Migration baseline import**
   - `backend/alembic/**` + `backend/alembic.ini`
   - Purpose: schema replay/rollback integrity as isolated review unit

3. **A4.2-B3 — Dependency baseline**
   - `backend/requirements.txt`
   - Purpose: deterministic environment dependency anchor

4. **A4.2-B4 — Test reproducibility baseline**
   - `backend/tests/**`
   - Purpose: reproducibility and regression evidence

5. **A4.2-B5 — Optional operational scripts review (separate, only if approved)**
   - `backend/scripts/**`
   - Purpose: classify/manual tooling governance without polluting runtime baseline commits

### Boundary rules

- Do not create a giant backend sweep commit.
- Do not mix migration import with scripts/manual SQL.
- Do not mix backend baseline import with n8n/specs/docs reconciliation in the same commit.
- Keep each boundary independently reversible for rollback-safe normalization.

---

## Final decision

Canonical backend reproducibility baseline is defined as:

- `backend/app/**`
- `backend/alembic/**`
- `backend/alembic.ini`
- `backend/requirements.txt`
- `backend/tests/**`

All other backend artifacts are excluded or deferred by class as documented above.

---

## A4.2-B1 preparation — `backend/app` rollback-safe slicing

Goal: split `backend/app/**` into minimal-risk import commits that preserve runtime behavior and maximize rollback clarity.

### Required classification map

1. **App bootstrap/runtime entrypoints**
   - `backend/app/main.py`
   - `backend/app/__init__.py`
   - `backend/app/core/__init__.py`
   - `backend/app/core/config.py`

2. **API layer**
   - `backend/app/api/__init__.py`
   - `backend/app/api/webhook_auth.py`
   - `backend/app/api/routes/__init__.py`
   - `backend/app/api/routes/health.py`
   - `backend/app/api/routes/webhook.py`

3. **DB layer**
   - `backend/app/db/__init__.py`
   - `backend/app/db/base.py`
   - `backend/app/db/session.py`

4. **Schemas/models**
   - `backend/app/schemas/**`
   - `backend/app/models/**`
   - `backend/app/exceptions.py`

5. **Orchestration services**
   - `backend/app/services/webhook_message_service.py`
   - `backend/app/services/ai_reply_orchestration_coordinator.py`
   - `backend/app/services/ai_reply_orchestration_service.py`

6. **Tenant/business services**
   - `backend/app/services/business_service.py`
   - `backend/app/services/customer_service.py`
   - `backend/app/services/conversation_service.py`
   - `backend/app/services/message_service.py`
   - `backend/app/services/lead_service.py`
   - `backend/app/services/tenant_*_service.py`
   - `backend/app/services/tenant_context_validator.py`
   - `backend/app/services/prompt_template_service.py`

7. **AI gateway/services**
   - `backend/app/services/ai_gateway/**`
   - `backend/app/services/ai_gateway_service.py`
   - `backend/app/services/ai_configuration_service.py`
   - `backend/app/services/knowledge_retrieval_service.py`
   - `backend/app/services/ai_reply_fallback_service.py`
   - `backend/app/services/prompt_run_service.py`

8. **Tracing/observability services**
   - `backend/app/services/langfuse_tracing_service.py`
   - `backend/app/schemas/langfuse_intent_trace.py`

9. **Prompt/policy services**
   - `backend/app/services/prompt_builder_service.py`
   - `backend/app/services/pre_sales_prompt_instructions.py`
   - `backend/app/services/intent_prompt_instructions.py`
   - `backend/app/services/greeting_prompt_instructions.py`
   - `backend/app/services/history_safety_prompt_instructions.py`
   - `backend/app/services/conversation_intent_service.py`
   - `backend/app/services/conversation_intent_policy.py`
   - `backend/app/services/greeting_policy_service.py`
   - `backend/app/services/customer_language_detection.py`

10. **Non-runtime/deferred artifacts**
   - `backend/app/seed/**` (development data seed support; not request runtime path)

### Recommended `backend/app` import order (minimal-risk sequence)

1. **B1.1 — Foundational types + persistence primitives**
   - `db/**`, `models/**`, `schemas/**`, `exceptions.py`
   - Why first: most other slices import these modules; low behavioral ambiguity as a dependency foundation.

2. **B1.2 — Tenant/business domain services**
   - tenant/business/customer/conversation/message/lead services + validators
   - Why second: establishes domain logic used by orchestration and API; rollback remains isolated from transport.

3. **B1.3 — AI core services**
   - AI config, knowledge retrieval, gateway, fallback, prompt-run service
   - Why third: keeps provider-facing orchestration dependencies together with clear boundaries.

4. **B1.4 — Prompt/policy services**
   - prompt builder, greeting/intent/history policies and instruction blocks
   - Why fourth: policy layer is tightly coupled to orchestration text assembly and easier to review as one concern.

5. **B1.5 — Orchestration services**
   - AI orchestration + webhook message coordinator/service
   - Why fifth: depends on all prior layers; isolate integration-heavy glue for focused review.

6. **B1.6 — API + bootstrap entrypoints**
   - `api/**`, `main.py`, core bootstrap/config modules
   - Why last: entrypoint layer wiring is safest to import once internal dependencies are already in git baseline.

7. **B1.7 — Deferred non-runtime seed artifacts (optional separate commit)**
   - `seed/**`
   - Why separate: dev seeding is useful but not required to preserve runtime execution path.

### Safe commit boundaries (within A4.2-B1 scope)

- One commit per step B1.1..B1.6, optionally B1.7.
- Keep each step independently reversible.
- No cross-layer bundling that obscures dependency ownership.

### Smallest safe first `backend/app` slice

**B1.1 (foundation)** is the smallest safe first import:
- `backend/app/db/**`
- `backend/app/models/**`
- `backend/app/schemas/**`
- `backend/app/exceptions.py`

This slice minimizes transport/runtime wiring risk while anchoring type and persistence imports required by all upper layers.

### Rollback concerns

- If API/bootstrap are imported before foundation/services, rollback can leave broken import graphs in intermediate history.
- Orchestration commits without prompt/policy or AI core services increase partial-state risk and reduce bisect clarity.
- Seed artifacts mixed with runtime slices can create false rollback expectations (data mutation vs code baseline).

### Coupling risks

- `webhook_message_service.py` is high-coupling across domain + AI + policy + API contracts.
- `prompt_builder_service.py` couples schemas, policy blocks, and orchestration expectations.
- `langfuse_tracing_service.py` couples to orchestration metadata contracts but should not block core runtime import.

### No-go combinations

- **No-go 1:** API routes + `main.py` without underlying services/schemas/models.
- **No-go 2:** Orchestration services without AI core + domain services imported.
- **No-go 3:** Prompt/policy services split across multiple mixed commits with orchestration in between.
- **No-go 4:** Seed artifacts in same commit as runtime-critical service/bootstrap slices.
- **No-go 5:** Observability/tracing mixed into foundational DB/model first slice.

---

## Reviewer section (alpstein-reviewer)

### Review summary

**Pass with notes (GO with boundary controls).**  
The proposed A4.2 baseline classes are directionally safe and reproducibility-focused, but commit boundaries need one tightening to avoid hidden architecture/noise import risk.

### GO / NO-GO for backend baseline import

- **GO** for backend baseline import **if** commit boundaries stay split and reviewable as proposed (B1..B4) and exclusion rules are enforced.
- **NO-GO** if `backend/scripts/**` is mixed into the baseline import or if `backend/app/**` is imported as one giant unreviewed sweep without boundary guardrails.

### Files/directories safe to stage

Safe for baseline (in isolated commits):

1. `backend/app/**`  
2. `backend/alembic/**`  
3. `backend/alembic.ini`  
4. `backend/requirements.txt`  
5. `backend/tests/**`

### Files/directories that must not be staged

Do not stage in backend baseline import:

- `backend/.venv/**`
- `backend/.pytest_cache/**`
- any `backend/**/__pycache__/**`
- any `backend/**/*.pyc`
- `backend/scripts/**` (defer to separate ops/manual-tooling governance slice)

Additionally (safety reminder): no `.env` secrets anywhere; no non-backend scope mixing (n8n/specs/docs reconciliation) in backend baseline commits.

### Risks before commit

1. **`backend/app/**` breadth risk**  
   Importing all app modules in one commit may hide architecture shifts or unrelated churn. This is not a reason to block baseline import, but it is a review risk that must be controlled by commit slicing and reviewer focus.

2. **Scripts classification mismatch / ambiguity**  
   Scope line says `backend/scripts/** (3 files)`, while the explicit local-only list in section 3 names only two SQL files; section 8 references `backend/scripts/seed_dev_ai_configuration.py` but earlier inventory lists `app/seed/dev_ai_configuration.py`.  
   **Risk:** staging mistakes during baseline sweep.

3. **Migration rollback confidence depends on independent review**  
   Alembic chain is correctly required, but downgrade/replay assumptions should be validated in a migration-only commit before broader import confidence is claimed.

4. **Test import noise risk**  
   Full `backend/tests/**` is reproducibility-correct, but test-only helpers/data could conceal local assumptions if not reviewed as an independent unit.

5. **Hidden runtime-only artifacts risk in large adds**  
   Cache/runtime artifacts are correctly excluded by policy, but broad `git add backend/` usage can still accidentally pick up unwanted files if ignore policy drifts.

### Recommended first backend baseline commit boundary

Use this as the **first** backend baseline commit:

- **A4.2-B2 — Migration baseline import only**
  - `backend/alembic/**`
  - `backend/alembic.ini`

Rationale:
- smallest high-impact reproducibility slice,
- independently reviewable for replay/rollback integrity,
- lowest chance of hidden architecture changes,
- creates a hard DB baseline before app/test breadth is imported.

Follow with:
- B3 (`backend/requirements.txt`),
- B1 (`backend/app/**`, optionally split by layer),
- B4 (`backend/tests/**`).

---

## Reviewer note (alpstein-reviewer) — A4.2-B1 slicing review

### GO / NO-GO for first `backend/app` slice

- **GO (guarded)** for first app slice if it is restricted to the foundation set only and excludes all service/bootstrap/API wiring.
- **NO-GO** if first app slice includes any `services/**`, `api/**`, `main.py`, or `seed/**`.

### Exact files/directories safe to stage for first slice

Stage only:

- `backend/app/db/**`
- `backend/app/models/**`
- `backend/app/schemas/**`
- `backend/app/exceptions.py`

This boundary is minimal and reviewable, with low runtime-wiring risk and no observed secret/local/cache artifacts.

### Exact files/directories that must not be staged (first slice)

- `backend/app/services/**`
- `backend/app/api/**`
- `backend/app/main.py`
- `backend/app/core/**`
- `backend/app/seed/**`
- `backend/app/__init__.py`

Also never stage:
- any `backend/**/__pycache__/**`
- any `backend/**/*.pyc`
- `backend/.venv/**`
- `backend/.pytest_cache/**`
- any env-secret files

### Risks before first app commit

1. **Seed coupling gap in current sequence**  
   `backend/app/services/webhook_message_service.py` imports `app.seed.dev_ai_configuration` constant. If B1.5 is committed while B1.7 remains deferred, intermediate history can have broken imports.

2. **Hidden coupling if service files leak into first slice**  
   Service layer spans domain, AI, policy, and orchestration; adding any of it in B1.1 defeats minimality and weakens rollback clarity.

3. **Large schema/model sweep reviewability**  
   Even in foundation slice, broad adds can hide non-foundational churn; reviewer should validate no runtime behavior rewrites are bundled.

### Recommended commit message (first app slice)

`A4.2-B1.1 import backend foundation db-model-schema`

### Sequencing correction note

To preserve rollback-safe intermediate states:
- either move `backend/app/seed/**` before any service slice that imports it,  
- or explicitly split service slices so seed-dependent services are committed only after seed.

---

## Service-layer review (alpstein-reviewer) — A4.2-B1.2 preparation

### Review summary

**Pass with notes (GO with strict slice boundaries).**  
Service graph is mostly acyclic and layerable, but there is a concrete coupling hotspot (`webhook_message_service -> app.seed`) and two orchestration hotspots that must remain late in sequence for rollback-safe imports.

### Recommended service import order

1. **S1 — leaf policy/utility services (no DB/session orchestration glue)**
   - `tenant_context_validator.py`
   - `customer_language_detection.py`
   - `conversation_intent_policy.py`
   - `notification_policy_service.py`
   - `lead_signal_detection_service.py`
   - `pre_sales_prompt_instructions.py`
   - `greeting_prompt_instructions.py`
   - `intent_prompt_instructions.py`
   - `history_safety_prompt_instructions.py`
   - `conversation_intent_service.py`
   - `greeting_policy_service.py`

2. **S2 — model access leaf services**
   - `prompt_template_service.py`
   - `tenant_ai_profile_service.py`
   - `tenant_business_profile_service.py`
   - `tenant_channel_setting_service.py`
   - `tenant_knowledge_source_service.py`
   - `business_service.py`
   - `customer_service.py`
   - `conversation_service.py`
   - `lead_service.py`
   - `message_service.py`

3. **S3 — composed domain services**
   - `ai_configuration_service.py` (depends on prompt/tenant profile services)
   - `knowledge_retrieval_service.py` (depends on tenant_knowledge_source service)
   - `prompt_run_service.py`

4. **S4 — AI gateway boundary**
   - `ai_gateway/**`
   - `ai_gateway_service.py`
   - `ai_reply_fallback_service.py`

5. **S5 — prompt assembly boundary**
   - `prompt_builder_service.py`

6. **S6 — tracing/observability**
   - `langfuse_tracing_service.py`

7. **S7 — orchestration glue**
   - `ai_reply_orchestration_service.py`
   - `ai_reply_orchestration_coordinator.py`

8. **S8 — webhook integration endpoint service (last)**
   - `webhook_message_service.py`
   - plus prerequisite alignment for `app.seed.dev_ai_configuration` import

### Service-layer safe slices

- **Safe slice A (minimal first service slice):** S1 only (policy/utility + instruction builders).
- **Safe slice B:** S2 model-access leaves.
- **Safe slice C:** S3 composed domain services.
- **Safe slice D:** S4 gateway boundary.
- **Safe slice E:** S5 prompt builder.
- **Safe slice F:** S6 tracing.
- **Safe slice G:** S7 orchestration.
- **Safe slice H (last):** S8 webhook message service.

### Coupling hotspots

1. **`webhook_message_service.py`**  
   High coupling hub across business/customer/conversation/message/lead, AI coordinator/fallback, notification/signals, and webhook schemas.

2. **Seed coupling (explicit):**  
   `webhook_message_service.py` imports `PROMPT_TEMPLATE_CUSTOMER_REPLY_KEY` from `app.seed.dev_ai_configuration`.  
   This is the key ordering constraint for service import and rollback-safe intermediate states.

3. **`ai_reply_orchestration_service.py`**  
   Central fan-in: AI config, knowledge retrieval, message history, greeting/intent policies, prompt builder, gateway, tracing, prompt-run persistence.

4. **`prompt_builder_service.py`**  
   Policy + schema coupling hotspot; should stay after instruction/policy modules and before orchestration glue.

5. **`langfuse_tracing_service.py`**  
   Optional runtime observability, but imported by orchestration service; keep in dedicated slice to isolate non-core telemetry drift.

### Hidden runtime coupling findings

- No direct circular-import pattern found in `services/**` from static import scan.
- Practical runtime coupling remains high at orchestration and webhook integration layers (S7/S8), so importing these early would reduce reviewability and rollback safety.

### Rollback risks

1. Importing orchestration (`S7`) before prompt/gateway/core services (`S4/S5`) risks intermediate broken wiring.
2. Importing webhook integration (`S8`) before seed dependency availability creates import failures (`app.seed` coupling).
3. Mixing tracing with foundation/service leaves can hide runtime behavior differences unrelated to core request path.
4. Bundling `webhook_message_service.py` with broad service imports reduces bisect clarity in incident rollback.

### No-go combinations

- **No-go A:** `webhook_message_service.py` without `app.seed` dependency availability.
- **No-go B:** `ai_reply_orchestration_service.py` without `prompt_builder_service.py`, `ai_gateway_service.py`, `prompt_run_service.py`, and core composed services.
- **No-go C:** `api/bootstrap` service consumers imported before S7/S8 service stack is present.
- **No-go D:** tracing + webhook + orchestration in same first service commit.
- **No-go E:** giant `services/**` sweep as single commit.

### Exact safest first services slice

Stage only this first service-layer slice:

- `backend/app/services/tenant_context_validator.py`
- `backend/app/services/customer_language_detection.py`
- `backend/app/services/conversation_intent_policy.py`
- `backend/app/services/notification_policy_service.py`
- `backend/app/services/lead_signal_detection_service.py`
- `backend/app/services/pre_sales_prompt_instructions.py`
- `backend/app/services/greeting_prompt_instructions.py`
- `backend/app/services/intent_prompt_instructions.py`
- `backend/app/services/history_safety_prompt_instructions.py`
- `backend/app/services/conversation_intent_service.py`
- `backend/app/services/greeting_policy_service.py`

This is the smallest low-coupling, rollback-safe service import slice before domain/AI/orchestration glue.

---

## Test-layer review (alpstein-reviewer) — A4.2-T1 preparation

### Review summary

**Pass with notes (GO with strict sequencing).**  
`backend/tests/**` (45 files + `conftest.py`) is importable in rollback-safe slices if tests are committed **after** their runtime dependency layers are already in git. The safest first test commit is schema/exception-only; migration, model, service, orchestration, and API/webhook tests must follow the app baseline slices.

### Prerequisite alignment (app baseline before tests)

| Test slice | Requires tracked app baseline |
|------------|-------------------------------|
| T1 pure schema/exception | B1.1 (`schemas/**`, `exceptions.py`) |
| T2 model contract | B1.1 (`models/**`, `db/**`) |
| T3 migration reproducibility | A4.2-B2 (`alembic/**`, `alembic.ini`) |
| T4 S1 utility/policy | B1.2-S1 service slice |
| T5 domain services | B1.2-S2/S3 |
| T6 prompt assembly | B1.2-S5 + instruction modules (S1) |
| T7 AI gateway/fallback/tracing | B1.2-S4/S6 |
| T8 orchestration | B1.2-S7 |
| T9 webhook/API | B1.2-S8 + `api/**` + `main.py` + `core/**` + `seed/**` (seed coupling) |

### Recommended tests import order

1. **T1 — Pure schema + exception tests (no services, no DB, no API)**
   - `conftest.py`
   - `test_exceptions.py`
   - `test_business_not_found_error.py`
   - `test_webhook_schemas.py`
   - `test_webhook_attribution_schemas.py`
   - `test_webhook_response_schemas.py`

2. **T2 — Model/DB contract tests (foundation)**
   - `test_database_models.py`
   - `test_ai_configuration_models.py`

3. **T3 — Migration reproducibility tests (isolated; requires B2)**
   - `test_alembic_migration.py`  
   - Reads `backend/alembic/versions/*.py` from disk; commit only after/with migration baseline.

4. **T4 — S1 utility/policy service tests**
   - `test_tenant_context_validator.py`
   - `test_customer_language_detection.py`
   - `test_conversation_intent_service.py`
   - `test_greeting_policy_service.py`
   - `test_notification_policy_service.py`
   - `test_lead_signal_detection_service.py`

5. **T5 — Domain service unit tests (mocked AsyncSession)**
   - `test_business_service.py`
   - `test_customer_service.py`
   - `test_conversation_service.py`
   - `test_lead_service.py`
   - `test_message_service.py`
   - `test_message_conversation_context.py`
   - `test_ai_configuration_services.py`
   - `test_knowledge_retrieval_service.py`
   - `test_prompt_run_service.py`
   - `test_ai_configuration_service.py` (imports `app.seed` constant — see coupling)

6. **T6 — Prompt builder / gating / HF-1 / CIP tests**
   - `test_prompt_builder_service.py`
   - `test_history_safety_prompt_builder.py`
   - `test_conversation_intent_prompt_builder.py`
   - `test_greeting_prompt_builder.py`
   - `test_product_behavior_gating.py`

7. **T7 — AI gateway, fallback, Langfuse**
   - `test_ai_gateway_service.py`
   - `test_ai_reply_fallback_service.py`
   - `test_langfuse_tracing_service.py`

8. **T8 — Orchestration (mocked)**
   - `test_ai_reply_orchestration_service.py`
   - `test_ai_reply_orchestration_coordinator.py`

9. **T9 — Webhook service wiring (mocked, no HTTP)**
   - `test_webhook_message_service.py`
   - `test_webhook_message_ai_wiring.py`
   - `test_webhook_message_lead_wiring.py`

10. **T10 — API / HTTP / full-path integration (last)**
    - `test_health.py`
    - `test_webhook_message_route.py`
    - `test_webhook_token_auth.py`
    - `test_operator_business_context.py`
    - `test_t12_webhook_http_regression.py`
    - `test_t11_ai_webhook_integration.py`

11. **T11 — Seed tests (optional separate; after `app/seed/**`)**
    - `test_dev_ai_configuration_seed.py`

### Safe test slices

| Slice | Files | Safe when |
|-------|-------|-----------|
| T1 | 6 | B1.1 schemas/exceptions tracked |
| T2 | 2 | B1.1 models/db tracked |
| T3 | 1 | B2 alembic tracked |
| T4 | 6 | B1.2-S1 tracked |
| T5 | 10 | B1.2-S2/S3 (+ seed if including `test_ai_configuration_service`) |
| T6 | 5 | B1.2-S1 + S5 |
| T7 | 3 | B1.2-S4/S6 |
| T8 | 2 | B1.2-S7 |
| T9 | 3 | B1.2-S8 |
| T10 | 6 | api + main + core + full stack |
| T11 | 1 | `app/seed/**` |

### Coupling risks

1. **`test_alembic_migration.py` ↔ migration baseline** — file-path reads of `alembic/versions/`; commit with or immediately after B2.
2. **Seed constant coupling** — `test_ai_configuration_service.py`, `test_t11_ai_webhook_integration.py` import `app.seed.dev_ai_configuration`.
3. **`app.main` cluster** — health, webhook routes, T12, operator context tests need API/bootstrap slice.
4. **Orchestration mock depth** — T8/T10 tests fan in many services; git import early is OK, execution needs B1.2 mostly complete.
5. **Prompt-builder tests** — need S1 instruction modules + S5 `prompt_builder_service`.
6. **No live DB in most unit tests** — migration tests are source-inspection only; does not replace B2 or runtime DB verification.

### Tests coupled to unimported runtime layers (execution blocked)

| Layer missing | Tests blocked for execution |
|---------------|-----------------------------|
| `alembic/**` | `test_alembic_migration.py` |
| S1 services | T4 |
| S2–S3 services | T5 |
| `prompt_builder_service` | T6 |
| S4 gateway | `test_ai_gateway_service.py`, parts of T11 |
| S7 orchestration | T8, T9 wiring, T10 integration |
| `api/**`, `main.py` | T10 HTTP tests |
| `app/seed/**` | `test_dev_ai_configuration_seed.py`, seed-dependent integration |

### Tests requiring AI orchestration layer

- `test_ai_reply_orchestration_service.py`
- `test_ai_reply_orchestration_coordinator.py`
- `test_webhook_message_ai_wiring.py`
- `test_webhook_message_lead_wiring.py`
- `test_t11_ai_webhook_integration.py`

### Tests requiring webhook runtime

- `test_webhook_message_service.py`
- `test_webhook_message_ai_wiring.py`
- `test_webhook_message_lead_wiring.py`
- `test_webhook_message_route.py`
- `test_webhook_token_auth.py`
- `test_t11_ai_webhook_integration.py`
- `test_t12_webhook_http_regression.py`
- `test_operator_business_context.py`

### Migration / DB / model / schema tests

| Category | File | Notes |
|----------|------|-------|
| Migration source audit | `test_alembic_migration.py` | 0001–0007; no live DB |
| ORM metadata | `test_database_models.py` | `Base.metadata` contract |
| AI config models | `test_ai_configuration_models.py` | FK/column constraints |
| Webhook schemas | `test_webhook_schemas.py`, attribution, response | schema-only |

### Service utility slice tests (S1-aligned)

- `test_conversation_intent_service.py`
- `test_greeting_policy_service.py`
- `test_customer_language_detection.py`
- `test_notification_policy_service.py`
- `test_lead_signal_detection_service.py`
- `test_tenant_context_validator.py`

### Tests unsafe for early baseline import (as runnable baseline)

- T10 before `app.main` + routes in git
- `test_alembic_migration.py` before B2
- T6 before prompt builder + policy modules
- T8/T9 before orchestration/webhook services
- Single `backend/tests/**` commit

### No-go combinations

- **No-go T-A:** `test_alembic_migration.py` bundled with unrelated app source (pair with B2).
- **No-go T-B:** HTTP tests before API/bootstrap import.
- **No-go T-C:** `test_t11_ai_webhook_integration.py` with partial service baseline.
- **No-go T-D:** Prompt-builder tests before S1 + S5 tracked.
- **No-go T-E:** Full `backend/tests/**` in one commit.
- **No-go T-F:** Test commit mixed with scripts/n8n/specs.

### Rollback-safe test import sequencing

1. Commit app slices: B1.1 → B2 → B1.2-S* → API/bootstrap.  
2. Import tests T1→T11 matching completed app layers.  
3. Optionally run targeted pytest per slice after each test commit.  
4. Keep T10 integration tests last for clean bisect history.

### Exact safest first test slice

Stage only:

- `backend/tests/conftest.py`
- `backend/tests/test_exceptions.py`
- `backend/tests/test_business_not_found_error.py`
- `backend/tests/test_webhook_schemas.py`
- `backend/tests/test_webhook_attribution_schemas.py`
- `backend/tests/test_webhook_response_schemas.py`

**Prerequisite:** B1.1 foundation already tracked.  
**Recommended commit message:** `A4.2-T1 import backend test schema exception slice`

### Tests that must wait for orchestration / API imports

**Wait for orchestration (B1.2-S7):**
- `test_ai_reply_orchestration_service.py`
- `test_ai_reply_orchestration_coordinator.py`
- `test_webhook_message_ai_wiring.py`
- `test_webhook_message_lead_wiring.py`
- `test_t11_ai_webhook_integration.py` (also needs API + seed)

**Wait for API/bootstrap (`api/**`, `main.py`, `core/config.py`):**
- `test_health.py`
- `test_webhook_message_route.py`
- `test_webhook_token_auth.py`
- `test_operator_business_context.py`
- `test_t12_webhook_http_regression.py`

**Wait for webhook service (B1.2-S8):**
- `test_webhook_message_service.py`
- T9/T10 tests importing `WebhookMessageService`

### GO / NO-GO for test baseline import

- **GO** for phased test import per T1–T11 after matching app commits.
- **NO-GO** for single-commit full test sweep or claiming integration coverage before orchestration/API baselines exist in git.

---
## Runtime bootstrap review (alpstein-reviewer) — A4.2-R1

### Review summary
**Pass with notes (import-graph boundary is the problem).**  
`backend/app/main.py` is not itself heavy, but importing it forces import of `app.api.routes.webhook`, and that module constructs `WebhookMessageService` at module-import time. As a result, **full runtime bootstrap (`app.main`) cannot be rollback-safe until the seed + webhook message service + orchestration + tracing/gateway dependencies are already committed**.

### Recommended bootstrap import order
1. **Core settings only (no FastAPI routes)**
   - `backend/app/core/config.py`
2. **DB engine/session factories (import-time engine creation)**
   - `backend/app/db/session.py`
3. **Webhook token auth + health router (no webhook endpoint service construction)**
   - `backend/app/api/webhook_auth.py`
   - `backend/app/api/routes/health.py`
4. **Avoid `backend/app/main.py` until “webhook integration endpoint service” is commit-complete**
   - `backend/app/main.py` and `backend/app/api/routes/webhook.py` are the boundary imports because `webhook.py` instantiates `WebhookMessageService()` at import time.

### Rollback-safe runtime slices
These slices are defined by “is it safe to import these modules from git rollback history without hitting missing-module import errors and without depending on later wiring slices?”

#### R0 — Core runtime config slice (safe earliest)
- `backend/app/core/config.py`

#### R1 — Runtime import slice for auth + health only (safe; avoids webhook service instantiation)
- `backend/app/db/session.py` (imports SQLAlchemy + async engine; no DB connection required at import)
- `backend/app/api/webhook_auth.py`
- `backend/app/api/routes/health.py`

#### R2 — Full app bootstrap slice (safe, but late; requires webhook integration + orchestration)
- `backend/app/main.py`
- `backend/app/api/routes/webhook.py`
- `backend/app/services/webhook_message_service.py`
- `backend/app/seed/dev_ai_configuration.py` (seed coupling; required for import-time constant)
- all transitive dependencies imported by `WebhookMessageService` defaults, including:
  - `backend/app/services/ai_reply_orchestration_service.py`
  - `backend/app/services/prompt_builder_service.py`
  - `backend/app/services/ai_gateway_service.py` and `backend/app/services/ai_gateway/**`
  - `backend/app/services/langfuse_tracing_service.py` (requires `langfuse` python package installed)
  - `backend/app/services/prompt_run_service.py`
  - `backend/app/services/ai_configuration_service.py`, `knowledge_retrieval_service.py`, and the domain leaf services they compose

### Startup coupling hotspots
1. **Module-level service construction in the webhook route**
   - `backend/app/api/routes/webhook.py`:
     - `webhook_message_service = WebhookMessageService()` at module import time
   - **Risk:** any rollback-safe import must ensure *all* transitive imports needed by `WebhookMessageService.__init__` and default dependencies are already present in git.

2. **Seed coupling via an import-time constant**
   - `backend/app/services/webhook_message_service.py` imports:
     - `PROMPT_TEMPLATE_CUSTOMER_REPLY_KEY` from `backend/app/seed/dev_ai_configuration.py`
   - `dev_ai_configuration.py` imports many model modules at import time.
   - **Risk:** runtime bootstrap attempts that “should not need seed/models” still fail because the seed module is imported for a constant.

3. **Langfuse tracing module import dependency**
   - `backend/app/services/langfuse_tracing_service.py` imports `from langfuse import Langfuse, propagate_attributes` at module import time.
   - **Risk:** runtime bootstrap will fail to import if `langfuse` is missing from the Python environment, even if tracing is “disabled” by env settings.

4. **DB engine created at import time**
   - `backend/app/db/session.py` creates `engine = create_async_engine(settings.database_url, ...)` at module import time.
   - **Risk:** import-time side effect increases blast radius of “early baseline import”; missing SQLAlchemy/asyncpg support breaks bootstrap import.

### No-go combinations
1. **No-go R-A:** Import `backend/app/main.py` (or `backend/app/api/routes/webhook.py`) before the webhook integration endpoint service dependency stack is committed.
2. **No-go R-B:** Import the webhook route (`app.api.routes.webhook`) in an intermediate baseline that has not committed `app.seed.dev_ai_configuration.py` (seed constant coupling).
3. **No-go R-C:** Import `app.api.routes/webhook` in an intermediate baseline that has not committed orchestration defaults (`AiReplyOrchestrationService` + prompt builder/gateway/prompt run + tracing module).
4. **No-go R-D:** Treat “health-only” as equivalent to “app.main import”: `test_health.py` imports `app.main`, which imports webhook routes too.

### Hidden runtime assumptions
1. **Python dependency availability for import**
   - `langfuse` must be installed to import `langfuse_tracing_service.py`.
   - `asyncpg` must be available for SQLAlchemy async engine support.
   - `httpx` must be available for AI gateway modules (import-time).
2. **Env var prefix and defaults**
   - Settings are loaded from environment variables with prefix `ALPSTEIN_AI_`.
   - `environment` defaults to `"production"`, which affects Langfuse tracing enablement logic (but not the module import itself).
3. **Webhook auth token requirement is runtime-only**
   - `N8N_BACKEND_API_TOKEN` affects whether requests are accepted, but missing token should not break import—only runtime calling.
4. **Database connectivity is runtime-only**
   - DB engine is constructed at import time, but actual connection failures only surface when endpoints/tests execute DB operations.

### Exact safest first runtime/bootstrap slice
Use this as the earliest “rollback-safe” import target set (importing these should not force webhook integration / orchestration wiring):
- `backend/app/core/config.py`
- `backend/app/db/session.py`
- `backend/app/api/webhook_auth.py`
- `backend/app/api/routes/health.py`

Explicitly: **do not import `backend/app/main.py` or `backend/app/api/routes/webhook.py`** in a minimal runtime baseline slice; those imports pull in `WebhookMessageService` and therefore require the late webhook integration stack.

### Runtime reproducibility blockers
`app.main` (and `app.api.routes.webhook`) imports are blocked for rollback-safe reproducibility until all of the following are committed:
1. `backend/app/api/routes/webhook.py` import can construct `WebhookMessageService` (module-level instantiation).
2. `backend/app/services/webhook_message_service.py` can import its seed constant:
   - `backend/app/seed/dev_ai_configuration.py` must be present in git (seed coupling).
3. The orchestration default chain is available:
   - `AiReplyOrchestrationService` → prompt builder → AI gateway → prompt run persistence
4. `backend/app/services/langfuse_tracing_service.py` can import `langfuse` package (environment dependency).

---
## Orchestration-runtime review (alpstein-reviewer) — A4.2-O1

### Review summary
**Pass with notes (high fan-in; must remain late).**  
The orchestration core (`AiReplyOrchestrationService` + `AiReplyOrchestrationCoordinator`) is a **fan-in hub** across AI configuration, knowledge retrieval, message history, greeting/intent policy, prompt building, AI gateway, tracing, and prompt-run persistence. It is rollback-safe **only** if imported after its prerequisite services are already in git; it must be kept separate from the webhook integration endpoint stack (`WebhookMessageService` + route wiring).

### Orchestration import order
Import orchestration only after these layers exist as independent slices:
1. **Foundation (B1.1)**: `db/**`, `models/**`, `schemas/**`, `exceptions.py`
2. **Service leaves + policy modules (S1–S3)**:
   - message history (`MessageService`), configuration loaders (`AiConfigurationService`), knowledge retrieval
3. **AI boundary services (S4)**:
   - `ai_gateway/**` and `ai_gateway_service.py`, plus `ai_reply_fallback_service.py`
4. **Prompt builder (S5)**:
   - `prompt_builder_service.py` (depends on S1 instruction builders + schemas)
5. **Tracing (S6)**:
   - `langfuse_tracing_service.py` (environment/package dependency)
6. **Orchestration glue (S7)**
   - `ai_reply_orchestration_service.py`
   - `ai_reply_orchestration_coordinator.py`

### Rollback-safe orchestration slices
Because the coordinator imports the orchestration service module, orchestration cannot be “micro-sliced” smaller than S7 without breaking imports.

#### O1 — Safest first orchestration slice (S7-only, no webhook wiring)
Stage only:
- `backend/app/services/ai_reply_orchestration_service.py`
- `backend/app/services/ai_reply_orchestration_coordinator.py`

**Prerequisite condition:** S1–S6 slices already committed (and their transitive imports resolved).

#### O2 — Orchestration execution slice (still no webhook endpoint)
Add only if you need execution of orchestration in isolation (still keep webhook service out):
- keep O1
- ensure runtime dependencies are present in environment (see “hidden side effects”)

### Startup/runtime coupling hotspots
1. **Webhook route import-time construction triggers orchestration**
   - `backend/app/api/routes/webhook.py` constructs `WebhookMessageService()` at module import time.
   - `WebhookMessageService.__init__` constructs `AiReplyOrchestrationCoordinator()` by default, which constructs `AiReplyOrchestrationService()` by default.
   - **Impact:** importing the webhook route is effectively importing the entire orchestration graph.

2. **Orchestration service fan-in**
   - `AiReplyOrchestrationService` depends on:
     - config loader (`AiConfigurationService`)
     - knowledge retrieval (`KnowledgeRetrievalService`)
     - history (`MessageService`)
     - prompt builder (`PromptBuilderService`)
     - AI gateway (`AiGatewayService`)
     - prompt-run persistence (`PromptRunService`)
     - greeting/intent (`GreetingPolicyService`, `ConversationIntentService`, gating policy)
     - tracing (`LangfuseTracingService`)
   - **Impact:** any missing service slice breaks import, and any “partial” import reduces rollback bisect clarity.

3. **Prompt-run persistence is DB-model coupled**
   - `PromptRunService` imports the ORM model `PromptRun` and validates tenant/business/message scope.
   - **Impact:** orchestration imports are not meaningful without B1.1 models.

4. **Tracing import dependency is package-coupled**
   - `langfuse_tracing_service.py` imports `langfuse` at module import time.
   - **Impact:** orchestration import will fail in environments missing `langfuse`, even when tracing is disabled by settings.

### No-go combinations
1. **No-go O-A:** Commit/import orchestration (S7) in the same commit as webhook runtime stack (`webhook_message_service.py` and/or `api/routes/webhook.py`).
2. **No-go O-B:** Import `app.main` as a proxy for “orchestration present”. `app.main` pulls in webhook routes, which eagerly construct `WebhookMessageService`.
3. **No-go O-C:** Import S7 without S5/S4/S3 present (prompt builder, AI gateway, and composed domain services).
4. **No-go O-D:** Include `seed/**` with orchestration unless explicitly required for a constant dependency (seed is a webhook-stack concern in current wiring).

### Hidden runtime side effects (import-time vs call-time)
1. **Import-time dependency on Python packages**
   - `langfuse` must be installed to import tracing service.
   - `httpx` must be installed to import AI gateway modules.
   - SQLAlchemy async stack must be installed to import DB/session types.
2. **Import-time engine construction**
   - DB engine is constructed in `db/session.py` at import time (does not connect yet).
3. **Call-time network + external dependency**
   - AI gateway performs HTTP calls only when `complete()` executes; missing `OPENAI_API_KEY` degrades to a controlled error result (does not crash import).
4. **Call-time DB dependency**
   - orchestration executes DB reads/writes through injected `AsyncSession`; failures surface at runtime, not import.

### Orchestration reproducibility blockers
Orchestration is not rollback-safe until:
1. **All prerequisite services exist in git**
   - config loader, knowledge retrieval, message history, prompt builder, gateway, prompt run persistence, greeting/intent policy modules.
2. **Python environment can import tracing + gateway deps**
   - `langfuse`, `httpx`, and SQLAlchemy async dependencies installed per `backend/requirements.txt`.
3. **No early import path forces webhook runtime stack**
   - avoid importing `app.main` / webhook route as a “smoke import” until webhook stack is committed.

### Exact conditions before `app.main` import becomes safe
`backend/app/main.py` becomes rollback-safe to import **only when all of the following are true**:
1. `backend/app/api/routes/webhook.py` exists and all of its imports exist.
2. `backend/app/api/routes/webhook.py` can construct `webhook_message_service = WebhookMessageService()` without raising import errors.
3. `WebhookMessageService` transitive imports all exist, including the seed constant dependency:
   - `backend/app/seed/dev_ai_configuration.py` must exist (due to `PROMPT_TEMPLATE_CUSTOMER_REPLY_KEY` import)
4. Orchestration is complete and importable:
   - S1–S7 slices present (prompt builder, gateway, tracing, prompt run persistence, etc.)
5. The Python environment has required packages installed (especially `langfuse`).

---
## Webhook-runtime ingress review (alpstein-reviewer) — A4.2-W1

### Review summary
**Pass with notes (high ingress fan-in, strict late import boundary).**  
`backend/app/api/routes/webhook.py` is a thin route handler, but it performs **module-level instantiation** of `WebhookMessageService`, making webhook ingress import safety depend on the full webhook runtime chain (seed constant, orchestration, gateway/tracing stack, and service leaves). The safest first webhook runtime step is to keep webhook ingress out until prerequisites are complete.

### Webhook runtime import order
1. **Ingress prerequisites (already tracked before webhook ingress)**
   - B1.1 foundation (`db/**`, `models/**`, `schemas/**`, `exceptions.py`)
   - service leaves/composed/orchestration stack (S1–S7)
   - seed constant provider (`backend/app/seed/dev_ai_configuration.py`)
2. **Webhook service ingress core**
   - `backend/app/services/webhook_message_service.py`
3. **Webhook route ingress entrypoint**
   - `backend/app/api/routes/webhook.py`
4. **Only after webhook route is safe, allow `app.main` import**
   - `backend/app/main.py`

### Rollback-safe webhook slices
#### W0 — Safest first webhook runtime slice
- **No webhook ingress files** (`webhook.py` and `webhook_message_service.py` excluded).
- Keep only previously safe runtime/bootstrap slices active.

#### W1 — Webhook service slice (late)
- `backend/app/services/webhook_message_service.py`
- only after seed + orchestration prerequisites exist.

#### W2 — Webhook route slice (latest ingress activation)
- `backend/app/api/routes/webhook.py`
- only after W1 is import-safe.

### Ingress/runtime coupling hotspots
1. **Module-level service construction (route import side effect)**
   - `backend/app/api/routes/webhook.py` sets `webhook_message_service = WebhookMessageService()` at import time.
   - Risk: importing route immediately evaluates transitive service graph.

2. **Webhook service as high-coupling hub**
   - `WebhookMessageService` composes business/customer/conversation/message/lead services + notification policy + AI orchestration coordinator + fallback/config services.
   - Risk: large fan-in makes partial imports brittle and hard to bisect.

3. **Seed constant hard-coupling**
   - `webhook_message_service.py` imports `PROMPT_TEMPLATE_CUSTOMER_REPLY_KEY` from `app.seed.dev_ai_configuration`.
   - Risk: webhook ingress import fails if seed module is absent/untracked.

4. **Orchestration chain transitively required**
   - `AiReplyOrchestrationCoordinator` defaults to `AiReplyOrchestrationService`, which depends on prompt builder, gateway, tracing, prompt run persistence.
   - Risk: webhook service import is effectively orchestration import.

5. **DB session dependency in route lifecycle**
   - route depends on `get_db_session`; session commit/rollback path is route-managed.
   - Risk: runtime failures surface in request handling if DB/env invalid.

### Hidden startup side effects
1. **Import-time object creation**
   - Webhook route import creates `WebhookMessageService` instance immediately.
2. **Import-time DB engine construction**
   - `db/session.py` builds async engine on import (no immediate connection, but dependency required).
3. **Import-time package dependency checks**
   - tracing path depends on `langfuse` package importability via orchestration chain.
4. **Request-time transaction side effects**
   - successful path commits; specific exception paths rollback (`BusinessNotFoundError`, `TenantContextError`).
   - unhandled exceptions rely on framework exception handling; explicit rollback for unexpected exceptions is not route-coded.

### No-go combinations
1. **No-go W-A:** stage/import `backend/app/api/routes/webhook.py` without `backend/app/services/webhook_message_service.py`.
2. **No-go W-B:** stage/import webhook service without `backend/app/seed/dev_ai_configuration.py`.
3. **No-go W-C:** stage/import webhook ingress before orchestration prerequisites (S4/S5/S6/S7) are import-safe.
4. **No-go W-D:** combine webhook ingress activation with unrelated broad `services/**` or API/bootstrap sweeps.
5. **No-go W-E:** treat `app.main` import as safe before webhook route and service chain are fully import-safe.

### Safest first webhook runtime slice
For A4.2-W1, the safest-first webhook runtime slice is:
- **stage nothing from webhook ingress stack yet**:
  - do **not** stage `backend/app/api/routes/webhook.py`
  - do **not** stage `backend/app/services/webhook_message_service.py`

Rationale: ingress files are late-bound high-coupling modules with import-time side effects; first safe action is to complete prerequisites and only then import webhook ingress in isolated late slices.

### Webhook reproducibility blockers
Webhook ingress reproducibility is blocked until all conditions hold:
1. `webhook_message_service.py` transitive imports resolved (domain services + orchestration + prompt builder + gateway + tracing + prompt run).
2. seed constant import resolved (`app.seed.dev_ai_configuration` available).
3. Python dependencies installed for transitive imports (notably `langfuse`, SQLAlchemy async stack, `httpx`).
4. DB/session config importable (`core/config.py`, `db/session.py`) for route dependency injection.

### Exact conditions before `webhook.py` import becomes safe
`backend/app/api/routes/webhook.py` import is safe only when:
1. `backend/app/services/webhook_message_service.py` is present and import-safe.
2. `WebhookMessageService()` default construction succeeds at module import time.
3. Seed constant dependency is present:
   - `backend/app/seed/dev_ai_configuration.py` import succeeds.
4. Orchestration chain imports succeed:
   - coordinator + orchestration service + prompt builder + gateway + tracing + prompt run persistence.
5. Runtime dependencies for transitive imports are installed (`langfuse`, `httpx`, SQLAlchemy async dependencies).

---
## Prerequisite-service review (alpstein-reviewer) — A4.2-P1

### Review summary
**Pass with notes (GO with strict prerequisite slicing).**  
Before webhook ingress (`webhook_message_service.py` + `api/routes/webhook.py`) can be imported rollback-safely, the missing prerequisite services must be imported in a narrow order that isolates high-risk coupling points: prompt assembly, gateway boundary, prompt-run persistence, tracing import dependency, configuration/knowledge loaders, then seed constant provider.

### Next safe prerequisite import order
1. **P1-S5 prompt assembly boundary**
   - `backend/app/services/prompt_builder_service.py`
2. **P1-S4 gateway boundary**
   - `backend/app/services/ai_gateway_service.py`
   - `backend/app/services/ai_gateway/**`
3. **P1-S3 composed data loaders**
   - `backend/app/services/ai_configuration_service.py`
   - `backend/app/services/knowledge_retrieval_service.py`
4. **P1-S3 audit persistence**
   - `backend/app/services/prompt_run_service.py`
5. **P1-S6 tracing boundary**
   - `backend/app/services/langfuse_tracing_service.py`
6. **P1-seed constant provider (last prerequisite before webhook service)**
   - `backend/app/seed/dev_ai_configuration.py`

Rationale for order:
- `prompt_builder_service.py` and gateway modules are orchestration-critical and independent of seed.
- `prompt_run_service.py` and config/knowledge loaders enforce tenant/business scope and DB persistence contracts.
- tracing is optional at runtime but mandatory for importability due to direct `langfuse` import.
- seed is isolated late to avoid mixing dev bootstrap payload with generic orchestration services.

### Rollback-safe prerequisite slices
#### Slice P-A (safest first prerequisite slice)
- `backend/app/services/prompt_builder_service.py`

#### Slice P-B
- `backend/app/services/ai_gateway_service.py`
- `backend/app/services/ai_gateway/**`

#### Slice P-C
- `backend/app/services/ai_configuration_service.py`
- `backend/app/services/knowledge_retrieval_service.py`

#### Slice P-D
- `backend/app/services/prompt_run_service.py`

#### Slice P-E
- `backend/app/services/langfuse_tracing_service.py`

#### Slice P-F (seed prerequisite)
- `backend/app/seed/dev_ai_configuration.py`

### Hidden coupling risks
1. **Seed constant coupling into webhook service**
   - `webhook_message_service.py` imports `PROMPT_TEMPLATE_CUSTOMER_REPLY_KEY` from `app.seed.dev_ai_configuration`.
   - Risk: webhook service import fails if seed file is missing.

2. **Tracing package import at module load**
   - `langfuse_tracing_service.py` imports `langfuse` at module import time.
   - Risk: import failure even when tracing feature is disabled in env.

3. **Prompt-run persistence model coupling**
   - `prompt_run_service.py` imports `PromptRun` model and validates tenant/business/conversation/message scope.
   - Risk: requires B1.1 model baseline to be already present and consistent.

4. **Gateway package dependency**
   - `ai_gateway_service.py` and `ai_gateway/_openai.py` import `httpx`.
   - Risk: environment importability blocker if dependencies are incomplete.

5. **Configuration/knowledge loaders depend on tenant-scoped service leaves**
   - `AiConfigurationService` and `KnowledgeRetrievalService` depend on underlying tenant profile/source services.
   - Risk: importing these before S2 leaves reduces rollback safety and can produce broken imports.

### No-go combinations
1. **No-go P-A:** Stage `webhook_message_service.py` before seed prerequisite (`app/seed/dev_ai_configuration.py`).
2. **No-go P-B:** Stage tracing service with webhook ingress in same commit (hard to isolate `langfuse` import failures).
3. **No-go P-C:** Stage gateway boundary + webhook ingress + route in one sweep.
4. **No-go P-D:** Stage `app.main` before prerequisites + webhook service + webhook route are all import-safe.
5. **No-go P-E:** Stage seed together with unrelated broad `models/**`/`services/**` sweep (reduced bisect clarity).

### Exact safest first prerequisite slice
Stage only:
- `backend/app/services/prompt_builder_service.py`

This is the smallest prerequisite slice that advances webhook-readiness without introducing seed, ingress, or package-heavy tracing side effects.

### Exact conditions before `webhook_message_service.py` can be staged
`backend/app/services/webhook_message_service.py` is safe to stage only when all are true:
1. **Service prerequisites present/importable**
   - `prompt_builder_service.py`
   - `ai_gateway_service.py` + `ai_gateway/**`
   - `ai_configuration_service.py`
   - `knowledge_retrieval_service.py`
   - `prompt_run_service.py`
   - `langfuse_tracing_service.py`
2. **Seed constant provider present/importable**
   - `backend/app/seed/dev_ai_configuration.py`
3. **Orchestration chain already import-safe**
   - `ai_reply_orchestration_coordinator.py`
   - `ai_reply_orchestration_service.py`
4. **Environment import dependencies available**
   - `langfuse`, `httpx`, SQLAlchemy async stack installed
5. **Ingress still isolated**
   - stage `webhook_message_service.py` before `api/routes/webhook.py` and before `app.main` to keep rollback boundaries clear.

---
## Remaining-prerequisite-gap review (alpstein-reviewer) — A4.2-P2

### Review summary
**Pass with notes (all listed prerequisites are still baseline-missing in git).**  
For the requested prerequisite set, none are currently reproducibly tracked (`git ls-files` returns empty for all listed paths). As a result, webhook ingress (`webhook_message_service.py`, `webhook.py`, `app.main`) remains blocked for rollback-safe import.

### Classification (requested items)
| Item | Classification | Notes |
|---|---|---|
| `backend/app/services/ai_gateway_service.py` | **fully missing** + **unsafe to import yet** | Not tracked in git baseline; gateway boundary prerequisite remains absent. |
| `backend/app/services/ai_gateway/**` | **fully missing** + **unsafe to import yet** | `__init__.py` and `_openai.py` untracked; required by gateway service and tracing. |
| `backend/app/services/langfuse_tracing_service.py` | **fully missing** + **unsafe to import yet** | Untracked and package-coupled (`langfuse` import at module load). |
| `backend/app/services/prompt_run_service.py` | **fully missing** + **unsafe to import yet** | Untracked; required for orchestration prompt-run persistence path. |
| `backend/app/services/ai_configuration_service.py` | **fully missing** + **unsafe to import yet** | Untracked; prerequisite for orchestration + webhook fallback behavior resolution. |
| `backend/app/services/knowledge_retrieval_service.py` | **fully missing** + **unsafe to import yet** | Untracked; orchestration dependency for prompt context. |
| `backend/app/seed/dev_ai_configuration.py` | **fully missing** + **unsafe to import yet** | Untracked; required by webhook service constant import (`PROMPT_TEMPLATE_CUSTOMER_REPLY_KEY`). |

No items in this list are currently “already reproducibly tracked” or “partially tracked”.

### Exact remaining reproducibility gaps
1. Missing gateway boundary in git baseline:
   - `ai_gateway_service.py`
   - `ai_gateway/**`
2. Missing orchestration-adjacent runtime prerequisites:
   - `prompt_run_service.py`
   - `ai_configuration_service.py`
   - `knowledge_retrieval_service.py`
3. Missing tracing module:
   - `langfuse_tracing_service.py`
4. Missing seed constant provider used by webhook service:
   - `seed/dev_ai_configuration.py`

### Next safest prerequisite slice
Given the current gap state, the next safest rollback-safe prerequisite slice remains:
- `backend/app/services/prompt_builder_service.py`

Then continue with previously defined prerequisite ordering:
1. gateway boundary (`ai_gateway_service.py` + `ai_gateway/**`)
2. config/knowledge loaders
3. prompt-run persistence
4. tracing
5. seed

### Blockers before `webhook_message_service.py`
`webhook_message_service.py` is blocked until:
1. all listed prerequisites above are tracked and import-safe,
2. seed constant provider is tracked (`seed/dev_ai_configuration.py`),
3. orchestration modules are already tracked/import-safe,
4. runtime deps available (`langfuse`, `httpx`, SQLAlchemy async stack).

### Blockers before `webhook.py`
`backend/app/api/routes/webhook.py` is blocked until:
1. `webhook_message_service.py` is tracked and import-safe,
2. module-level `WebhookMessageService()` construction succeeds,
3. all transitive prerequisites (gateway/config/knowledge/prompt-run/tracing/seed/orchestration) are tracked and import-safe.

### Blockers before `app.main`
`backend/app/main.py` is blocked until:
1. `backend/app/api/routes/webhook.py` is tracked and import-safe,
2. `webhook_message_service.py` chain is import-safe,
3. transitive runtime dependencies for webhook/orchestration stack are available,
4. webhook ingress stack is committed in isolated rollback-safe order (service before route before main).

---
## Observability-runtime review (alpstein-reviewer) — A4.2-OBS1

### Review summary
**Pass with notes (GO as isolated prerequisite slice).**  
Observability runtime is split across two different risk profiles: `prompt_run_service.py` (DB persistence, tenant-scope guardrails) and `langfuse_tracing_service.py` (external package/env-gated tracing with import-time dependency on `langfuse`). Both are prerequisites for orchestration/webhook reproducibility but should be imported in isolated slices to preserve rollback clarity.

### Observability import order
1. **Prompt-run persistence first**
   - `backend/app/services/prompt_run_service.py`
2. **Tracing second**
   - `backend/app/services/langfuse_tracing_service.py`
3. **CIP-C trace metadata schema readiness (non-runtime wiring marker)**
   - `backend/app/schemas/langfuse_intent_trace.py` (optional in same observability review stream, but keep separate from runtime ingress)

Rationale:
- Prompt-run persistence is core backend auditability and does not require external tracing package.
- Tracing has stricter environment/package coupling and should remain isolated for easier rollback if import/runtime issues appear.

### Rollback-safe observability slices
#### OBS-A — Safest first observability slice
- `backend/app/services/prompt_run_service.py`

#### OBS-B — Tracing slice
- `backend/app/services/langfuse_tracing_service.py`

#### OBS-C — CIP-C observability metadata readiness (optional prep)
- `backend/app/schemas/langfuse_intent_trace.py`

### Startup/runtime coupling hotspots
1. **Orchestration hard dependency fan-in**
   - `AiReplyOrchestrationService` imports both `PromptRunService` and `LangfuseTracingService`.
   - Effect: orchestration import safety depends on both observability modules being import-safe.

2. **Tracing module import-time package dependency**
   - `langfuse_tracing_service.py` imports `from langfuse import Langfuse, propagate_attributes` at module load.
   - Effect: import fails if `langfuse` is missing, regardless of runtime feature flags.

3. **PromptRun persistence DB/model coupling**
   - `prompt_run_service.py` imports `PromptRun` ORM model and validates tenant/business/message scope.
   - Effect: requires foundation model baseline and consistent tenant-scoped entities.

4. **Trace payload coupling to prompt/gateway schemas**
   - tracing recorder uses assembled prompt serialization and gateway token/latency fields.
   - Effect: runtime observability depends on prompt builder + gateway result contracts staying stable.

### Hidden env/runtime assumptions
1. **Langfuse activation semantics**
   - `langfuse_tracing_active()` requires both keys, and then either explicit `LANGFUSE_TRACING_ENABLED=true` or non-production env class.
2. **Env prefix requirement**
   - all settings resolve via `ALPSTEIN_AI_` prefix in `core/config.py`.
3. **Tracing disabled does not remove import dependency**
   - no-op tracing path exists at runtime, but module import still requires `langfuse` package.
4. **Prompt redaction assumes string patterns only**
   - prompt-run secret redaction is regex-based; metadata/object structures are recursively sanitized only for string fields.

### No-go combinations
1. **No-go OBS-A:** bundle tracing + webhook ingress in one commit (`langfuse` failures become hard to localize).
2. **No-go OBS-B:** import `app.main` before observability modules are import-safe and tracked.
3. **No-go OBS-C:** combine prompt-run persistence with unrelated API/bootstrap ingress files.
4. **No-go OBS-D:** treat CIP-C metadata constants as completed tracing wiring (schema exists, runtime wiring still marked prep-only).

### Safest first observability slice
Stage only:
- `backend/app/services/prompt_run_service.py`

This is the smallest observability runtime slice that improves reproducibility without adding external tracing package risk.

### Blockers before webhook tracing becomes safe
Webhook tracing path is not safe until all hold:
1. `langfuse_tracing_service.py` is tracked and import-safe.
2. `langfuse` package is installed in runtime environment.
3. orchestration stack (`AiReplyOrchestrationService`) is tracked and import-safe with prompt builder + gateway dependencies.
4. webhook service stack is tracked (`webhook_message_service.py`) and can execute orchestration path.
5. (for active traces, not just import) Langfuse keys/host env are configured per `ALPSTEIN_AI_LANGFUSE_*`.

### Blockers before `app.main` import becomes safe
`app.main` remains blocked until:
1. `api/routes/webhook.py` import-safe (module-level `WebhookMessageService()` construction succeeds),
2. webhook service dependencies are complete (including seed constant),
3. orchestration dependencies complete (including both observability modules),
4. tracing package/runtime deps installed (`langfuse`, `httpx`, SQLAlchemy async stack),
5. webhook route + webhook service + observability prerequisites are tracked in rollback-safe sequence.

### CIP-C observability readiness
- `backend/app/schemas/langfuse_intent_trace.py` defines metadata keys and explicitly marks wiring as prep-only.
- Current state: **ready for schema-level CIP-C observability constants**, **not yet wired into active Langfuse metadata emission**.

---
## Final-ingress-readiness review (alpstein-reviewer) — A4.2-FINAL-GATE

### Review summary
**Pass with notes (final gate currently NO-GO for ingress import).**  
The target ingress/runtime files remain untracked (`webhook_message_service.py`, `webhook.py`, `main.py`, `langfuse_tracing_service.py`, `seed/dev_ai_configuration.py`) and are still blocked by prerequisite ordering and environment/package assumptions. Runtime ingress should not be imported as a bundle yet.

### Remaining blockers
1. **Tracked-state blocker**
   - Final-gate target files are still untracked in git baseline:
     - `backend/app/services/webhook_message_service.py`
     - `backend/app/api/routes/webhook.py`
     - `backend/app/main.py`
     - `backend/app/services/langfuse_tracing_service.py`
     - `backend/app/seed/dev_ai_configuration.py`

2. **Prerequisite-service blocker**
   - Gateway/config/knowledge/prompt-run/tracing prerequisite slices are not yet fully imported as reproducible sequence.

3. **Tracing runtime blocker**
   - `langfuse_tracing_service.py` has import-time dependency on `langfuse`; clean clone without dependencies will fail module import.

4. **Seed coupling blocker**
   - `webhook_message_service.py` imports seed constant from `seed/dev_ai_configuration.py`; missing seed blocks webhook service import.

5. **Ingress startup side-effect blocker**
   - `webhook.py` constructs `WebhookMessageService()` at module import time; this expands to full transitive orchestration stack at startup.

### Exact remaining safe import order
1. **Observability prerequisite completion**
   - `backend/app/services/prompt_run_service.py`
   - `backend/app/services/langfuse_tracing_service.py`
2. **Seed prerequisite**
   - `backend/app/seed/dev_ai_configuration.py`
3. **Webhook service ingress (late)**
   - `backend/app/services/webhook_message_service.py`
4. **Webhook route ingress activation**
   - `backend/app/api/routes/webhook.py`
5. **App bootstrap entrypoint last**
   - `backend/app/main.py`

### Safest next runtime slice
Stage next:
- `backend/app/services/prompt_run_service.py`

Reason: smallest remaining observability/runtime prerequisite with no external tracing package import at module load.

### Exact conditions before `webhook.py` becomes safe
`backend/app/api/routes/webhook.py` is safe only when all hold:
1. `backend/app/services/webhook_message_service.py` is tracked and import-safe.
2. Seed dependency is tracked/import-safe:
   - `backend/app/seed/dev_ai_configuration.py`.
3. Orchestration prerequisites are tracked/import-safe (prompt builder, gateway, config/knowledge loaders, prompt run, tracing).
4. Environment dependencies are installed in clean clone/runtime (`langfuse`, `httpx`, SQLAlchemy async stack).
5. Module-level `WebhookMessageService()` construction succeeds without import errors.

### Exact conditions before `main.py` becomes safe
`backend/app/main.py` is safe only when all hold:
1. `backend/app/api/routes/webhook.py` is safe to import under the conditions above.
2. `backend/app/api/routes/health.py` and auth/session dependencies remain import-safe.
3. Webhook route startup side effects (service construction) do not fail.
4. Runtime ingress stack has been imported in rollback-safe order (service -> route -> main), not as a sweep.

### GO / NO-GO for runtime ingress import phase
- **Current decision:** **NO-GO**
- **Why:** remaining tracked-state and dependency blockers still present for final ingress target set.
- **GO only after:** prerequisite slices are imported in order, env/package assumptions validated for clean clone, and webhook service/route/main are introduced as isolated late slices.

---
## Langfuse-seed review (alpstein-reviewer) — A4.2-LS1

### Review summary
**Pass with notes (these are the last two high-risk prerequisites before ingress).**  
`backend/app/services/langfuse_tracing_service.py` and `backend/app/seed/dev_ai_configuration.py` are the remaining prerequisite blockers that still prevent safe webhook ingress import. They should be imported as separate late slices due to distinct risk profiles: tracing has package/env startup risk, while seed has webhook constant-coupling and broad model import surface.

### Safest remaining prerequisite order
1. **Tracing prerequisite first**
   - `backend/app/services/langfuse_tracing_service.py`
2. **Seed prerequisite second**
   - `backend/app/seed/dev_ai_configuration.py`
3. **Only then ingress**
   - `backend/app/services/webhook_message_service.py`
   - `backend/app/api/routes/webhook.py`
   - `backend/app/main.py`

### Rollback-safe slices
#### LS-A — Tracing slice
- `backend/app/services/langfuse_tracing_service.py`

#### LS-B — Seed slice
- `backend/app/seed/dev_ai_configuration.py`

#### LS-C — Ingress activation slices (after LS-A + LS-B)
- service ingress: `backend/app/services/webhook_message_service.py`
- route ingress: `backend/app/api/routes/webhook.py`
- app bootstrap: `backend/app/main.py`

### Hidden startup/runtime risks
1. **Tracing import-time dependency**
   - `langfuse_tracing_service.py` imports `langfuse` at module load.
   - Risk: clean clone import failure if dependency is absent, even when tracing is disabled.

2. **Tracing lifecycle runtime risk**
   - tracing context manager flushes in `finally`; exceptions are swallowed to no-op recorder.
   - Risk: silent observability degradation in runtime while functional path continues.

3. **Seed import surface risk**
   - `seed/dev_ai_configuration.py` imports settings + multiple ORM models and SQLAlchemy.
   - Risk: larger import graph and environment sensitivity in clean clone baseline.

4. **Seed runtime guard assumption**
   - seed operations are gated to dev/test/local environments.
   - Risk: behavior depends on correct `ALPSTEIN_AI_ENVIRONMENT` resolution in runtime.

5. **Webhook coupling risk**
   - `webhook_message_service.py` requires seed constant (`PROMPT_TEMPLATE_CUSTOMER_REPLY_KEY`) at import.
   - Risk: ingress import fails without seed slice tracked/import-safe.

### No-go combinations
1. **No-go LS-A:** stage tracing + webhook ingress in one commit.
2. **No-go LS-B:** stage seed + webhook ingress in one commit.
3. **No-go LS-C:** stage `webhook.py` before `webhook_message_service.py` import-safety is proven.
4. **No-go LS-D:** stage `main.py` before `webhook.py` import-safety is proven.
5. **No-go LS-E:** treat runtime env flags as substitute for missing package dependency (`langfuse`).

### Exact safest next slice
Stage only:
- `backend/app/services/langfuse_tracing_service.py`

Reason: smallest remaining prerequisite slice; isolates external tracing package/env risk before introducing seed and ingress coupling.

### Exact blockers before `webhook_message_service.py` becomes safe
`backend/app/services/webhook_message_service.py` remains blocked until:
1. `backend/app/services/langfuse_tracing_service.py` is tracked and import-safe.
2. `backend/app/seed/dev_ai_configuration.py` is tracked and import-safe.
3. Environment dependencies for tracing/import graph are available (`langfuse`, `httpx`, SQLAlchemy async stack).
4. Upstream orchestration prerequisites remain import-safe in baseline sequence.

### Exact blockers before `webhook.py` becomes safe
`backend/app/api/routes/webhook.py` remains blocked until:
1. `webhook_message_service.py` is tracked/import-safe under the conditions above.
2. Module-level `WebhookMessageService()` construction succeeds at route import.
3. Seed + tracing prerequisite slices are already tracked/import-safe.

### Exact blockers before `main.py` becomes safe
`backend/app/main.py` remains blocked until:
1. `webhook.py` import is safe.
2. `webhook_message_service.py` chain is safe (including seed + tracing prerequisites).
3. Clean-clone runtime dependency assumptions are satisfied (notably `langfuse` package availability).
4. Ingress import sequence is preserved for rollback clarity (service -> route -> main).

---
## Seed-runtime review (alpstein-reviewer) — A4.2-SEED1

### Review summary
**Pass with notes (seed is a hard ingress prerequisite due to constant import coupling).**  
`backend/app/seed/dev_ai_configuration.py` is not optional for current webhook ingress import safety because `WebhookMessageService` imports `PROMPT_TEMPLATE_CUSTOMER_REPLY_KEY` directly from it at module load. This makes seed/bootstrap tracking a runtime ingress gate, not just a dev helper concern.

### Safest seed import order
1. **Tracing prerequisite first (already designated in LS1)**
   - `backend/app/services/langfuse_tracing_service.py`
2. **Seed prerequisite second**
   - `backend/app/seed/dev_ai_configuration.py`
3. **Only then ingress chain**
   - `backend/app/services/webhook_message_service.py`
   - `backend/app/api/routes/webhook.py`
   - `backend/app/main.py`

### Rollback-safe slices
#### SEED-A — Seed prerequisite slice
- `backend/app/seed/dev_ai_configuration.py`

#### SEED-B — Ingress service slice (after SEED-A)
- `backend/app/services/webhook_message_service.py`

#### SEED-C — Route/bootstrap slices (after SEED-B)
- `backend/app/api/routes/webhook.py`
- `backend/app/main.py`

### Hidden startup/runtime risks
1. **Import-time seed coupling into ingress**
   - `webhook_message_service.py` imports `PROMPT_TEMPLATE_CUSTOMER_REPLY_KEY` from seed module.
   - Risk: ingress service import fails if seed module is missing/untracked.

2. **Broad seed import surface**
   - seed module imports settings, SQLAlchemy session types, and multiple ORM models at module load.
   - Risk: larger transitive import graph for clean-clone startup than a simple constants module.

3. **Environment-gated seed execution semantics**
   - seed function enforces dev/local/test environment at runtime.
   - Risk: environment misconfiguration can break seed execution expectations, even if import succeeds.

4. **Deterministic demo ID assumptions**
   - seed defines fixed UUIDs and demo identifiers.
   - Risk: conflicting existing rows trigger seed conflict errors in non-clean data states.

### No-go combinations
1. **No-go SEED-A:** stage `webhook_message_service.py` before `backend/app/seed/dev_ai_configuration.py`.
2. **No-go SEED-B:** stage seed + webhook route + main in one commit (rollback/bisect clarity loss).
3. **No-go SEED-C:** stage `webhook.py` before verifying webhook service + seed import safety.
4. **No-go SEED-D:** treat seed as optional for current ingress chain while service still imports seed constant directly.

### Exact safest next slice
Stage only:
- `backend/app/seed/dev_ai_configuration.py`

Reason: it removes the direct seed constant blocker on `WebhookMessageService` while keeping ingress activation deferred.

### Blockers before `webhook_message_service.py` becomes safe
`backend/app/services/webhook_message_service.py` remains blocked until:
1. `backend/app/seed/dev_ai_configuration.py` is tracked and import-safe.
2. tracing prerequisite is tracked/import-safe (`backend/app/services/langfuse_tracing_service.py`).
3. required transitive runtime dependencies are available in clean clone environment.
4. prerequisite orchestration/config/gateway services remain import-safe in baseline sequence.

### Blockers before `webhook.py` becomes safe
`backend/app/api/routes/webhook.py` remains blocked until:
1. `webhook_message_service.py` is tracked/import-safe under the above conditions.
2. module-level `WebhookMessageService()` construction succeeds at route import time.
3. seed + tracing prerequisites are already tracked/import-safe.

### Blockers before `main.py` becomes safe
`backend/app/main.py` remains blocked until:
1. `webhook.py` import is safe.
2. ingress service chain is safe (including seed constant coupling resolution).
3. clean-clone dependency assumptions hold for all transitive imports.
4. rollback-safe sequence is preserved (seed/tracing prerequisites -> webhook service -> webhook route -> main).

---
## Final-route-runtime review (alpstein-reviewer) — A4.2-ROUTE-GATE

### Review summary
**Pass with notes (GO for route slice, NO-GO for `main.py` bundle).**  
Current tracked state includes the deep ingress prerequisites (`webhook_message_service.py`, orchestration/gateway/prompt-run/tracing, seed), while `webhook.py` and `main.py` remain untracked. This is the expected late-stage posture: import the route first as an isolated slice, then `main.py` as a separate final entrypoint slice.

### Safest remaining import order
1. `backend/app/api/routes/webhook.py`
2. `backend/app/main.py`

### Rollback-safe slices
#### RG-A — Route ingress slice (safest next)
- `backend/app/api/routes/webhook.py`

#### RG-B — App entrypoint slice (last)
- `backend/app/main.py`

### Hidden startup/runtime risks
1. **Route import-time side effect**
   - `webhook.py` instantiates `WebhookMessageService()` at module load.
   - Risk: any latent dependency/env drift now appears during import, not first request.

2. **DB session/engine import side effect**
   - route depends on `get_db_session`; DB engine is created at module import in db session module.
   - Risk: clean-clone with broken SQLAlchemy/asyncpg deps will fail startup path.

3. **Token-based ingress assumption**
   - webhook route always enforces `require_webhook_token`.
   - Risk: runtime acceptance depends on `ALPSTEIN_AI_N8N_BACKEND_API_TOKEN` being configured.

4. **Exception handling envelope split**
   - route handles `BusinessNotFoundError` and `TenantContextError` with explicit rollback and structured response.
   - Risk: unexpected exceptions rely on global handling and may produce different response shape.

5. **Main import amplifies route side effects**
   - `main.py` imports `webhook_router`, so all route import risks become app startup risks.

### No-go combinations
1. **No-go RG-A:** stage `webhook.py` and `main.py` together in one final sweep.
2. **No-go RG-B:** stage `main.py` before `webhook.py`.
3. **No-go RG-C:** include unrelated service/refactor files with route/main final slices.
4. **No-go RG-D:** assume startup-safe status without verifying clean-clone dependency/install assumptions.

### Exact safest next slice
Stage only:
- `backend/app/api/routes/webhook.py`

### Blockers before `webhook.py` becomes safe
Minimal blockers remain:
1. **Tracked-state blocker only** — file is currently untracked; prerequisites are already tracked.
2. **Environment readiness check** — runtime package stack must be present (`fastapi`, SQLAlchemy async stack, `langfuse`, `httpx`).
3. **Webhook service import construction** — `WebhookMessageService()` must instantiate successfully at module load.

### Blockers before `main.py` becomes safe
`main.py` remains blocked until:
1. `backend/app/api/routes/webhook.py` is tracked/import-safe first.
2. route import-time construction path is known-stable in clean clone/runtime.
3. route and main are kept as separate rollback-safe slices (route before main).

### GO / NO-GO for final runtime entrypoint import
- **For `webhook.py` (RG-A):** **GO**
- **For `main.py` before route slice lands:** **NO-GO**
- **For `main.py` after route slice is in and import-safe:** **GO**

---
## Main-runtime-readiness review (alpstein-reviewer) — A4.2-MAIN-GATE

### Review summary
**Pass with notes (GO for isolated `main.py` slice).**  
Given current tracked state (route/service/orchestration/gateway/prompt-run/tracing/seed/core bootstrap present), the remaining entrypoint file `backend/app/main.py` is now the final untracked runtime bootstrap artifact and is safe to import as a standalone final slice.

### Remaining startup blockers
1. **Tracked-state only**
   - `backend/app/main.py` is still untracked.
2. **Environment dependency readiness (operational, not source blocker)**
   - clean-clone startup still assumes dependencies from `backend/requirements.txt` are installed (`fastapi`, `sqlalchemy`, `asyncpg`, `httpx`, `langfuse`).

No additional code-level import blockers were identified for `main.py` beyond these.

### Safest remaining import order
1. `backend/app/main.py` (final runtime entrypoint slice)

### Hidden startup/runtime risks
1. **Entrypoint imports webhook route at startup**
   - `main.py` imports `app.api.routes.webhook`, which performs module-level `WebhookMessageService()` construction.
   - Risk: any latent transitive import/env break now surfaces at app import/startup.

2. **DB engine construction side effect remains import-time**
   - route dependency graph includes db session module where async engine is created at import.
   - Risk: dependency/runtime misconfiguration appears during startup rather than first request.

3. **Langfuse package dependency remains startup-sensitive**
   - tracing module import requires `langfuse` package availability even when tracing is effectively disabled by env.

4. **Webhook auth configuration affects runtime behavior**
   - startup succeeds without token, but ingress requests fail closed when `ALPSTEIN_AI_N8N_BACKEND_API_TOKEN` is unset.

### No-go combinations
1. **No-go M-A:** bundle `main.py` with unrelated files in this final gate slice.
2. **No-go M-B:** combine final runtime entrypoint import with docs/spec/n8n broad changes.
3. **No-go M-C:** assume container/runtime portability without dependency install + env validation.

### Exact safest next slice
Stage only:
- `backend/app/main.py`

### Exact blockers before `main.py` becomes safe
For source-level reproducibility baseline: **none remaining after isolated staging target**.  
Operational readiness checks still required post-import:
1. dependency install from `backend/requirements.txt`,
2. env configuration for webhook token and optional Langfuse keys,
3. runtime smoke import in clean clone/container context.

### GO / NO-GO for `main.py` import
- **Decision:** **GO**
- **Condition:** import as isolated final slice only.

### Readiness for Docker portability phase
- **Readiness status:** **Ready with notes**
- Core startup graph is now baseline-complete once `main.py` is tracked.
- Docker portability phase should focus on environment bootstrapping (dependency install, env wiring, startup health checks), not further runtime architecture changes.

---
## Phase C Step C3 — Rollback discipline audit (alpstein-reviewer)

**Phase:** C3 — Rollback discipline  
**Context:** PHASE A/B complete; C1 export parity + C2 G-EXP-2 scrub gate complete; portable compose track B2.0–B2.9 complete.  
**Primary contract:** [`docs/deployment/deployment-contract.md`](../deployment/deployment-contract.md) §11 RDU/RBU  
**n8n policy:** [`docs/ops/n8n-runtime-export-parity.md`](../ops/n8n-runtime-export-parity.md)

### Review summary
**Pass with notes (rollback is operationally understood only when executed as atomic RBU, not as “git tag only”).**  
Rollback anchors exist and portable startup is deterministic, but **production-like recovery cannot be guaranteed** without rehearsed downgrade paths, volume snapshots, n8n re-import discipline, and post-rollback verification gates. Partial rollback is explicitly invalid.

---

## 1. Rollback discipline audit

### 1.1 What “rollback” means in this stack

| Term | Definition |
|------|------------|
| **RDU** (reproducible deployment unit) | Identified release: git commit/tag + alembic head + canonical n8n export(s) + env template version + compose hash |
| **RBU** (rollback unit) | Atomic recovery bundle: git tag/commit + target alembic revision + n8n export version + env re-apply + optional volume snapshot IDs |
| **Code rollback** | `git checkout <tag>` + rebuild images + redeploy compose |
| **Data rollback** | Postgres volume restore and/or rehearsed `alembic downgrade` — **not** implied by code rollback alone |
| **n8n rollback** | Deactivate → re-import prior export → re-bind credentials → restart → activate one workflow → update registry |

### 1.2 Git tag rollback integrity

**Known anchors (verified in repo):**

| Tag | Typical use |
|-----|-------------|
| `baseline-pre-b2.5` | Pre migrate-then-serve entrypoint |
| `baseline-b2.5-entrypoint` | Entrypoint contract only |
| `baseline-b2.6-compose` | Postgres + backend compose (no n8n service) |
| `baseline-b2.7-n8n-network` | + portable n8n on `alpstein_internal` |
| `baseline-b2.8-bootstrap` | + compose profile `bootstrap` |
| `baseline-b2.9-clean-clone-gate` | Gate evidence + portable path acceptance |
| `baseline-c2-export-scrub-gate` | **Planned** — tag after C2 commit accepted (not yet in `git tag -l` at audit time) |

**Integrity rules:**

1. Tag must point to a **single commit** that passed the gates valid for that era (B2.9 for portable stack; C2 for export scrub).
2. Tag alone does **not** roll back volumes, n8n SQLite, or secrets.
3. After `git checkout <tag>`, **rebuild** `alpstein-ai-backend:local` — do not assume old image layers match tag without rebuild.
4. Record tag + `alembic current` + `docker compose config` hash in release notes.

**Risks:**

| Risk | Severity | Note |
|------|----------|------|
| Tag without gate transcript | Important | Tag is pointer only; operator must re-run verification checklist |
| Checking out older tag on live DB at newer revision | **Critical** | Backend may fail startup or behave inconsistently until downgrade or volume restore |
| Missing `baseline-c2-export-scrub-gate` | Suggestion | Create after C2 merge for export-governance rollback point |

### 1.3 Docker compose rollback reproducibility

**Portable stack** (`docker-compose.yml`, project `-p alpstein-ai`):

| Component | Rollback mechanism | Reversible? |
|-----------|-------------------|-------------|
| Compose file | `git checkout` tag | Yes (with rebuild) |
| `alpstein_postgres_data` | Persists across `down` | **Data not reverted** by compose rollback |
| `alpstein_n8n_data` | Persists; holds credentials + workflow IDs | **State not reverted** by git alone |
| Backend image | Rebuild from checked-out tree | Yes |
| n8n image pin | `docker.n8n.io/n8nio/n8n:1.95.3` in compose | Pin change requires explicit RBU |
| Networks/volumes names | Fixed names (`alpstein_internal`, etc.) | Stable across tags — good for ops, bad for side-by-side old/new |

**Rollback procedure (compose):**

```bash
# 1) Stop (volumes persist)
docker-compose -p alpstein-ai down

# 2) Code rollback
git checkout <RBU-tag>
docker-compose -p alpstein-ai build backend

# 3) Redeploy
docker-compose -p alpstein-ai up -d postgres backend n8n

# 4) Optional fresh data (DESTRUCTIVE)
docker-compose -p alpstein-ai down -v   # only after snapshot/backup
```

**Not reversible without volume backup:** rows in `messages`, `leads`, `prompt_runs`, n8n execution history, Telegram webhook registration on wrong active workflow.

### 1.4 Backend/runtime compatibility risks

| Risk | After rollback to older tag |
|------|----------------------------|
| Newer DB schema than code expects | Startup/migration errors or silent query failures |
| Older code than DB schema | Missing tables/columns at runtime |
| Entrypoint always runs `alembic upgrade head` | Rolls **forward** on start to migrations in checked-out tree — not backward |
| Langfuse package required at import | Clean clone must install `langfuse` even if tracing disabled |
| Bootstrap profile re-run | **Adds** demo data; does not undo prior bootstrap |

**Critical truth:** Rolling back **code** to tag T while keeping Postgres volume at revision **0007** only works if tag T’s code is compatible with **0007** schema. Rolling back to pre-`0007` code requires **`alembic downgrade`** to `0006` or volume restore — not automatic.

### 1.5 Migration rollback limitations

**Chain:** `0001` … `0007` (all revisions include `downgrade()` implementations).

| Scenario | Safe? | Notes |
|----------|-------|-------|
| `alembic downgrade -1` on empty test DB | Rehearsal only | Validates downgrade scripts exist |
| Downgrade on DB with production-like data | **Risky** | Dropping `leads` / `prompt_runs` **deletes data** |
| Downgrade after columns referenced by app | **Unsafe** without coordinated code rollback |
| Renumbering migration files | **Forbidden** on DB that already applied old IDs |
| Forward-only deploy policy | **Recommended default** | Document target revision; snapshot before upgrade |

**Cannot safely rollback after migrations if:**

- Application code at new head wrote to new tables (`leads`, `prompt_runs`, AI config tables).
- Downgrade would drop those tables and lose rows.
- No rehearsed downgrade path or snapshot taken before upgrade.

**Manual recovery:** restore `alpstein_postgres_data` from snapshot taken at RDU tag time.

### 1.6 n8n export rollback consistency

**Atomic RBU-n8n** (from parity doc):

```text
git tag/commit
+ canonical export filename + versionId
+ runtime-registry.md workflow ID (pre-rollback)
+ optional backups/*.json
+ credential re-bind (names only)
```

| Action | Reversible via git? | Manual steps |
|--------|---------------------|--------------|
| Topology rollback | Yes (import previous export) | Deactivate → import → bind → restart → activate |
| Activation-only rollback | Partial | Use registry “known-good” ID |
| Execution history | **No** | n8n SQLite not in git |
| Telegram duplicate active workflows | **No** | Operator must deactivate extras |
| `BACKEND_BASE_URL` drift | **No** | Fix env + restart n8n |

**C2 contribution:** `scripts/n8n/export-scrub.sh` (G-EXP-2) blocks bad exports before commit; rollback of **workflow logic** still requires runtime import, not script alone.

### 1.7 Runtime registry rollback integrity

[`n8n/workflows/runtime-registry.md`](../../n8n/workflows/runtime-registry.md) maps **git export → host workflow UUID**.

| Failure mode | Effect |
|--------------|--------|
| Registry not updated after import | Rollback targets wrong workflow ID |
| Stale Contabo IDs on portable host | Wrong deactivate/activate |
| Multiple rows for same bot | Telegram 403 / duplicate processing |

**Rollback rule:** restore registry row from git history at RBU tag, then match runtime via n8n UI before activate.

### 1.8 Bootstrap compatibility risks

| Item | Rollback behavior |
|------|-------------------|
| `docker-compose --profile bootstrap` | **Idempotent-ish** seed; re-run may conflict if demo rows exist |
| SQL scripts in bootstrap | Mutate data; **not undone** by code rollback |
| `ALPSTEIN_AI_ENVIRONMENT=production` | Bootstrap **refused** (by design) |
| B2.8 rollback per docs | **Volume restore** — not compose down alone |

### 1.9 Environment drift risks

| Drift source | Rollback impact |
|--------------|-----------------|
| `.env` not in git | Must re-apply secrets from vault; templates from tag |
| `N8N_ENCRYPTION_KEY` change | n8n volume unreadable — **requires volume backup** |
| `OPENAI_API_KEY` / Langfuse keys | AI/tracing behavior changes; not code rollback |
| Legacy host `172.20.0.1:8010` vs portable `http://backend:8000` | Wrong backend if mixed on one n8n instance |
| Operator UI edits on Contabo | Silent drift until export + registry update |

### 1.10 Rollback verification procedures (summary)

See **§4 Recovery gates** and **§4 Rollback verification checklist** below.

---

## 2. Operational rollback policy

### 2.1 Principles

1. **Atomic RBU only** — never roll back “backend only” while leaving n8n/DB at newer effective state for production verification.
2. **Snapshot before upgrade** — Postgres volume (and n8n volume before credential/Telegram changes) before non-disposable environment changes.
3. **Forward migrations default** — treat `alembic downgrade` as exception requiring rehearsal ticket.
4. **n8n activation is operator action** — repo exports stay `active: false`; rollback activation uses registry IDs.
5. **Secrets never rolled back via git** — re-apply from secure store aligned to env templates at tag.
6. **Record evidence** — gate transcript or checklist signed per RBU.

### 2.2 Layer policy matrix

| Layer | Default rollback | Data handling | Verification minimum |
|-------|------------------|---------------|----------------------|
| Backend code/image | Git tag + rebuild | Keep volume | Liveness + readiness + one webhook |
| Alembic | Forward at startup to tag’s head; downgrade only if rehearsed | Snapshot before downgrade | `alembic current` matches expectation |
| Postgres data | Volume restore | **Primary** for production | Migrations + seed if dev |
| n8n workflows | Re-import export + registry | SQLite volume optional restore | G-EXP-2 on export + G-EXP-6 + smoke |
| Secrets | Rotate/re-apply | N/A | Health + auth failures expected if wrong |
| Bootstrap | Do not auto-run on rollback | Volume restore if demo reset needed | Business rows query |

### 2.3 What rollback does **not** fix (contractual)

From deployment contract §11.3 + parity doc:

- Polluted `messages` history / duplicate processing artifacts
- Lost `N8N_ENCRYPTION_KEY` without volume backup
- Telegram webhook conflicts from multiple active workflows
- n8n execution history
- Owner notification delivery already sent (external side effect)

---

## 3. Rollback-safe release procedure

### 3.1 Before release (RDU creation)

1. Identify git commit; create **annotated tag** `baseline-<phase>-<name>`.
2. Record `alembic heads` (expect `0007`).
3. Run `scripts/n8n/export-scrub.sh` — commit only on pass (G-EXP-2).
4. Update `runtime-registry.md` if workflows activated on target host.
5. Snapshot volumes if environment is not disposable:
   - `docker run --rm -v alpstein_postgres_data:... postgres:15 pg_dump ...` or volume-level backup
   - n8n volume before Telegram/credential changes
6. Archive RDU record: tag + compose hash + export `versionId` + gate transcript pointer.

### 3.2 Rollback execution (RBU)

```text
1. Declare incident RBU id (tag + volumes + exports)
2. docker-compose -p alpstein-ai down
3. git checkout <RBU-tag>
4. Restore postgres volume OR rehearse alembic downgrade (only if planned)
5. docker-compose build backend && docker-compose up -d postgres backend
6. Wait: migrations + readiness healthy
7. n8n: deactivate current workflows (registry + UI)
8. import previous canonical export(s); re-bind credentials
9. docker-compose up -d n8n (or restart)
10. Activate ONE workflow per bot; update registry
11. Run recovery gates R1–R7 (§5)
12. Document outcome; new tag if stack is healthy baseline
```

### 3.3 After rollback

- Do **not** delete RBU tag.
- File short incident note: what was rolled back, what was **not** rolled back (data/history).
- If downgrade was used: document data loss scope.

---

## 4. Rollback verification checklist

Operator checklist after RBU deploy (tick all):

| ID | Check | Pass criteria |
|----|--------|---------------|
| V1 | Git state | `git describe --tags` = intended RBU tag |
| V2 | Images rebuilt | `docker-compose build backend` from tag tree |
| V3 | Postgres healthy | `pg_isready` via compose healthcheck |
| V4 | Alembic revision | `alembic current` matches RBU target (usually tag head) |
| V5 | Liveness | `GET /api/v1/health` → 200 |
| V6 | Readiness | `GET /api/v1/health/ready` → 200 |
| V7 | Webhook smoke | `POST /api/v1/webhook/message` → `success: true` (token + seeded business) |
| V8 | n8n → backend | From n8n container: readiness 200 at `BACKEND_BASE_URL` |
| V9 | G-EXP-2 | `scripts/n8n/export-scrub.sh` exit 0 on exports at tag |
| V10 | G-EXP-3 | `runtime-registry.md` matches live workflow IDs |
| V11 | G-EXP-4 | Exactly one active Telegram workflow per bot (if applicable) |
| V12 | No duplicate Telegram 403 | Webhook set once per bot |

**B2.9 gate mapping:** V3–V6 ≈ G2–G4; V7 ≈ G5 (manual); V8 ≈ G6.

---

## 5. Recovery gates definition

Formal gates (use in incident/runbooks):

| Gate | Name | Blocks release/close | Failure means |
|------|------|----------------------|---------------|
| **R1** | Tag integrity | RBU start | Wrong commit/tag checked out |
| **R2** | Schema compatibility | Backend start | Migration/DB mismatch |
| **R3** | Core health | Traffic restore | Stack not actually up |
| **R4** | Readiness | n8n dependency | DB pool / deps broken |
| **R5** | Webhook path | Customer ingress | Business/AI path broken |
| **R6** | n8n parity | Automation confidence | Wrong workflow active or export drift |
| **R7** | Registry truth | Repeat rollback | Wrong UUID documented |

**Gate failure handling:**

| Gate failed | Likely action |
|-------------|---------------|
| R1–R2 | Stop; fix git/DB strategy (restore snapshot or rehearse downgrade) |
| R3–R4 | Fix compose/env/DB connectivity |
| R5 | Seed/bootstrap/token/AI config |
| R6–R7 | n8n operator procedure; do not declare RBU complete |

---

## 6. Database rollback limitations document

### 6.1 Reversible (with rehearsal or empty DB)

- `alembic upgrade head` / `downgrade` scripts exist for all `0001`–`0007`.
- Empty volume + tag checkout + `up` + bootstrap profile → full dev stack replay (B2.9 path).

### 6.2 NOT reversible without data loss

- Downgrade from `0007` → `0006` on DB with leads rows → **drops `leads` table and data**.
- Downgrade across `0006` (AI config, `prompt_runs`) → loses audit and config tables.
- Any rollback removing `messages` uniqueness index era → idempotency behavior change.

### 6.3 Requires manual recovery

- Partial business seed / SQL bootstrap scripts applied manually.
- Wrong tenant/business rows after bad seed.
- n8n credential bindings (names in export, secrets in vault).

### 6.4 Requires backup restore

- Production Postgres at revision N when code needs N−k.
- Corrupt or lost `alpstein_postgres_data`.
- n8n volume when `N8N_ENCRYPTION_KEY` lost or volume wiped.
- Point-in-time recovery for legal/audit retention.

### 6.5 Cannot safely rollback after migrations (operational rule)

**Rule:** Once revision **0007** is applied in an environment with live traffic:

- Do **not** roll back code to `baseline-b2.6-compose` without either:
  - **(A)** volume restore to pre-0007 snapshot, or
  - **(B)** rehearsed downgrade to `0006` accepting **loss** of `leads` + related data, or
  - **(C)** new disposable environment (clean volume) for verification only.

**Startup coupling:** `docker-entrypoint.sh` always runs `alembic upgrade head` for the **checked-out** tree — it will not downgrade automatically on code rollback.

---

## 7. Runtime rollback matrix

| Artifact | Rollback method | Auto on `git checkout`? | Data loss risk | Verification |
|----------|-----------------|-------------------------|----------------|--------------|
| `backend/app/**` | Git tag | N/A (source) | None | Tests / smoke |
| Backend Docker image | Rebuild | No | None | Health |
| `docker-compose.yml` | Git tag | No | None | `compose config` |
| Postgres volume | Snapshot restore / `down -v` | No | **High** if `-v` | Migrations |
| Alembic revision | `upgrade` on start; `downgrade` manual | Partial | Downgrade: high | `alembic current` |
| Bootstrap seed | Re-run profile or restore volume | No | Duplicate/conflict | SQL query |
| n8n export JSON | Git + re-import | No | None | G-EXP-2 |
| n8n runtime IDs | Registry-guided import | No | None | G-EXP-3 |
| n8n SQLite volume | Snapshot restore | No | Restore or lose creds | UI + smoke |
| `.env` secrets | Manual re-apply | No | N/A | Auth + AI |
| Telegram webhooks | Deactivate/activate | No | None | HTTP 200 |
| Langfuse traces | Not in scope | No | N/A | Optional |

---

## 8. Failure / recovery scenarios

| # | Scenario | Symptoms | Recovery path | Rollback guaranteed? |
|---|----------|----------|---------------|----------------------|
| F1 | Code rolled back; DB still at 0007 | Missing columns or logic errors | Restore DB snapshot or use tag matching 0007 | **No** until DB aligned |
| F2 | `alembic downgrade` on live DB | Data loss in dropped tables | Restore from snapshot; accept loss | **No** |
| F3 | n8n wrong workflow active | Duplicate replies / 403 Telegram | Deactivate all; activate one per registry | Manual |
| F4 | Lost `N8N_ENCRYPTION_KEY` | n8n cannot decrypt creds | Restore `alpstein_n8n_data` backup | **Only with backup** |
| F5 | Export scrub failure at tag | Secrets in git export | Fix export; re-run G-EXP-2; new commit | Yes before deploy |
| F6 | Partial compose rollback (backend only) | n8n points at wrong URL/version | Full RBU including n8n + registry | **No** |
| F7 | `down -v` without backup | Empty DB | `alembic upgrade` + bootstrap profile | Fresh env only |
| F8 | Migration fails on start | Backend exits; no uvicorn | Fix DB URL/password; fix revision drift | Fix-forward |
| F9 | Readiness fails after rollback | n8n won't start | Fix postgres/pool/deps | Fix-forward |
| F10 | Registry stale | Rollback activate wrong ID | Git history of `runtime-registry.md` | Manual |

---

## 9. Recommended rollback tagging discipline

### 9.1 Tag naming

```text
baseline-<track>-<milestone>[-qualifier]
```

Examples: `baseline-b2.9-clean-clone-gate`, `baseline-c2-export-scrub-gate`, `baseline-c3-rollback-discipline`.

### 9.2 When to tag (mandatory)

| Event | Tag? |
|-------|------|
| B2.x portable milestone | Yes (existing) |
| C2 export scrub gate accepted | **Yes** — `baseline-c2-export-scrub-gate` |
| Before alembic revision bump affecting prod | **Yes** + volume snapshot |
| Before n8n Telegram production activate | Yes + registry update |
| C3 policy accepted | Suggested: `baseline-c3-rollback-discipline` (docs-only) |

### 9.3 Annotated tag message must include

- RDU/RBU id
- Alembic head
- Canonical n8n export `versionId`(s)
- Gate transcript path (e.g. clean-clone, G-EXP-2 log)
- Known limitations (e.g. “G5 not run”)

### 9.4 Do not tag

- Mid-incident dirty tree
- Local `.env` experiments
- Contabo-only hotfix without export in git

---

## 10. Suggested implementation tasks (if needed)

| Task ID | Scope | Priority | Notes |
|---------|--------|----------|-------|
| **T-C3.1** | Create annotated tag `baseline-c2-export-scrub-gate` | High | Closes planned anchor gap |
| **T-C3.2** | Add `docs/ops/rollback-runbook.md` (extract from this audit) | Medium | Operator-facing; link contract §11 |
| **T-C3.3** | Rehearse `alembic downgrade` 0007→0006 on disposable volume | Medium | Evidence whether downgrade is viable |
| **T-C3.4** | Document volume snapshot commands in rollback runbook | High | Postgres + n8n |
| **T-C3.5** | Post-rollback gate script (health + readiness + optional webhook) | Low | Automate V5–V7 |
| **T-C3.6** | Portable G5 extension (C6): import + webhook in gate transcript | Medium | Closes B2.9 gap |
| **T-C3.7** | Contabo duplicate Telegram workflow cleanup | Ops | Registry hygiene |

**Out of scope (per C3 charter):** Kubernetes, new infra, observability stack, workflow logic changes, architecture redesign.

---

## 11. Blockers before ingress files (post-C3 state)

For reference after prerequisites complete:

### 11.1 Before `webhook_message_service.py` / full ingress

- RBU prerequisites: tag at or after `baseline-b2.9-clean-clone-gate` + C2 export governance tag when workflows change.
- Postgres at expected revision; bootstrap only on dev.

### 11.2 Before `webhook.py`

- `webhook_message_service.py` import-safe at target tag.
- Module-level `WebhookMessageService()` succeeds.

### 11.3 Before `main.py`

- `webhook.py` import-safe.
- Recovery gates R3–R5 pass on target environment.

---

## 12. GO / NO-GO — rollback discipline phase

| Question | Decision |
|----------|----------|
| Are rollback anchors sufficient for portable stack? | **GO** (B2.5–B2.9 + contract) |
| Is `git tag only` sufficient for production recovery? | **NO-GO** |
| Is atomic RBU policy defined? | **GO** (this audit + contract §11) |
| Is C2 export scrub part of rollback discipline? | **GO** (G-EXP-2) |
| Can downgrade be assumed safe without rehearsal? | **NO-GO** |
| Ready for Docker portability **operations** (not new architecture)? | **GO with notes** — env/snapshot/runbook discipline still operator-dependent |

**Operational truth:** Move from “we have tags” to “rollback behavior is understood and reproducible” requires **using** RBU procedure + verification checklist on a disposable environment before claiming production rollback guarantee.

---

## Specs consulted

- [`docs/deployment/deployment-contract.md`](../deployment/deployment-contract.md)
- [`docs/ops/n8n-runtime-export-parity.md`](../ops/n8n-runtime-export-parity.md)
- [`docs/audits/clean-clone-gate-2026-05-27.md`](clean-clone-gate-2026-05-27.md)
- [`docs/deployment/bootstrap-profile.md`](../deployment/bootstrap-profile.md)
- [`docs/ops/database-recovery.md`](../ops/database-recovery.md)
- [`n8n/workflows/runtime-registry.md`](../../n8n/workflows/runtime-registry.md)
- [`docker-compose.yml`](../../docker-compose.yml)
- [`backend/docker-entrypoint.sh`](../../backend/docker-entrypoint.sh)
- [`backend/alembic/versions/`](../../backend/alembic/versions/)

## What was not reviewed

- Live execution of rollback on Contabo or production host
- Rehearsed `alembic downgrade` on real data
- Automated rollback script implementation (suggested only)
- HubSpot / legacy `n8n/docker-compose.yml` stack rollback


