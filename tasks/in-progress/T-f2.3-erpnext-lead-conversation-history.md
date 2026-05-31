# T-f2.3 — ERPNext Lead conversation history

## Goal

Add a visible ERPNext Lead tab/block after "Подробности" called "История переписки" that shows chat-style conversation history.

## Scope

- Use PostgreSQL `messages` as the source of truth.
- Store an ERPNext read model as linked `Communication` rows.
- Link `Communication` rows to `Lead` with:
  - `reference_doctype = Lead`
  - `reference_name = lead.name`
  - `communication_type = Communication`
  - `communication_medium = Telegram / Instagram`
  - `sent_or_received = Sent / Received`
  - `content = message text`
  - `communication_date = message created_at`
- Add missing custom fields to `Communication`:
  - `alpstein_external_message_id`
  - `alpstein_channel`
  - `alpstein_business_id`
  - `alpstein_direction`
  - `alpstein_sender_type`
  - `alpstein_conversation_id`
- Add Lead UI tab/section "История переписки" and render linked Communications as chat.
- Sync inbound customer and outbound AI replies for Instagram and Telegram.

## Follow-up UI fix — 2026-05-31

- Keep linked ERPNext `Communication` rows as the source for Lead conversation history.
- Update only the ERPNext Lead Client Script embedded in
  `scripts/erpnext/create_alpstein_lead_fields.py`.
- Render the existing `alpstein_conversation_history` HTML field as a fixed-height
  scrollable chat window.
- Preserve oldest-to-newest order and auto-scroll to the newest message after render.
- Keep the active n8n workflow, Communication creation, Lead dedupe, AI logic, and
  Instagram/Telegram transport unchanged.
- Add runtime validation for visible Alpstein Lead fields, Client Script presence,
  and Communication query ordering.

## Idempotency

Before creating a Communication, search by:

```text
alpstein_external_message_id + alpstein_business_id
```

If a row exists, skip creation.

## Tests

- Instagram inbound creates one Communication payload.
- Instagram AI reply creates one Communication payload.
- Telegram inbound creates one Communication payload.
- Telegram AI reply creates one Communication payload.
- Duplicate webhook/search hit does not create duplicate Communication.
- All Communications link to the correct Lead.

## Out of Scope

- Do not store chat history inside Lead text fields.
- Do not duplicate messages.
- Do not change Instagram or Telegram flow semantics.
- Do not change AI logic.
- Do not create fake messages.
- Do not perform large refactors.
