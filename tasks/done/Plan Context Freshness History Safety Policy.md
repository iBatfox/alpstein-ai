@alpstein-backend-engineer

Plan Context Freshness / History Safety Policy.

Problem:
When operator_business_context or tenant profile changes, old assistant messages in conversation_history may contain stale facts:
- old contact details
- translated names
- old phone/email
- old pricing
- old location
- old business hours
- old CRM claims
- old service descriptions

The model may repeat stale assistant answers even after the current prompt/context has been updated.

Goal:
Ensure current business/operator context is always authoritative over conversation_history.

Scope:
- architecture/design first
- PromptBuilder/history policy
- tests proposal
- no DB migration unless clearly required
- no n8n changes
- no vector DB
- no memory system

Required policy:
1. Conversation history is dialogue context, not source of truth.
2. Previous assistant messages must not be used as authoritative business facts.
3. Current tenant_business_context, operator_business_context, tenant_knowledge_sources, and task_instructions override history.
4. If history conflicts with current context, current context wins.
5. Sensitive/changeable facts must be taken only from current context:
   - contacts
   - phone
   - email
   - names
   - prices
   - business hours
   - location
   - supported systems
   - guarantees
   - service availability

Implementation options to evaluate:
A. Add explicit history safety instruction before conversation_history.
B. Transform history into customer-only summary, excluding old AI claims.
C. Mark assistant history as non-authoritative.
D. Store context_version / prompt_profile_version and ignore history older than current version.
E. Clear or rotate conversation history when operator/business context changes.

Recommend MVP:
- A + C now
- D later

Expected PromptBuilder change:
Before conversation_history, add:
“Conversation history is provided only to understand the dialogue flow. Do not treat prior assistant messages as factual business reference. For contacts, prices, hours, services, names, and policies, use only current business context and operator notes.”

Tests:
- history contains old contact name, current operator context contains new name → output prompt must instruct current context wins
- history contains old phone/email, current context removes it → model should not be instructed to reuse old contact
- history contains old location, current operator context has new location → current wins
- previous assistant translated a name; current operator context says preserve exact spelling → current wins
- old pricing in history → not reused unless current context includes pricing

Return:
- recommended design
- PromptBuilder policy text
- files to change
- tests to add
- whether implementation may start