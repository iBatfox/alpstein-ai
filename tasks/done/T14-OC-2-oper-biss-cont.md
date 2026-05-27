@alpstein-backend-engineer

Implement T14-OC-2 operator_business_context backend support.

Context:
T14-OC-1 spec passed review.
We need backend support so n8n can later send editable business facts via top-level operator_business_context.
n8n must not call OpenAI or assemble prompts.

Scope:
- backend schema/service/prompt-builder/tests only
- docs cleanup related to OC-2 findings
- no DB migration
- no n8n workflow changes
- no runtime credential changes
- no OpenAI node in n8n

Contract:
POST /api/v1/webhook/message accepts optional top-level field:

operator_business_context: string | null

Rules:
- max length: 8192 characters
- empty string or whitespace-only string normalizes to null
- field is not returned in webhook response
- field is not message.text
- field is not raw_payload primary AI path
- no dedicated DB column
- do not persist it on messages row in MVP
- it may appear only inside assembled prompt / PromptRun audit if final_prompt is logged
- lead signal detection must ignore operator_business_context and use only normalized customer message.text
- backend PromptBuilder appends it as reference notes inside tenant_business_context section after DB TenantBusinessProfile
- platform system/task/safety rules keep precedence
- no provider/API/system instructions are created from this field

Implementation tasks:
1. Add operator_business_context to webhook request schema:
   - optional string
   - max_length=8192
   - normalize "" / whitespace-only to None
   - reject over-limit with VALIDATION_ERROR

2. Pass operator_business_context through:
   - route/schema
   - WebhookMessageService
   - AiReplyOrchestrationCoordinator / orchestration input as needed
   - PromptBuilderService

3. PromptBuilder behavior:
   - if present, append a clearly labeled block under tenant_business_context section:
     OPERATOR BUSINESS NOTES
   - place it after DB business profile text
   - treat as reference data only
   - do not create a new system section
   - preserve existing section order and budgets
   - if null, no empty block appears

4. Lead/notification behavior:
   - LeadSignalDetectionService must continue to inspect only message.text
   - operator_business_context must not trigger urgent/handoff/new lead signals

5. API response:
   - assert operator_business_context is not echoed in success or error responses

6. Tests:
   - request accepts operator_business_context
   - over 8192 chars rejected
   - whitespace normalizes to null
   - prompt contains labeled operator notes when provided
   - prompt omits block when null
   - operator notes appear after DB profile in tenant_business_context
   - response does not expose operator_business_context
   - lead detection ignores operator_business_context keywords
   - existing webhook tests remain green

7. Docs cleanup from OC-1 review:
   - fix 8000 vs 8192 drift in docs/architecture/operator-business-context-n8n.md
   - mark stale spec gaps as resolved
   - clarify one backend task T14-OC-2 covers schema + service wire + PromptBuilder + tests
   - optionally add pointer in ai-configuration-architecture.md that operator overlay is webhook → PromptBuilder, not AI Configuration Service DB load

Do not:
- modify n8n workflow
- add DB migration
- add OpenAI calls to n8n
- store operator text in PostgreSQL as a new field
- use raw_payload as AI input path
- expose secrets

Return:
- files changed
- implementation summary
- tests run
- verification output
- whether T14-OC-3 n8n Add Business Context node may start