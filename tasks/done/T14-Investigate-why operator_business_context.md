@alpstein-backend-engineer

Investigate why operator_business_context does not override existing repetitive German onboarding behavior.

Context:
T14-OC-3 is working technically:
- operator_business_context reaches backend
- PromptBuilder includes OPERATOR BUSINESS NOTES
- Telegram workflow works
- no OpenAI in n8n

But runtime behavior still strongly follows older German onboarding rules:
- “Bitte nennen Sie mir Ihren Namen”
- “Ich spreche nur Deutsch und Englisch”
- repetitive greeting loops
even when operator_business_context explicitly instructs:
- reply in customer language
- Russian supported
- ask for name only when booking intent is clear

Goal:
Find which existing backend prompt/profile layer dominates the response behavior.

Scope:
- backend AI configuration inspection only
- no DB migration
- no workflow changes
- no OpenAI provider changes
- no T13.6
- no n8n redesign

Tasks:
1. Trace the assembled prompt for:
   business_id = demo_barbershop_001
   channel = telegram

2. Identify:
   - TenantBusinessProfile content
   - tenant_ai_profiles
   - PromptBuilder section ordering
   - onboarding/fallback templates
   - language instructions
   - repetitive name collection rules
   - hardcoded assistant rules if any

3. Compare:
   Existing DB/profile instructions
   vs
   operator_business_context

4. Determine why model still answers:
   - German-first
   - repetitive greeting loop
   - “only German/English”

5. Output:
   - exact source file/config/table causing it
   - assembled prompt section order
   - which layer has strongest influence
   - recommended minimal fix

6. Preferred fixes:
   - weaken/remove outdated German-only instructions
   - reduce forced onboarding repetition
   - improve language-following behavior
   - keep architecture intact

7. Avoid:
   - moving prompts into n8n
   - duplicating prompt logic
   - OpenAI nodes in workflow

Return:
- findings
- prompt hierarchy explanation
- exact conflicting instructions
- recommended fix path
- whether this is config-only or requires PromptBuilder adjustment