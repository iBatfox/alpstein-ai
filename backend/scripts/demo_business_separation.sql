-- Demo business separation (option B): keep demo_barbershop_001, add alpstein_ai_demo_001
-- Scope: development DB only. Run manually after review.
-- Does not print secrets. Idempotent where noted.

BEGIN;

-- Fixed demo tenant (shared container for multiple demo businesses)
-- Tenant id: 11111111-1111-4111-8111-111111111111

CREATE TEMP TABLE _tenant_scope ON COMMIT DROP AS
SELECT id AS tenant_id
FROM tenants
WHERE id = '11111111-1111-4111-8111-111111111111'::uuid;

CREATE TEMP TABLE _barbershop_scope ON COMMIT DROP AS
SELECT b.tenant_id, b.id AS business_id
FROM businesses b
WHERE b.external_id = 'demo_barbershop_001';

DO $$
BEGIN
  IF (SELECT COUNT(*) FROM _tenant_scope) <> 1 THEN
    RAISE EXCEPTION 'Demo tenant missing';
  END IF;
  IF (SELECT COUNT(*) FROM _barbershop_scope) <> 1 THEN
    RAISE EXCEPTION 'demo_barbershop_001 missing';
  END IF;
END $$;

-- ---------------------------------------------------------------------------
-- 1) Create Alpstein AI demo business (isolated external_id)
-- ---------------------------------------------------------------------------
INSERT INTO businesses (
  id, tenant_id, external_id, name, business_type, description,
  language, timezone, status, created_at, updated_at
)
SELECT
  '22222222-2222-4222-8222-222222222223'::uuid,
  s.tenant_id,
  'alpstein_ai_demo_001',
  'Alpstein AI Demo',
  'saas',
  'Development demo business for Alpstein AI assistant testing (messengers, CRM, workflow automation).',
  'de',
  'Europe/Zurich',
  'active',
  NOW(),
  NOW()
FROM _tenant_scope s
WHERE NOT EXISTS (
  SELECT 1 FROM businesses b WHERE b.external_id = 'alpstein_ai_demo_001'
);

CREATE TEMP TABLE _alpstein_scope ON COMMIT DROP AS
SELECT b.tenant_id, b.id AS business_id
FROM businesses b
WHERE b.external_id = 'alpstein_ai_demo_001';

-- ---------------------------------------------------------------------------
-- 2) Alpstein AI configuration rows (no barbershop knowledge copied)
-- ---------------------------------------------------------------------------
INSERT INTO tenant_business_profiles (
  id, tenant_id, business_id,
  business_description, services, pricing, working_hours,
  target_audience, business_limitations,
  city, region, country,
  created_at, updated_at
)
SELECT
  '33333333-3333-4333-8333-333333333334'::uuid,
  a.tenant_id,
  a.business_id,
  'Alpstein AI develops AI assistants and communication automation for businesses. Projects combine messengers, webhooks, workflow orchestration, and CRM integration depending on scope.',
  '{
    "ai_assistants": "Configuration-driven customer-facing assistants",
    "integrations": "CRM and business systems via API/webhooks when scope allows",
    "workflow_automation": "n8n for webhooks, routing, notifications, retries",
    "channels": "Telegram, WhatsApp, website chat, and other channels per project"
  }'::jsonb,
  NULL,
  NULL,
  'Small and medium businesses that want faster replies, automated lead capture, and less manual messaging work.',
  'Demo scope only: do not invent live credentials, signed contracts, or production service guarantees.',
  NULL,
  NULL,
  'CH',
  NOW(),
  NOW()
FROM _alpstein_scope a
WHERE NOT EXISTS (
  SELECT 1 FROM tenant_business_profiles tbp
  WHERE tbp.business_id = a.business_id AND tbp.tenant_id = a.tenant_id
);

INSERT INTO tenant_ai_profiles (
  id, tenant_id, business_id,
  profile_name, tone, response_style, language,
  ask_for_name, ask_for_phone, ask_for_email,
  handoff_enabled, handoff_keywords, forbidden_promises,
  fallback_response, created_at, updated_at
)
SELECT
  '44444444-4444-4444-8444-444444444445'::uuid,
  a.tenant_id,
  a.business_id,
  'Alpstein AI demo profile',
  'professional',
  'concise',
  NULL,
  false,
  false,
  false,
  true,
  '["human", "agent", "operator"]'::jsonb,
  '["guaranteed SLA", "free unlimited usage"]'::jsonb,
  'Thanks for your message. Our team will follow up shortly.',
  NOW(),
  NOW()
