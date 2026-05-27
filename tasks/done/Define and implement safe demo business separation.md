@alpstein-database-architect

Define and implement safe demo business separation.

Problem:
Current demo business demo_barbershop_001 was reused for Alpstein AI assistant tests.
This caused domain contamination: barbershop business profile/knowledge influenced Alpstein AI replies.

Scope:
- database architecture / demo data separation
- safe demo seed/update plan
- no schema migration unless truly necessary
- no backend logic changes unless a blocking assumption is found
- no n8n workflow redesign yet

Goal:
Prevent different agents/projects from sharing the same business context.

Required decision:
One agent/business persona must have its own business_external_id and isolated context.

Proposed separation:
- demo_barbershop_001 = barbershop demo only
- alpstein_ai_demo_001 = Alpstein AI assistant only

Tasks:
1. Inspect current demo data:
   - businesses
   - tenant_business_profiles
   - tenant_ai_profiles
   - tenant_knowledge_sources
   - tenant_channel_settings
   - conversations
   - messages

2. Propose clean data model for demo separation:
   - separate business row for alpstein_ai_demo_001
   - separate tenant_business_profile
   - separate tenant_ai_profile
   - separate tenant_knowledge_sources
   - separate tenant_channel_settings for telegram
   - no shared contaminated conversations/messages

3. Decide whether to:
   A. Rename/repurpose demo_barbershop_001 into alpstein_ai_demo_001
   or
   B. Keep barbershop demo and create new Alpstein AI demo business

Preferred:
B — keep barbershop as old demo, create new Alpstein AI demo business.

4. Provide SQL plan:
   - create new business/profile rows if missing
   - do not copy barbershop knowledge into Alpstein AI demo
   - create clean Alpstein AI knowledge
   - set AI profile language neutral/multilingual
   - ask_for_name=false
   - ask_for_phone=false

5. Identify required n8n update:
   - Normalize Telegram Incoming must use business_id/business_external_id = alpstein_ai_demo_001
   - do not change now unless approved

6. Verification:
   - query active context for alpstein_ai_demo_001
   - confirm no barber/haircut/beard/CHF terms
   - confirm barbershop context remains isolated if kept

Return:
- recommended approach
- SQL plan
- affected tables
- risks
- exact next task for n8n/business_id switch

Important:
Do not delete production-like data.
Do not mix Alpstein AI assistant with barbershop demo.
Do not expose secrets.