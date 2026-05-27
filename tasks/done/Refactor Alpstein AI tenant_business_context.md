@alpstein-database-architect

Refactor Alpstein AI tenant_business_context to reduce prompt noise and hallucination pressure.

Problem:
Current tenant_business_profiles content behaves like a marketing brochure and over-influences the model.

Observed issues in assembled prompt:
- overly specific CRM/platform claims
- long marketing-style explanations
- GPT repeating CRM names aggressively
- hallucination pressure from injected capabilities
- duplicated meaning between tenant_business_context and operator_business_context

Evidence from Langfuse:
tenant_business_context currently injects:
- Bitrix24
- HubSpot
- Salesforce
- long capability lists
- sales-style wording

This causes:
- overconfident answers
- unnecessary platform lists
- verbose Telegram replies
- “sales brochure” tone instead of grounded assistant behavior

Scope:
- data/content cleanup only
- tenant_business_profiles only
- no schema migration
- no backend code changes
- no n8n changes
- no PromptBuilder redesign

Target business:
business_id = 22222222-2222-4222-8222-222222222223
business_external_id = alpstein_ai_demo_001

Goals:
1. Convert tenant_business_context from:
   “marketing brochure”
   into:
   “grounded business identity + capabilities”

2. Reduce hallucination pressure.

3. Separate responsibilities:
   - tenant_business_context = stable business facts/capabilities
   - operator_business_context = runtime communication behavior and office rules

Tasks:
1. Inspect current row in:
   tenant_business_profiles

2. Identify:
   - duplicated information already present in operator_business_context
   - overly specific CRM/platform claims
   - wording likely to trigger hallucinations or long sales responses

3. Replace with a cleaner grounded version.

Desired characteristics:
- concise
- factual
- neutral
- capability-oriented
- no exaggerated marketing language
- no unsupported guarantees
- no hard promises
- no long CRM/platform enumerations unless truly required

Recommended direction:
description:
"Alpstein AI develops AI assistants and communication automation systems for businesses."

services:
- AI assistants
- CRM/workflow integrations
- Telegram communication flows
- workflow automation
- customer communication systems

Avoid:
- long capability paragraphs
- aggressive enterprise wording
- “exactly captures leads”
- “faster than competitors”
- unsupported integrations
- giant CRM name lists

4. Keep:
- multilingual capability
- Telegram support
- workflow automation concept
- CRM integration concept

5. Verify in Langfuse:
- assembled prompt shorter
- less duplication with operator_business_context
- reduced hallucination pressure
- cleaner Telegram responses

6. After update:
recommend whether conversation/messages should be cleared again for clean testing.

Return:
- findings
- exact UPDATE SQL
- before/after summary
- estimated effect on prompt quality
- whether cleanup is accepted

Important:
- do not modify other businesses
- do not touch Telegram credentials
- do not redesign PromptBuilder
- do not remove operator_business_context
- no secrets