FROM _alpstein_scope a
WHERE NOT EXISTS (
  SELECT 1 FROM tenant_ai_profiles tap
  WHERE tap.business_id = a.business_id AND tap.tenant_id = a.tenant_id
);

INSERT INTO tenant_knowledge_sources (
  id, tenant_id, business_id, source_type, title, content, tags, is_active, created_at, updated_at
)
SELECT
  v.id,
  a.tenant_id,
  a.business_id,
  v.source_type,
  v.title,
  v.content,
  v.tags::jsonb,
  true,
  NOW(),
  NOW()
FROM _alpstein_scope a
CROSS JOIN (
  VALUES
    (
      'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaa01'::uuid,
      'faq',
      'What is Alpstein AI',
      'Alpstein AI is a platform for AI assistants and customer communication automation: inbound handling, AI replies, lead capture, and owner notifications. Integrations use APIs and webhooks; CRM connectivity depends on project requirements.',
      '["platform", "faq"]'
    ),
    (
      'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaa02'::uuid,
      'capabilities',
      'Core capabilities',
      'Typical building blocks: Python/FastAPI backend, PostgreSQL, n8n orchestration, REST/webhooks, multi-channel ingress (messengers and web chat). CRM examples customers ask about include Salesforce, Bitrix24, Odoo, and Zoho — feasibility is confirmed per project.',
      '["capabilities", "services"]'
    ),
    (
      'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaa03'::uuid,
      'policy',
      'Language behavior (demo)',
      'Reply in the same language as the customer. Russian, English, and German are supported in this demo. Do not claim the business only speaks German or English.',
      '["language", "demo"]'
    )
) AS v(id, source_type, title, content, tags)
WHERE NOT EXISTS (
  SELECT 1 FROM tenant_knowledge_sources tks
  WHERE tks.id = v.id
);

-- Telegram channel: re-home existing row if present, else create deterministic row
UPDATE tenant_channel_settings tcs
SET business_id = a.business_id, updated_at = NOW()
FROM _barbershop_scope b, _alpstein_scope a
WHERE tcs.business_id = b.business_id
  AND tcs.tenant_id = b.tenant_id
  AND tcs.channel = 'telegram';

INSERT INTO tenant_channel_settings (
  id, tenant_id, business_id, channel,
  response_style, max_response_length, allow_emojis, allow_links,
  created_at, updated_at
)
SELECT
  '55555555-5555-4555-8555-555555555558'::uuid,
  a.tenant_id,
  a.business_id,
  'telegram',
  'concise',
  500,
  false,
  false,
  NOW(),
  NOW()
FROM _alpstein_scope a
WHERE NOT EXISTS (
  SELECT 1 FROM tenant_channel_settings tcs
  WHERE tcs.business_id = a.business_id
    AND tcs.tenant_id = a.tenant_id
    AND tcs.channel = 'telegram'
);

INSERT INTO tenant_channel_settings (
  id, tenant_id, business_id, channel,
  response_style, max_response_length, allow_emojis, allow_links,
  created_at, updated_at
)
SELECT
  '55555555-5555-4555-8555-555555555559'::uuid,
  a.tenant_id,
  a.business_id,
  'whatsapp',
  'concise',
  500,
  false,
  false,
  NOW(),
  NOW()
FROM _alpstein_scope a
WHERE NOT EXISTS (
  SELECT 1 FROM tenant_channel_settings tcs
  WHERE tcs.business_id = a.business_id
    AND tcs.tenant_id = a.tenant_id
    AND tcs.channel = 'whatsapp'
);

-- ---------------------------------------------------------------------------
-- 3) Move Telegram runtime data off barbershop demo (isolation)
-- ---------------------------------------------------------------------------
UPDATE conversations c
SET business_id = a.business_id, updated_at = NOW()
FROM _barbershop_scope b, _alpstein_scope a
WHERE c.business_id = b.business_id
  AND c.tenant_id = b.tenant_id
  AND c.channel = 'telegram';

UPDATE customers cu
SET business_id = a.business_id, updated_at = NOW()
FROM _barbershop_scope b, _alpstein_scope a
WHERE cu.business_id = b.business_id
  AND cu.tenant_id = b.tenant_id
  AND cu.source_channel = 'telegram';

UPDATE messages m
SET business_id = a.business_id
FROM _barbershop_scope b, _alpstein_scope a, conversations c
WHERE m.business_id = b.business_id
  AND m.tenant_id = b.tenant_id
  AND m.conversation_id = c.id
  AND c.channel = 'telegram';

