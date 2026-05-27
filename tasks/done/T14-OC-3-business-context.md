@alpstein-n8n-integration-engineer

Implement T14-OC-3 Add Business Context node in Telegram customer ingress workflow.

Context:
T14-OC-2 backend implementation is accepted.
Backend now accepts top-level operator_business_context on POST /api/v1/webhook/message.
This field is passed to PromptBuilder as OPERATOR BUSINESS NOTES.
n8n must only provide editable business facts; no OpenAI or prompt assembly in n8n.

Prerequisite:
- Deploy/restart backend with T14-OC-2 before runtime verification.

Scope:
- n8n Telegram customer ingress workflow
- docs/status updates
- no backend code
- no DB changes
- no migrations
- no OpenAI node in n8n
- no T13.6 retries

Workflow change:
Telegram Trigger
→ Normalize Telegram Incoming
→ Add Business Context
→ POST Backend
→ Shape Telegram Customer Reply
→ Telegram Send Message

Owner notify branch stays unchanged and reads from POST Backend only.

Requirements:
1. Add Set/Edit Fields node after Normalize Telegram Incoming:
   Node name: Add Business Context

2. Add top-level field:
   operator_business_context

3. Example MVP context:
   Barbershop demo business.
   Services: haircut, beard trim, appointment requests.
   Opening hours: Monday to Friday, 09:00-18:00.
   Languages: German, English, Russian.
   Tone: friendly, concise, helpful.
   If the customer writes in Russian, answer in Russian.
   Ask for the customer's name only when they clearly want to book an appointment.

4. Ensure POST Backend sends operator_business_context as top-level request field.

5. Do not include:
   - bot tokens
   - chat IDs
   - backend tokens
   - OpenAI keys
   - system prompt / jailbreak instructions
   - raw provider instructions

6. Verify:
   - JSON export valid
   - no secrets in export
   - backend receives operator_business_context
   - Telegram Russian test reply reflects the context
   - owner notify and duplicate behavior remain unchanged

7. Tests:
   Normal Russian message:
   “Привет, вы сегодня работаете?”

   Expected:
   - customer receives Russian reply
   - bot does not say it only speaks German/English
   - response reflects opening hours/business context

   Booking intent:
   “Хочу записаться на стрижку сегодня”

   Expected:
   - bot may ask for name / preferred time
   - response stays in Russian

8. Update docs:
   - docs/ops/n8n-workflow-telegram-customer-ingress.md
   - docs/architecture/operator-business-context-n8n.md
   - docs/project-status/next-steps.md
   - tasks/todo/t14-telegram-customer-ingress.md
   - create tasks/done/T14-OC-3-add-business-context-node.md

Return:
- files changed
- workflow topology
- context text added
- verification results
- whether T14-OC-3 passed
- whether T14.5 regression may start

Important:
Do not move AI logic into n8n.
Do not add OpenAI node.
Do not modify backend.
Do not expose secrets.