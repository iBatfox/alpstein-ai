@alpstein-task-planner

Create architecture spec for Conversation Intent Policy MVP.

File:
docs/architecture/conversation-intent-policy-mvp.md

Scope:
- documentation/spec only
- no backend code
- no DB migration
- no n8n changes
- no PromptBuilder implementation yet

Context:
Reviewer approved the direction but warned that §2 task_instructions is overloaded.
Conversation Intent Policy must not be added on top of the full PRE_SALES_TASK_APPENDIX.
It must replace monolithic behavior with:
- small static core charter
- small per-turn intent slices
- greeting orchestration kept separate

Goal:
Define how Alpstein AI assistant should route response behavior by current customer intent.

Required sections:

1. Problem
- current §2 task_instructions is too large
- static pre-sales appendix creates brochure tone
- contact/CRM/pricing/off-topic rules conflict
- model compliance drops when too many rules are always active

2. Design principle
- static core should be short
- dynamic intent slice should be active per turn
- no giant prompt
- no n8n intent logic
- no LLM classifier in MVP
- no LangGraph / multi-agent

3. Prompt composition target
Current:
platform_system
task_instructions + large pre_sales + greeting

Target:
platform_system
task_instructions:
  - short core task
  - compact pre-sales charter
  - one active intent_behavior slice
  - greeting orchestration block when applicable
tenant_business_context
tenant_behavior
channel_rules
knowledge
conversation_history
current_message

4. Intent list
MVP intents:
- greeting / social_greeting
- technical_interest
- implementation_interest
- pricing_interest
- unsupported_system
- confused_customer
- off_topic

5. Greeting separation
Clarify:
- GreetingPolicyService controls conversation lifecycle:
  first_contact / follow_up / soft_return
- ConversationIntentService controls current user intent:
  social opener, technical question, pricing, etc.
- They are separate and may both contribute to task_instructions.

6. Intent behavior table
For each intent define:
- purpose
- expected behavior
- what to avoid
- contact policy
- response length expectation

7. Detection rules
Define simple heuristic detection:
- current message first
- optionally previous customer message for short replies
- priority order:
  confused_customer
  pricing_interest
  implementation_interest
  unsupported_system
  technical_interest
  off_topic
  social_greeting
  default = technical_interest
- no LLM classifier in MVP

8. §2 refactor rule
Important:
PRE_SALES_TASK_APPENDIX must be reduced to a short core charter.
CRM/pricing/contact/off-topic/implementation rules must move into intent slices.
Intent Policy must reduce prompt size, not increase it.

9. Langfuse metadata
Add future fields:
- conversation_intent
- intent_matched_rule
- intent_confidence optional later
- greeting_mode stays separate

10. Tests planned
- detection tests
- prompt block tests
- no full pre-sales appendix duplication
- pricing does not invent price
- unsupported system does not guarantee support
- implementation interest asks for contact
- technical interest gives medium-depth answer
- confused customer gets one simple example
- off-topic does not become encyclopedia mode

11. Risks
- rule collisions
- overgrowing intents
- history contamination
- duplicated guidance
- premature classifier complexity

12. Implementation slices
Slice A:
- schema enum + ConversationIntentService
- tests

Slice B:
- intent prompt instruction blocks
- PromptBuilder wire
- tests

Slice C:
- Langfuse metadata

Slice D:
- live Telegram smoke test

13. Out of scope
- DB migration
- n8n changes
- vector DB
- LangGraph
- multi-agent orchestration
- lead scoring
- analytics dashboard
- new channels

Update:
- docs/project-status/next-steps.md with pointer to this spec
- docs/project-status/completed.md with “Conversation Intent Policy MVP spec created”

Return:
- files changed
- summary of spec
- open questions
- whether implementation may start after review

Important:
Do not implement code.
Do not modify runtime.
Do not change prompts in DB.