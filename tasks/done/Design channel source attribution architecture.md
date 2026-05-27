@alpstein-api-designer

Design channel source attribution architecture for multi-platform customer ingress.

Context:
Alpstein AI will not be Telegram-only. Future channels may include:
- Telegram
- WhatsApp
- website chat
- Instagram
- Facebook Messenger
- email
- SMS
- voice/calls
- custom API/webhooks

Problem:
We need to know where the customer came from and preserve channel/source attribution for AI behavior, CRM routing, analytics, lead attribution, and future multi-channel support.

Scope:
- architecture/spec design only
- no backend implementation
- no DB migration
- no n8n workflow changes

Goal:
Extend the normalized inbound-message concept so every customer message carries channel/source metadata consistently.

Design fields:
- channel
- source_platform
- source_account_id
- source_account_name
- external_message_id
- external_customer_id
- external_conversation_id
- marketing_source
- campaign_id
- landing_page_url
- referrer_url
- utm_source
- utm_medium
- utm_campaign
- utm_content
- utm_term
- locale
- country
- region
- timezone
- ip_address_hash or privacy-safe IP metadata
- user_agent if website chat
- raw_payload for debug/audit only

Rules:
- channel/source metadata must not be mixed with message.text
- raw_payload must not be primary AI input
- source attribution should be available to AI as structured context only when safe and useful
- no secrets/tokens stored in source metadata
- external IDs must be channel-scoped
- same customer across channels may later require identity resolution, but not MVP
- one business_id still defines the AI context bundle
- channel adapter is responsible for normalizing platform-specific payloads

Deliverables:
1. Recommended normalized schema extension
2. Channel adapter model
3. Which fields belong in DB tables:
   - messages
   - conversations
   - customers
   - leads
   - channel settings
4. Which fields stay in raw_payload only
5. How AI PromptBuilder should use source/channel context
6. Privacy/security notes
7. MVP implementation slice proposal

Important:
Do not implement code.
Do not add DB migration yet.
Do not redesign current Telegram workflow.