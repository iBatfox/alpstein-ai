@alpstein-backend-engineer

Remove hardcoded Ivan contact details from backend pre-sales prompt and move contact ownership to workflow/operator context.

Context:
CIP-B introduced intent slices and pre-sales behavior.
We noticed Ivan’s contact details are present in backend prompt behavior / intent slices.
This is wrong architecturally:
- backend should define behavior
- workflow/operator_business_context should provide runtime contact data
- contact names must not be translated

Scope:
- backend prompt cleanup
- tests
- docs/status update
- no DB migration
- no n8n workflow change in this task
- no Langfuse runtime change
- no tenant data change unless only docs mention it

Requirements:
1. Remove hardcoded contact details from backend prompt code:
   - phone number
   - email
   - Ivan Bataiev as static contact
   - any “manager Ivan” hardcoded backend text

2. Replace with generic behavior:
   - If customer asks for contact or shows implementation interest, use contact details only if provided in business/operator context.
   - If contact details are not provided, ask the customer to leave phone or email for team follow-up.
   - Do not invent contact details.

3. Add name preservation rule:
   - Do not translate personal names, company names, email addresses, phone numbers, URLs, CRM names, or product names.
   - Preserve them exactly as provided in reference data/operator context.

4. Contact source rule:
   - Contact details belong in operator_business_context / workflow Set node or future business contact profile.
   - Backend may instruct how to use contact details, but must not own the actual contact values.

5. Update tests:
   - backend assembled §2 contains no literal phone number
   - backend assembled §2 contains no literal email
   - backend assembled §2 contains no hardcoded Ivan Bataiev contact
   - implementation_interest says “use contact details if provided” or ask customer for contact
   - contact_request behavior does not invent contact data
   - name preservation rule exists in core/intent instructions

6. Docs:
   - update conversation-intent-policy-mvp.md or technical-pre-sales doc:
     backend owns behavior, operator context owns contact data
   - update next-steps/completed
   - create task done note

Return:
- files changed
- removed hardcoded values
- tests run
- where contact data should now live
- whether n8n operator_business_context must be updated next

Important:
Do not modify n8n in this task.
Do not expose secrets.
Do not hardcode personal contact data in backend.