UPDATE leads l
SET business_id = a.business_id, updated_at = NOW()
FROM _barbershop_scope b, _alpstein_scope a, conversations c
WHERE l.business_id = b.business_id
  AND l.tenant_id = b.tenant_id
  AND l.conversation_id = c.id
  AND c.channel = 'telegram';

UPDATE prompt_runs pr
SET business_id = a.business_id
FROM _barbershop_scope b, _alpstein_scope a, conversations c
WHERE pr.business_id = b.business_id
  AND pr.tenant_id = b.tenant_id
  AND pr.conversation_id = c.id
  AND c.channel = 'telegram';

-- Alpstein-only knowledge row must not remain on barbershop business
DELETE FROM tenant_knowledge_sources tks
USING _barbershop_scope b
WHERE tks.business_id = b.business_id
  AND tks.tenant_id = b.tenant_id
  AND tks.id = '88888888-8888-4888-8888-888888888888'::uuid;

-- ---------------------------------------------------------------------------
-- 4) Restore barbershop demo domain on demo_barbershop_001
-- ---------------------------------------------------------------------------
UPDATE tenants t
SET
  name = 'Demo Dev Tenant',
  slug = 'demo-dev',
  updated_at = NOW()
FROM _tenant_scope s
WHERE t.id = s.tenant_id;

UPDATE businesses b
SET
  name = 'Demo Barbershop Zurich',
  business_type = 'barbershop',
  description = 'Development demo business for barbershop webhook and channel testing.',
  updated_at = NOW()
FROM _barbershop_scope s
WHERE b.id = s.business_id AND b.tenant_id = s.tenant_id;

UPDATE tenant_business_profiles tbp
SET
  business_description = 'Neighborhood barbershop in Zurich for development demos.',
  services = '{"haircut": {"price": 35, "currency": "CHF"}, "beard_trim": {"price": 20, "currency": "CHF"}}'::jsonb,
  pricing = NULL,
  working_hours = '{"monday": "09:00-18:00", "tuesday": "09:00-18:00", "wednesday": "09:00-18:00", "thursday": "09:00-18:00", "friday": "09:00-18:00", "saturday": "09:00-14:00"}'::jsonb,
  target_audience = 'Local customers looking for quick walk-in haircuts.',
  business_limitations = NULL,
  city = 'Zurich',
  region = 'ZH',
  country = 'CH',
  updated_at = NOW()
FROM _barbershop_scope s
WHERE tbp.business_id = s.business_id AND tbp.tenant_id = s.tenant_id;

UPDATE tenant_ai_profiles tap
SET
  profile_name = 'Barbershop demo profile',
  tone = 'friendly',
  response_style = 'concise',
  language = 'de',
  ask_for_name = true,
  ask_for_phone = true,
  ask_for_email = false,
  handoff_enabled = true,
  handoff_keywords = '["human", "agent", "mitarbeiter"]'::jsonb,
  forbidden_promises = '["guaranteed appointment", "free service"]'::jsonb,
  fallback_response = 'Danke für Ihre Nachricht. Wir melden uns so bald wie möglich bei Ihnen.',
  updated_at = NOW()
FROM _barbershop_scope s
WHERE tap.business_id = s.business_id AND tap.tenant_id = s.tenant_id;

UPDATE tenant_knowledge_sources tks
SET
  source_type = 'faq',
  title = 'Opening hours',
  content = 'We are open Monday to Friday 09:00-18:00 and Saturday 09:00-14:00. We are closed on Sunday.',
  tags = '["hours", "faq"]'::jsonb,
  is_active = true,
  updated_at = NOW()
FROM _barbershop_scope s
WHERE tks.id = '66666666-6666-4666-8666-666666666666'::uuid
  AND tks.business_id = s.business_id AND tks.tenant_id = s.tenant_id;

UPDATE tenant_knowledge_sources tks
SET
  source_type = 'pricing',
  title = 'Haircut pricing',
  content = 'Haircut: 35 CHF. Beard trim: 20 CHF. Prices are indicative for demo use.',
  tags = '["pricing", "services"]'::jsonb,
  is_active = true,
  updated_at = NOW()
FROM _barbershop_scope s
WHERE tks.id = '77777777-7777-4777-8777-777777777777'::uuid
  AND tks.business_id = s.business_id AND tks.tenant_id = s.tenant_id;

COMMIT;
