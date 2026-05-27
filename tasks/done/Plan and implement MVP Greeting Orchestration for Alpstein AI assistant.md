@alpstein-backend-engineer

Plan and implement MVP Greeting Orchestration for Alpstein AI assistant.

Context:
Telegram AI flow works.
Business context separation is being introduced.
Now we need stable first-contact behavior.

Goal:
Assistant should greet only when appropriate, introduce itself as Alpstein AI assistant, and reply in the customer's language.

Supported greeting languages:
- German
- English
- Russian
- French
- Italian
- Spanish
- Ukrainian

Behavior:
1. First message in a new conversation:
   - greet the customer
   - say: “I am your Alpstein AI assistant” in the customer’s language
   - briefly explain that the assistant helps with AI assistants, CRM integrations, automation, and customer communication workflows
   - ask how it can help

2. Follow-up messages:
   - do not repeat the greeting
   - answer directly
   - keep context

3. After long inactivity:
   - optional soft greeting, but do not repeat full introduction every time

Language rule:
- Detect language from customer message first
- If unclear, use Telegram language_code if available
- If still unclear, default to English
- Reply in the same language as the customer
- Never say “I only speak German/English”
- Supported languages: German, English, Russian, French, Italian, Spanish, Ukrainian

Scope:
- backend greeting policy / prompt orchestration
- tests
- docs/status updates
- no DB migration unless absolutely needed
- no n8n OpenAI node
- no workflow redesign

Implementation options to evaluate:
A. Prompt-only:
   Add greeting rules into prompt_templates / tenant_ai_profile / knowledge.
   Fast, but not deterministic.

B. Backend conversation-state flag:
   Determine first customer message from conversation history/message count.
   Add a greeting instruction into PromptBuilder only on first turn.
   Preferred for MVP if simple.

Expected:
- first turn includes greeting + Alpstein AI intro
- second turn does not repeat intro
- Russian, German, English, French, Italian, Spanish, Ukrainian tested
- no repeated name request
- no barbershop context
- no greeting loop

Return:
- recommended design
- files changed
- tests run
- sample outputs for supported languages
- whether Greeting Orchestration MVP passed