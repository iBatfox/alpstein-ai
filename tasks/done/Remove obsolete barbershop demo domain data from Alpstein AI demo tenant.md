@alpstein-database-architect

Remove obsolete barbershop demo domain data from Alpstein AI demo tenant.

Context:
System prompt was already updated from "local barbershop" to Alpstein AI.
messages and prompt_runs were cleared.
But runtime replies still contain:
- barbershop identity
- haircut/beard services
- Zurich barbershop language

This means obsolete business-domain data still exists in active tenant context sources.

Scope:
- demo tenant cleanup only
- database data cleanup/update only
- no schema changes
- no migrations
- no backend code changes
- no n8n changes
- no OpenAI/provider changes

Target:
business_external_id = demo_barbershop_001

Tasks:
1. Search all active prompt/business/knowledge sources for:
   - barber
   - barbershop
   - haircut
   - beard
   - Zurich
   - CHF
   - appointment
   - grooming
   - стриж
   - бород

2. Inspect:
   - tenant_business_profiles
   - tenant_knowledge_sources
   - tenant_channel_settings
   - tenant_ai_profiles
   - prompt_runs (historical only if needed)

3. Determine:
   - which active records are still injected into PromptBuilder
   - which records produce the current barbershop identity

4. Produce scoped cleanup/update SQL:
   - replace obsolete barbershop business profile with Alpstein AI profile
   - remove obsolete barbershop FAQ/knowledge rows
   - preserve tenant/business structure
   - preserve Telegram integration/runtime settings

5. Replace with Alpstein AI domain:
   - AI assistants
   - CRM integrations
   - workflow automation
   - Telegram AI assistants
   - customer communication systems

6. Verify after cleanup:
   - no active business context contains barber/haircut/beard/CHF
   - assembled prompt no longer identifies as barbershop
   - Russian/English/German language switching still works

7. Return:
   - findings
   - exact tables/rows changed
   - cleanup SQL
   - verification queries

Important:
- Do not touch non-demo tenants/businesses
- Do not print secrets
- Do not delete tables
- Do not remove Telegram channel config