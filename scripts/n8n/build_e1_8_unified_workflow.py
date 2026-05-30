#!/usr/bin/env python3
"""Generate e1_8_unified_customer_ingress_skeleton.json from canonical channel exports."""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "n8n/workflows/e1_8_unified_customer_ingress_skeleton.json"

OPERATOR_CONTEXT = (
    "Alpstein AI demo business.\n"
    "We help businesses with AI assistants, CRM integrations, workflow automation, "
    "Telegram AI assistants, and customer communication systems.\n"
    "Reply in the customer's language (German, English, Russian, and other supported languages).\n"
    "Tone: calm, clear, concise, helpful.\n"
    "Do not ask for the customer's name unless they clearly need identification or want to book."
)

NORMALIZE_TELEGRAM = r"""// E1.8 — Telegram Update → canonical ingress (private text only)
const update = $input.first().json;

if (update.edited_message || update.channel_post || update.edited_channel_post) {
  return [];
}

const message = update.message;
if (!message || typeof message !== 'object') {
  return [];
}

if (message.from?.is_bot === true) {
  return [];
}

const chat = message.chat;
if (!chat || chat.type !== 'private') {
  return [];
}

const text = message.text;
if (!text || String(text).trim() === '') {
  return [];
}

function randomHex(length) {
  let out = '';
  while (out.length < length) {
    out += Math.floor(Math.random() * 16).toString(16);
  }
  return out.slice(0, length);
}

function randomUuidV4() {
  if (typeof crypto !== 'undefined' && crypto && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  const bytes = randomHex(32).split('');
  bytes[12] = '4';
  const variant = ['8', '9', 'a', 'b'][Math.floor(Math.random() * 4)];
  bytes[16] = variant;
  return `${bytes.slice(0, 8).join('')}-${bytes.slice(8, 12).join('')}-${bytes.slice(12, 16).join('')}-${bytes.slice(16, 20).join('')}-${bytes.slice(20, 32).join('')}`;
}

const businessId =
  typeof $env !== 'undefined' && $env.ALPSTEIN_TELEGRAM_BUSINESS_ID
    ? $env.ALPSTEIN_TELEGRAM_BUSINESS_ID
    : 'alpstein_ai_demo_001';

const chatId = String(chat.id);
const from = message.from;
const externalCustomerId = String(from.id);
const name = [from.first_name, from.last_name].filter(Boolean).join(' ').trim();

function sanitizeRawPayload(value) {
  if (value == null || typeof value !== 'object') return {};
  const secretPattern = /^(token|secret|password|authorization|api[_-]?key)$/i;
  if (Array.isArray(value)) {
    return value.map((entry) =>
      typeof entry === 'object' && entry !== null ? sanitizeRawPayload(entry) : entry
    );
  }
  const out = {};
  for (const [key, val] of Object.entries(value)) {
    if (secretPattern.test(key)) out[key] = '[REDACTED]';
    else if (typeof val === 'object' && val !== null) out[key] = sanitizeRawPayload(val);
    else out[key] = val;
  }
  return out;
}

const raw_payload = sanitizeRawPayload({
  provider: 'telegram',
  update_id: update.update_id,
  chat_id: chatId,
  chat_type: chat.type,
  message_id: message.message_id,
});

const timestamp = new Date(message.date * 1000).toISOString();
const correlation_id = randomUuidV4();

return [
  {
    json: {
      correlation_id,
      business_id: businessId,
      channel: 'telegram',
      customer: {
        phone: null,
        name: name || null,
        email: null,
        external_customer_id: externalCustomerId,
      },
      message: {
        text: String(text).trim(),
        external_message_id: `tg:${chatId}:${message.message_id}`,
        timestamp,
        raw_payload,
      },
      telegram_chat_id: chatId,
      telegram_username: from.username ? String(from.username) : null,
      telegram_language_code: from.language_code ? String(from.language_code) : null,
    },
  },
];"""

NORMALIZE_INSTAGRAM = r"""// T-N8N-IG-INGRESS — backend Meta ingress event → canonical unified format
const item = $input.first().json;
const event = item.body ?? item;

function optString(raw) {
  if (raw == null) return null;
  const text = String(raw).trim();
  return text === '' ? null : text;
}

function randomHex(length) {
  let out = '';
  while (out.length < length) {
    out += Math.floor(Math.random() * 16).toString(16);
  }
  return out.slice(0, length);
}

function randomUuidV4() {
  if (typeof crypto !== 'undefined' && crypto && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  const bytes = randomHex(32).split('');
  bytes[12] = '4';
  const variant = ['8', '9', 'a', 'b'][Math.floor(Math.random() * 4)];
  bytes[16] = variant;
  return `${bytes.slice(0, 8).join('')}-${bytes.slice(8, 12).join('')}-${bytes.slice(12, 16).join('')}-${bytes.slice(16, 20).join('')}-${bytes.slice(20, 32).join('')}`;
}

const correlation_id = optString(event.correlation_id) || randomUuidV4();
const business_id = optString(event.business_id);
const ctx = event.instagram_context || {};
const customer = event.customer || {};
const message = event.message || {};
const instagram_user_id =
  optString(ctx.instagram_user_id) || optString(customer.external_customer_id);

console.log(
  JSON.stringify({
    component: 'instagram_ingress',
    outcome: 'instagram_ingress_received',
    correlation_id,
    business_id,
    external_message_id: optString(message.external_message_id),
    execution_id: $execution.id,
  })
);

if (!business_id || !instagram_user_id) {
  return [];
}

const messageText = String(message.text || '').trim();
if (!messageText) {
  return [];
}

const normalized = {
  correlation_id,
  business_id,
  channel: 'instagram',
  customer: {
    phone: null,
    name:
      optString(ctx.instagram_display_name) ||
      optString(ctx.instagram_username) ||
      optString(customer.name),
    email: null,
    external_customer_id: instagram_user_id,
  },
  message: {
    text: messageText,
    external_message_id: optString(message.external_message_id),
    external_conversation_id:
      optString(message.external_conversation_id) || optString(ctx.conversation_id),
    timestamp: optString(message.timestamp),
    raw_payload:
      message.raw_payload && typeof message.raw_payload === 'object'
        ? message.raw_payload
        : {},
  },
  instagram_context: {
    instagram_user_id,
    instagram_username: optString(ctx.instagram_username),
    instagram_display_name: optString(ctx.instagram_display_name),
    instagram_account_id: optString(ctx.instagram_account_id),
    conversation_id:
      optString(ctx.conversation_id) || optString(message.external_conversation_id),
  },
};

console.log(
  JSON.stringify({
    component: 'instagram_ingress',
    outcome: 'instagram_normalized',
    correlation_id,
    business_id,
    external_message_id: normalized.message.external_message_id,
    execution_id: $execution.id,
  })
);

return [{ json: normalized }];"""

INSTAGRAM_REPLY_DISABLED = r"""// T-N8N-IG-INGRESS — Instagram outbound reply intentionally disabled
const item = $input.first().json;
const log = {
  component: 'instagram_reply',
  outcome: 'disabled',
  correlation_id: item.correlation_id,
  business_id: item.business_id,
  external_message_id: item.external_message_id || null,
  execution_id: $execution.id,
};
console.log(JSON.stringify(log));
return [{ json: log }];"""

SHAPE_CANONICAL = r"""// E1.8 — shared reply shaping before channel delivery
const backend = $input.first().json;
const normalized = $('Add Business Context').first().json;
const channel = normalized.channel;

const SAFE_ERROR =
  'Sorry, we could not process your message right now. Please try again in a moment.';

if (channel === 'telegram') {
  const chatId = normalized.telegram_chat_id;
  if (backend.success !== true || !backend.data) {
    return [
      {
        json: {
          channel: 'telegram',
          reply_to_customer: SAFE_ERROR,
          telegram_chat_id: chatId,
        },
      },
    ];
  }
  const reply = (backend.data.reply_to_customer || '').trim();
  return [
    {
      json: {
        channel: 'telegram',
        reply_to_customer: reply || 'Thank you for your message.',
        telegram_chat_id: chatId,
      },
    },
  ];
}

if (channel === 'website_chat') {
  const ctx = normalized.website_chat_context;
  if (backend.success !== true || !backend.data) {
    return [
      {
        json: {
          channel: 'website_chat',
          success: false,
          correlation_id: normalized.correlation_id,
          session_id: ctx.session_id,
          visitor_id: ctx.visitor_id,
          error: {
            code: backend.error?.code || 'BACKEND_RESPONSE_FAILED',
            message: backend.error?.message || 'Backend request was not successful',
          },
        },
      },
    ];
  }
  return [
    {
      json: {
        channel: 'website_chat',
        success: true,
        correlation_id: normalized.correlation_id,
        session_id: ctx.session_id,
        visitor_id: ctx.visitor_id,
        message: {
          id: `ai:${Date.now()}`,
          text: (backend.data.reply_to_customer || '').trim() || 'Thank you for your message.',
          is_duplicate: backend.data.message?.is_duplicate === true,
        },
      },
    },
  ];
}

if (channel === 'instagram') {
  const reply =
    backend.success === true && backend.data
      ? (backend.data.reply_to_customer || '').trim()
      : '';
  return [
    {
      json: {
        channel: 'instagram',
        reply_to_customer: reply,
        correlation_id: normalized.correlation_id,
        business_id: normalized.business_id,
        external_message_id: normalized.message?.external_message_id || null,
      },
    },
  ];
}

throw new Error(`Unsupported channel for reply shaping: ${channel}`);"""

FORMAT_CHANNEL_ERROR = r"""// E1.8 — HTTP/transport failure per channel
const normalized = $('Add Business Context').first().json;
const channel = normalized.channel;

if (channel === 'telegram') {
  return [
    {
      json: {
        channel: 'telegram',
        reply_to_customer:
          'Sorry, our service is temporarily unavailable. Please try again later.',
        telegram_chat_id: normalized.telegram_chat_id,
      },
    },
  ];
}

if (channel === 'website_chat') {
  const ctx = normalized.website_chat_context;
  return [
    {
      json: {
        channel: 'website_chat',
        success: false,
        correlation_id: normalized.correlation_id,
        session_id: ctx.session_id,
        visitor_id: ctx.visitor_id,
        error: {
          code: 'N8N_BACKEND_REQUEST_FAILED',
          message: 'Service is temporarily unavailable. Please retry.',
        },
      },
    },
  ];
}

if (channel === 'instagram') {
  return [
    {
      json: {
        channel: 'instagram',
        correlation_id: normalized.correlation_id,
        business_id: normalized.business_id,
        external_message_id: normalized.message?.external_message_id || null,
      },
    },
  ];
}

throw new Error(`Unsupported channel for transport error: ${channel}`);"""

SHAPE_OWNER = r"""// E1.8 — unified owner notification (channel-aware copy)
const backend = $('POST Backend').first().json;
const data = backend.data || {};
const notification = data.notification || {};
const normalized = $('Add Business Context').first().json;
const channel = normalized.channel;

const customerText = normalized?.message?.text?.trim() || null;
const customerName = normalized?.customer?.name || null;
const leadStatus = data.lead?.status || null;
const leadPriority = data.lead?.priority || null;
const convStatus = data.conversation?.status || null;

const type = notification.notification_type || 'system_error';
const reason = notification.reason || 'unknown';
const priority = notification.priority || 'normal';

const TYPE_LABELS = {
  new_lead: 'New lead',
  urgent_lead: 'Urgent lead',
  human_handoff: 'Human handoff',
  ai_failure: 'AI failure',
  system_error: 'System alert',
};

const prefix =
  channel === 'website_chat'
    ? `[Alpstein][Website Chat] ${type}`
    : `[Alpstein] ${TYPE_LABELS[type] || TYPE_LABELS.system_error}`;

const lines = [prefix, `Type: ${type}`, `Priority: ${priority}`, `Reason: ${reason}`];

if (customerName) lines.push(`Customer: ${customerName}`);
if (customerText) {
  const snippet =
    customerText.length > 280 ? customerText.slice(0, 277) + '...' : customerText;
  lines.push(`Message: ${snippet}`);
}

if (channel === 'website_chat') {
  const pageUrl = normalized?.attribution?.landing_page_url || null;
  const utmSource = normalized?.attribution?.utm_source || null;
  if (pageUrl) lines.push(`Page: ${pageUrl}`);
  if (utmSource) lines.push(`UTM source: ${utmSource}`);
} else if (convStatus) {
  lines.push(`Conversation: ${convStatus}`);
}

if (leadStatus) {
  const lp = leadPriority ? ` (${leadPriority})` : '';
  lines.push(`Lead: ${leadStatus}${lp}`);
}

return [{ json: { telegram_text: lines.join('\n'), notification_type: type } }];"""

PREPARE_DELIVERY_PATCH = r"""// E2 post-cutover — report channel delivery outcome to backend (non-blocking)
const backendData = $('POST Backend').first().json?.data;
const delivery = backendData?.delivery;

if (!delivery?.delivery_id) {
  return [];
}
if (backendData?.message?.is_duplicate === true) {
  return [];
}

const tenantId =
  typeof $env !== 'undefined' ? $env.ALPSTEIN_OBSERVABILITY_TENANT_ID : null;
const businessId =
  typeof $env !== 'undefined' ? $env.ALPSTEIN_OBSERVABILITY_BUSINESS_ID : null;
if (!tenantId || !businessId) {
  return [];
}

const normalized = $('Add Business Context').first().json;
const channel = normalized.channel;
const item = $input.first().json;

function truncate(value, max) {
  const text = String(value ?? '').trim();
  if (text.length <= max) return text;
  return text.slice(0, max - 3) + '...';
}

function stripUndefined(obj) {
  const out = {};
  for (const [key, val] of Object.entries(obj)) {
    if (val !== undefined && val !== null && val !== '') {
      out[key] = val;
    }
  }
  return out;
}

let patch_body;

if (channel === 'telegram') {
  const failed = !!(item.error || item.description || item.ok === false);
  if (failed) {
    patch_body = {
      status: 'failed',
      error_type: 'telegram_send_failed',
      error_message: truncate(
        item.error?.message || item.description || 'Telegram send failed',
        500
      ),
    };
  } else {
    const messageId = item.message_id ?? item.result?.message_id;
    patch_body = stripUndefined({
      status: 'delivered',
      provider_message_id: messageId != null ? String(messageId) : undefined,
      provider_status: 'sent',
    });
  }
} else if (channel === 'website_chat') {
  const failed = item.success === false;
  if (failed) {
    patch_body = {
      status: 'failed',
      error_type: 'website_chat_delivery_failed',
      error_message: truncate(
        item.error?.message || 'Website response delivery failed',
        500
      ),
    };
  } else {
    patch_body = stripUndefined({
      status: 'delivered',
      provider_message_id: item.message?.id ? String(item.message.id) : undefined,
      provider_status: 'responded',
    });
  }
} else {
  return [];
}

return [
  {
    json: {
      delivery_id: delivery.delivery_id,
      tenant_id: tenantId,
      business_id: businessId,
      patch_body,
      channel,
    },
  },
];"""

PATCH_DELIVERY_URL = (
    "={{ $env.BACKEND_BASE_URL + '/api/v1/observability/deliveries/' "
    "+ $json.delivery_id + '?tenant_id=' + encodeURIComponent($json.tenant_id) "
    "+ '&business_id=' + encodeURIComponent($json.business_id) }}"
)

ERPNEXT_BASE_URL_EXPR = (
    "($env.ERPNEXT_BASE_URL || 'https://crm.alpstein-ai.ch').replace(/\\/$/, '')"
)
ERPNEXT_SEARCH_URL = f"={{{{ {ERPNEXT_BASE_URL_EXPR} + $json.erpnext_search_path }}}}"
ERPNEXT_UPDATE_URL = (
    f"={{{{ {ERPNEXT_BASE_URL_EXPR} + '/api/resource/Lead/' "
    f"+ encodeURIComponent($json.erpnext_lead_name) }}}}"
)
ERPNEXT_CREATE_URL = f"={{{{ {ERPNEXT_BASE_URL_EXPR} + '/api/resource/Lead' }}}}"

ERPNEXT_HTTP_AUTH = {
    "authentication": "genericCredentialType",
    "genericAuthType": "httpHeaderAuth",
}

ERPNEXT_HTTP_OPTIONS = {
    "timeout": 15000,
    "response": {
        "response": {
            "fullResponse": True,
            "neverError": True,
            "responseFormat": "json",
        }
    },
}

PREPARE_ERPNEXT_LEAD = r"""// F.2.2 — CRM copy after Alpstein SoT (field-based dedupe, non-blocking tail)
const enabled =
  typeof $env !== 'undefined' && $env.ALPSTEIN_ERPNEXT_LEAD_SYNC_ENABLED === 'true';
if (!enabled) {
  return [];
}

const backend = $('POST Backend').first().json;
if (backend.success !== true || !backend.data) {
  return [];
}

const normalized = $('Add Business Context').first().json;
const customer = normalized.customer || {};
const channel = normalized.channel;
const businessId = normalized.business_id;
const bizFilter = ['alpstein_business_id', '=', businessId];

const isDuplicate = backend.data?.message?.is_duplicate === true;
if (isDuplicate && channel !== 'instagram') {
  return [];
}

function normalizePhone(raw) {
  if (!raw) return null;
  const digits = String(raw).replace(/\D/g, '');
  if (digits.length < 6) return null;
  return digits;
}

function normalizeEmail(raw) {
  if (!raw || typeof raw !== 'string') return null;
  const email = raw.trim().toLowerCase();
  return email.includes('@') ? email : null;
}

function normalizeName(raw) {
  if (!raw) return null;
  const name = String(raw).trim().replace(/\s+/g, ' ');
  return name || null;
}

function optString(raw) {
  if (raw == null) return null;
  const text = String(raw).trim();
  return text === '' ? null : text;
}

function erpnextDateTime(raw) {
  if (!raw) return null;
  const d = new Date(raw);
  if (Number.isNaN(d.getTime())) return null;
  const pad = (n) => String(n).padStart(2, '0');
  return (
    d.getUTCFullYear() +
    '-' +
    pad(d.getUTCMonth() + 1) +
    '-' +
    pad(d.getUTCDate()) +
    ' ' +
    pad(d.getUTCHours()) +
    ':' +
    pad(d.getUTCMinutes()) +
    ':' +
    pad(d.getUTCSeconds())
  );
}

const phone = normalizePhone(customer.phone);
const email = normalizeEmail(customer.email);
const externalId = customer.external_customer_id
  ? String(customer.external_customer_id)
  : null;
const displayName = normalizeName(customer.name);

let chatId = null;
if (channel === 'telegram' && normalized.telegram_chat_id) {
  chatId = String(normalized.telegram_chat_id);
} else if (channel === 'website_chat' && normalized.website_chat_context?.visitor_id) {
  chatId = String(normalized.website_chat_context.visitor_id);
} else if (channel === 'instagram') {
  const ctx = normalized.instagram_context || {};
  chatId = ctx.conversation_id
    ? String(ctx.conversation_id)
    : ctx.instagram_user_id
      ? String(ctx.instagram_user_id)
      : null;
}

let dedupeTier = null;
let dedupeValue = null;
let filters = null;

if (phone) {
  dedupeTier = 'phone';
  dedupeValue = phone;
  filters = [['mobile_no', '=', phone], bizFilter];
} else if (email) {
  dedupeTier = 'email';
  dedupeValue = email;
  filters = [['email_id', '=', email], bizFilter];
} else if (chatId) {
  dedupeTier = 'chat_id';
  dedupeValue = `${channel}:${businessId}:${chatId}`;
  filters = [
    ['alpstein_channel', '=', channel],
    bizFilter,
    ['alpstein_chat_id', '=', chatId],
  ];
} else if (externalId) {
  dedupeTier = 'external_id';
  dedupeValue = `${channel}:${businessId}:${externalId}`;
  filters = [
    ['alpstein_channel', '=', channel],
    bizFilter,
    ['alpstein_external_user_id', '=', externalId],
  ];
} else {
  const safeName = (displayName || 'visitor')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .slice(0, 40);
  dedupeTier = 'name_channel_business';
  dedupeValue = `${safeName}:${channel}:${businessId}`;
  const leadName = `${channel} / ${businessId} / ${displayName || 'visitor'}`;
  filters = [['lead_name', '=', leadName], bizFilter];
}

const messageAt =
  erpnextDateTime(normalized.message?.timestamp) ||
  erpnextDateTime(new Date().toISOString());
const tenantId =
  backend.data?.tenant_id || backend.data?.tenant?.id || backend.data?.business?.tenant_id || null;

const attr = normalized.attribution || {};
const websitePayload = normalized.message?.raw_payload?.website_payload || {};

function touchFromAttribution() {
  const source = optString(attr.utm_source) || optString(attr.marketing_source);
  return {
    source,
    medium: optString(attr.utm_medium),
    campaign: optString(attr.utm_campaign) || optString(attr.campaign_id),
    content: optString(attr.utm_content),
    term: optString(attr.utm_term),
    landing_page: optString(attr.landing_page_url),
    referrer_url: optString(attr.referrer_url),
    gclid: optString(websitePayload.gclid),
    fbclid: optString(websitePayload.fbclid),
  };
}

const touch = touchFromAttribution();

const sourceMap = {
  telegram: 'Telegram',
  website_chat: 'Website Chat',
  whatsapp: 'WhatsApp',
  instagram: 'Instagram',
};

const leadNameBase =
  displayName || (externalId ? `${channel} user ${externalId}` : `${channel} visitor`);
let leadName = leadNameBase;
if (channel === 'instagram') {
  const ctx = normalized.instagram_context || {};
  leadName =
    optString(ctx.instagram_display_name) ||
    optString(ctx.instagram_username) ||
    (externalId ? `instagram user ${externalId}` : 'instagram visitor');
}

const leadDoc = {
  lead_name: leadName,
  status: 'Lead',
  source: sourceMap[channel] || channel,
  alpstein_channel: channel,
  alpstein_business_id: businessId,
  alpstein_tenant_id: tenantId ? String(tenantId) : null,
  alpstein_external_user_id: externalId,
  alpstein_chat_id: chatId,
  first_message_at: messageAt,
  last_message_at: messageAt,
  conversation_count: 1,
  last_message_channel: channel,
  first_touch_source: touch.source,
  first_touch_medium: touch.medium,
  first_touch_campaign: touch.campaign,
  first_touch_content: touch.content,
  first_touch_term: touch.term,
  last_touch_source: touch.source,
  last_touch_medium: touch.medium,
  last_touch_campaign: touch.campaign,
  last_touch_content: touch.content,
  last_touch_term: touch.term,
  landing_page: touch.landing_page,
  referrer_url: touch.referrer_url,
  gclid: touch.gclid,
  fbclid: touch.fbclid,
  telegram_username: optString(normalized.telegram_username),
  telegram_language_code: optString(normalized.telegram_language_code),
  instagram_username: optString(normalized.instagram_context?.instagram_username),
  instagram_display_name: optString(normalized.instagram_context?.instagram_display_name),
};

if (phone) {
  leadDoc.mobile_no = phone;
  leadDoc.phone = phone;
}
if (email) {
  leadDoc.email_id = email;
}

const searchFields = [
  'name',
  'lead_name',
  'mobile_no',
  'email_id',
  'source',
  'status',
  'alpstein_channel',
  'alpstein_business_id',
  'alpstein_chat_id',
  'alpstein_external_user_id',
  'conversation_count',
  'first_message_at',
  'last_message_at',
  'first_touch_source',
  'last_touch_source',
  'landing_page',
  'telegram_username',
  'instagram_username',
  'instagram_display_name',
];

function buildQuery(params) {
  return Object.entries(params)
    .map(
      ([k, v]) =>
        encodeURIComponent(k) + '=' + encodeURIComponent(String(v))
    )
    .join('&');
}

const searchQuery = buildQuery({
  filters: JSON.stringify(filters),
  fields: JSON.stringify(searchFields),
  limit_page_length: '1',
});

const searchPath = '/api/resource/Lead?' + searchQuery;

return [
  {
    json: {
      erpnext_search_path: searchPath,
      erpnext_lead_doc: leadDoc,
      erpnext_touch: touch,
      erpnext_message_at: messageAt,
      erpnext_dedupe_tier: dedupeTier,
      erpnext_dedupe_value: dedupeValue,
      correlation_id: normalized.correlation_id,
      channel,
      business_id: businessId,
    },
  },
];"""

ERPNEXT_HTTP_HELPERS = r"""
function getHttpStatus(json) {
  if (!json || typeof json !== 'object') return null;
  return (
    json.statusCode ??
    json.status ??
    json.response?.statusCode ??
    json.response?.status ??
    json.error?.statusCode ??
    json.error?.status ??
    null
  );
}

function getHttpError(json) {
  if (!json || typeof json !== 'object') return null;
  return (
    json.message ??
    json.error?.message ??
    json.errorMessage ??
    json.body?.message ??
    json.body?.exception ??
    json.body?._server_messages ??
    json.exception ??
    null
  );
}

function unwrapHttpBody(json) {
  if (!json || typeof json !== 'object') return null;
  if (json.body != null) {
    if (typeof json.body === 'string') {
      try {
        return JSON.parse(json.body);
      } catch {
        return { message: json.body };
      }
    }
    return json.body;
  }
  if (json.response?.body != null) {
    const inner = json.response.body;
    if (typeof inner === 'string') {
      try {
        return JSON.parse(inner);
      } catch {
        return { message: inner };
      }
    }
    return inner;
  }
  return json;
}

function getErpnextListRows(json) {
  const body = unwrapHttpBody(json);
  const data = body?.data ?? json?.data ?? json?.response?.body?.data;
  return Array.isArray(data) ? data : [];
}

function getErpnextDocName(json) {
  const body = unwrapHttpBody(json);
  const data = body?.data ?? json?.data ?? json?.response?.body?.data;
  if (data && typeof data === 'object' && data.name) return data.name;
  if (json?.name) return json.name;
  if (body?.name) return body.name;
  return null;
}

function isHttpFailure(json) {
  if (!json || typeof json !== 'object') return true;
  if (json.__transport_error === true) return true;
  if (typeof json.error === 'string' && json.error.trim() !== '') return true;
  if (json.error && typeof json.error === 'object' && !getHttpStatus(json) && !json.body) {
    return true;
  }
  const status = getHttpStatus(json);
  if (status != null && status >= 400) return true;
  const body = unwrapHttpBody(json);
  if (body?.exc || body?.exception) return true;
  return false;
}
"""

PARSE_ERPNEXT_SEARCH = (
    ERPNEXT_HTTP_HELPERS
    + r"""// F.2.2c — interpret ERPNext Lead search response (HTTP Request node output)
const prep = $('Prepare ERPNext Lead Payload').first().json;
const item = $input.first().json;

if (isHttpFailure(item)) {
  return [
    {
      json: {
        ...prep,
        erpnext_lead_exists: false,
        erpnext_lead_name: null,
        erpnext_existing_row: null,
        erpnext_search_failed: true,
        erpnext_search_ok: false,
        erpnext_search_error: getHttpError(item) || 'ERPNext search failed',
        erpnext_http_status: getHttpStatus(item),
      },
    },
  ];
}

const rows = getErpnextListRows(item);
const existing = rows.length > 0 ? rows[0] : null;

return [
  {
    json: {
      ...prep,
      erpnext_lead_exists: !!existing,
      erpnext_lead_name: existing?.name || null,
      erpnext_existing_row: existing,
      erpnext_search_failed: false,
      erpnext_search_ok: true,
      erpnext_search_error: null,
      erpnext_http_status: getHttpStatus(item),
    },
  },
];
"""
)

PREPARE_ERPNEXT_UPDATE = r"""// F.2.2 — update existing Lead (custom fields, no description dedupe)
const row = $input.first().json;
const existing = row.erpnext_existing_row || {};
const touch = row.erpnext_touch || {};
function erpnextDateTime(raw) {
  if (!raw) return null;
  const d = new Date(raw);
  if (Number.isNaN(d.getTime())) return null;
  const pad = (n) => String(n).padStart(2, '0');
  return (
    d.getUTCFullYear() +
    '-' +
    pad(d.getUTCMonth() + 1) +
    '-' +
    pad(d.getUTCDate()) +
    ' ' +
    pad(d.getUTCHours()) +
    ':' +
    pad(d.getUTCMinutes()) +
    ':' +
    pad(d.getUTCSeconds())
  );
}

const messageAt =
  erpnextDateTime(row.erpnext_message_at) ||
  erpnextDateTime(new Date().toISOString());
const prevCount = Number(existing.conversation_count || 0);

const body = {
  ...row.erpnext_lead_doc,
  last_message_at: messageAt,
  last_message_channel: row.channel,
  conversation_count: prevCount > 0 ? prevCount + 1 : 1,
  last_touch_source: touch.source ?? existing.last_touch_source,
  last_touch_medium: touch.medium ?? existing.last_touch_medium,
  last_touch_campaign: touch.campaign ?? existing.last_touch_campaign,
  last_touch_content: touch.content ?? existing.last_touch_content,
  last_touch_term: touch.term ?? existing.last_touch_term,
};

if (touch.landing_page) body.landing_page = touch.landing_page;
if (touch.referrer_url) body.referrer_url = touch.referrer_url;
if (touch.gclid) body.gclid = touch.gclid;
if (touch.fbclid) body.fbclid = touch.fbclid;

return [
  {
    json: {
      erpnext_lead_name: row.erpnext_lead_name,
      erpnext_update_body: body,
      correlation_id: row.correlation_id,
      channel: row.channel,
      business_id: row.business_id,
      erpnext_dedupe_tier: row.erpnext_dedupe_tier,
      erpnext_dedupe_value: row.erpnext_dedupe_value,
      erpnext_lead_exists: true,
    },
  },
];"""

PREPARE_ERPNEXT_CREATE = r"""// F.2.2 — new ERPNext Lead document (structured fields)
const row = $input.first().json;

return [
  {
    json: {
      erpnext_create_body: { ...row.erpnext_lead_doc },
      correlation_id: row.correlation_id,
      channel: row.channel,
      business_id: row.business_id,
      erpnext_dedupe_tier: row.erpnext_dedupe_tier,
      erpnext_dedupe_value: row.erpnext_dedupe_value,
      erpnext_lead_exists: false,
    },
  },
];"""

ERPNEXT_RESULT_LOGGER = (
    ERPNEXT_HTTP_HELPERS
    + r"""// F.2.2c — structured log line (no secrets / no message bodies)
const prep = $('Prepare ERPNext Lead Payload').first().json;
const item = $input.first().json;

function truncate(value, max) {
  const text = String(value ?? '').trim();
  if (text.length <= max) return text;
  return text.slice(0, max - 3) + '...';
}

let outcome = 'failed';
let erpnext_lead_id = null;
let error_message = null;

if (isHttpFailure(item)) {
  error_message = truncate(getHttpError(item) || 'ERPNext request failed', 200);
} else {
  erpnext_lead_id = getErpnextDocName(item);
  const parseRow = $('Parse ERPNext Search').first().json;
  const existed = parseRow.erpnext_lead_exists === true;
  if (erpnext_lead_id) {
    outcome = existed ? 'updated' : 'created';
  } else {
    outcome = 'failed';
    error_message = 'ERPNext response missing lead name';
  }
}

const log = {
  component: 'erpnext_lead_sync',
  outcome,
  channel: prep.channel,
  correlation_id: prep.correlation_id,
  business_id: prep.business_id,
  dedupe_tier: prep.erpnext_dedupe_tier,
  dedupe_value: prep.erpnext_dedupe_value,
  erpnext_lead_id,
  http_status: getHttpStatus(item),
  error_message,
  execution_id: $execution.id,
};

console.log(JSON.stringify(log));
return [{ json: log }];
"""
)

ERPNEXT_SEARCH_FAILED_LOGGER = (
    ERPNEXT_HTTP_HELPERS
    + r"""// F.2.2b — search failed: do not create Lead (dedupe safety)
const prep = $('Prepare ERPNext Lead Payload').first().json;
const row = $('Parse ERPNext Search').first().json;

function truncate(value, max) {
  const text = String(value ?? '').trim();
  if (text.length <= max) return text;
  return text.slice(0, max - 3) + '...';
}

const log = {
  component: 'erpnext_lead_sync',
  outcome: 'search_failed',
  channel: prep.channel,
  correlation_id: prep.correlation_id,
  business_id: prep.business_id,
  dedupe_tier: prep.erpnext_dedupe_tier,
  dedupe_value: prep.erpnext_dedupe_value,
  erpnext_lead_id: null,
  http_status: row.erpnext_http_status ?? getHttpStatus(row),
  error_message: truncate(row.erpnext_search_error || 'ERPNext search failed', 200),
  execution_id: $execution.id,
};

console.log(JSON.stringify(log));
return [{ json: log }];
"""
)

ERPNEXT_CREDENTIALS = {"httpHeaderAuth": {"name": "erpnext_crm_api"}}

POST_JSON_BODY = (
    "={{ (() => { const j = $json; const body = { correlation_id: j.correlation_id, "
    "business_id: j.business_id, channel: j.channel, customer: j.customer, message: j.message, "
    "operator_business_context: j.operator_business_context }; "
    "if (j.source) body.source = j.source; if (j.attribution) body.attribution = j.attribution; "
    "return body; })() }}"
)


def node(nid, name, ntype, type_version, position, parameters, **extra):
    o = {
        "parameters": parameters,
        "id": nid,
        "name": name,
        "type": ntype,
        "typeVersion": type_version,
        "position": position,
    }
    o.update(extra)
    return o


def main() -> None:
    nodes = [
        node(
            "e1800001-0000-4000-8000-000000000001",
            "Telegram Trigger",
            "n8n-nodes-base.telegramTrigger",
            1.2,
            [0, 200],
            {"updates": ["message"], "additionalFields": {}},
            webhookId="alpstein-telegram-customer-trigger-unified-inactive",
            credentials={"telegramApi": {"name": "alpsteinai_0001bot"}},
            notesInFlow=True,
            notes="E1.8 INACTIVE: non-prod webhookId. Do not activate while production Telegram workflow is active.",
        ),
        node(
            "ig180001-0000-4000-8000-000000000001",
            "Instagram Backend Event Webhook",
            "n8n-nodes-base.webhook",
            2,
            [0, 820],
            {
                "httpMethod": "POST",
                "path": "alpstein/unified-customer-ingress/instagram/incoming",
                "responseMode": "onReceived",
                "options": {"responseCode": 200},
            },
            webhookId="alpstein-unified-instagram-backend-ingress",
            notesInFlow=True,
            notes="T-N8N-IG-INGRESS: backend dispatch after Meta DM persist. Immediate 200 response; no responseNode.",
        ),
        node(
            "e1800001-0000-4000-8000-000000000005",
            "Normalize Telegram Incoming",
            "n8n-nodes-base.code",
            2,
            [280, 200],
            {"jsCode": NORMALIZE_TELEGRAM},
        ),
        node(
            "ig180002-0000-4000-8000-000000000001",
            "Normalize Instagram Incoming",
            "n8n-nodes-base.code",
            2,
            [280, 820],
            {"jsCode": NORMALIZE_INSTAGRAM},
        ),
        node(
            "e1800001-0000-4000-8000-000000000007",
            "Add Business Context",
            "n8n-nodes-base.set",
            2,
            [840, 360],
            {
                "keepOnlySet": False,
                "values": {
                    "string": [
                        {
                            "name": "operator_business_context",
                            "value": OPERATOR_CONTEXT,
                        }
                    ]
                },
                "options": {},
            },
            notesInFlow=True,
            notes="E1.8 shared: operator_business_context for ALL channels.",
        ),
        node(
            "e1800001-0000-4000-8000-000000000008",
            "POST Backend",
            "n8n-nodes-base.httpRequest",
            4.2,
            [1080, 360],
            {
                "method": "POST",
                "url": "={{ $env.BACKEND_BASE_URL }}/api/v1/webhook/message",
                "sendHeaders": True,
                "headerParameters": {
                    "parameters": [
                        {"name": "Content-Type", "value": "application/json"},
                        {
                            "name": "X-Alpstein-Webhook-Token",
                            "value": "={{ $env.N8N_BACKEND_API_TOKEN }}",
                        },
                        {
                            "name": "X-Correlation-Id",
                            "value": "={{ $json.correlation_id }}",
                        },
                        {
                            "name": "X-N8n-Execution-Id",
                            "value": "={{ $execution.id }}",
                        },
                    ]
                },
                "sendBody": True,
                "specifyBody": "json",
                "jsonBody": POST_JSON_BODY,
                "options": {"timeout": 30000},
            },
            onError="continueErrorOutput",
            notesInFlow=True,
            notes="E1.8 shared POST. Includes operator_business_context + correlation_id.",
        ),
        node(
            "e1800001-0000-4000-8000-000000000009",
            "Shape Canonical Customer Reply",
            "n8n-nodes-base.code",
            2,
            [1340, 260],
            {"jsCode": SHAPE_CANONICAL},
        ),
        node(
            "e1800001-0000-4000-8000-00000000000a",
            "Format Channel Backend Error",
            "n8n-nodes-base.code",
            2,
            [1340, 480],
            {"jsCode": FORMAT_CHANNEL_ERROR},
        ),
        node(
            "e1800001-0000-4000-8000-00000000000b",
            "Route Reply Telegram",
            "n8n-nodes-base.if",
            2.2,
            [1600, 200],
            {
                "conditions": {
                    "options": {
                        "caseSensitive": True,
                        "leftValue": "",
                        "typeValidation": "strict",
                        "version": 2,
                    },
                    "conditions": [
                        {
                            "id": "cond-channel-telegram",
                            "leftValue": "={{ $json.channel }}",
                            "rightValue": "telegram",
                            "operator": {"type": "string", "operation": "equals"},
                        }
                    ],
                    "combinator": "and",
                },
                "options": {},
            },
        ),
        node(
            "ig180003-0000-4000-8000-000000000001",
            "Route Reply Instagram",
            "n8n-nodes-base.if",
            2.2,
            [1600, 520],
            {
                "conditions": {
                    "options": {
                        "caseSensitive": True,
                        "leftValue": "",
                        "typeValidation": "strict",
                        "version": 2,
                    },
                    "conditions": [
                        {
                            "id": "cond-channel-instagram",
                            "leftValue": "={{ $json.channel }}",
                            "rightValue": "instagram",
                            "operator": {"type": "string", "operation": "equals"},
                        }
                    ],
                    "combinator": "and",
                },
                "options": {},
            },
        ),
        node(
            "ig180004-0000-4000-8000-000000000001",
            "Instagram Reply Disabled Logger",
            "n8n-nodes-base.code",
            2,
            [1860, 520],
            {"jsCode": INSTAGRAM_REPLY_DISABLED},
        ),
        node(
            "e1800001-0000-4000-8000-00000000000e",
            "Telegram Send Message",
            "n8n-nodes-base.telegram",
            1.2,
            [1860, 200],
            {
                "resource": "message",
                "operation": "sendMessage",
                "chatId": "={{ $json.telegram_chat_id }}",
                "text": "={{ $json.reply_to_customer }}",
                "additionalFields": {"appendAttribution": False},
            },
            continueOnFail=True,
            credentials={"telegramApi": {"name": "alpsteinai_0001bot"}},
        ),
        node(
            "e1800001-0000-4000-8000-000000000015",
            "Prepare Delivery PATCH",
            "n8n-nodes-base.code",
            2,
            [2120, 360],
            {"jsCode": PREPARE_DELIVERY_PATCH},
            notesInFlow=True,
            notes="E2: PATCH delivery outcome after transport. Skips duplicate / missing delivery_id.",
        ),
        node(
            "e1800001-0000-4000-8000-000000000016",
            "PATCH Delivery Outcome",
            "n8n-nodes-base.httpRequest",
            4.2,
            [2380, 360],
            {
                "method": "PATCH",
                "url": PATCH_DELIVERY_URL,
                "sendHeaders": True,
                "headerParameters": {
                    "parameters": [
                        {"name": "Content-Type", "value": "application/json"},
                        {
                            "name": "X-Alpstein-Webhook-Token",
                            "value": "={{ $env.N8N_BACKEND_API_TOKEN }}",
                        },
                        {
                            "name": "X-Correlation-Id",
                            "value": "={{ $('Add Business Context').first().json.correlation_id }}",
                        },
                        {
                            "name": "X-N8n-Execution-Id",
                            "value": "={{ $execution.id }}",
                        },
                    ]
                },
                "sendBody": True,
                "specifyBody": "json",
                "jsonBody": "={{ $json.patch_body }}",
                "options": {"timeout": 10000},
            },
            continueOnFail=True,
            onError="continueRegularOutput",
            notesInFlow=True,
            notes="E2: Non-blocking observability PATCH. Failure leaves delivery pending.",
        ),
        node(
            "e1800001-0000-4000-8000-000000000011",
            "IF Notify Owner",
            "n8n-nodes-base.if",
            2.2,
            [1340, 700],
            {
                "conditions": {
                    "options": {
                        "caseSensitive": True,
                        "leftValue": "",
                        "typeValidation": "strict",
                        "version": 2,
                    },
                    "conditions": [
                        {
                            "id": "cond-notify-owner",
                            "leftValue": "={{ $('POST Backend').first().json.data.notify_owner }}",
                            "rightValue": "",
                            "operator": {
                                "type": "boolean",
                                "operation": "true",
                                "singleValue": True,
                            },
                        },
                        {
                            "id": "cond-notification-exists",
                            "leftValue": "={{ $('POST Backend').first().json.data.notification }}",
                            "rightValue": "",
                            "operator": {
                                "type": "object",
                                "operation": "notEmpty",
                                "singleValue": True,
                            },
                        },
                        {
                            "id": "cond-not-duplicate",
                            "leftValue": "={{ $('POST Backend').first().json.data.message.is_duplicate }}",
                            "rightValue": False,
                            "operator": {"type": "boolean", "operation": "equals"},
                        },
                    ],
                    "combinator": "and",
                },
                "options": {},
            },
        ),
        node(
            "e1800001-0000-4000-8000-000000000012",
            "Shape Owner Notification",
            "n8n-nodes-base.code",
            2,
            [1600, 700],
            {"jsCode": SHAPE_OWNER},
        ),
        node(
            "e1800001-0000-4000-8000-000000000013",
            "Telegram Owner Notify",
            "n8n-nodes-base.telegram",
            1.2,
            [1860, 700],
            {
                "resource": "message",
                "operation": "sendMessage",
                "chatId": "={{ $env.TELEGRAM_CHAT_ID }}",
                "text": "={{ $json.telegram_text }}",
                "additionalFields": {"appendAttribution": False},
            },
            continueOnFail=True,
            credentials={"telegramApi": {"name": "AlpsteinAIbot"}},
        ),
        node(
            "f210001-0000-4000-8000-000000000001",
            "Prepare ERPNext Lead Payload",
            "n8n-nodes-base.code",
            2,
            [1340, 900],
            {"jsCode": PREPARE_ERPNEXT_LEAD},
            notesInFlow=True,
            notes="F.2.1: After POST Backend success. Kill switch ALPSTEIN_ERPNEXT_LEAD_SYNC_ENABLED.",
        ),
        node(
            "f210001-0000-4000-8000-000000000002",
            "Search ERPNext Lead",
            "n8n-nodes-base.httpRequest",
            4.2,
            [1600, 900],
            {
                "method": "GET",
                "url": ERPNEXT_SEARCH_URL,
                "authentication": ERPNEXT_HTTP_AUTH["authentication"],
                "genericAuthType": ERPNEXT_HTTP_AUTH["genericAuthType"],
                "options": ERPNEXT_HTTP_OPTIONS,
            },
            continueOnFail=True,
            onError="continueRegularOutput",
            credentials=ERPNEXT_CREDENTIALS,
            notesInFlow=True,
            notes="F.2.2c: GET fullResponse+neverError; genericCredentialType httpHeaderAuth",
        ),
        node(
            "f210001-0000-4000-8000-000000000003",
            "Parse ERPNext Search",
            "n8n-nodes-base.code",
            2,
            [1860, 900],
            {"jsCode": PARSE_ERPNEXT_SEARCH},
        ),
        node(
            "f210010-0000-4000-8000-000000000001",
            "IF ERPNext Search OK",
            "n8n-nodes-base.if",
            2.2,
            [2000, 900],
            {
                "conditions": {
                    "options": {
                        "caseSensitive": True,
                        "leftValue": "",
                        "typeValidation": "strict",
                        "version": 2,
                    },
                    "conditions": [
                        {
                            "id": "cond-erpnext-search-ok",
                            "leftValue": "={{ $json.erpnext_search_ok }}",
                            "rightValue": "",
                            "operator": {
                                "type": "boolean",
                                "operation": "true",
                                "singleValue": True,
                            },
                        }
                    ],
                    "combinator": "and",
                },
                "options": {},
            },
            notesInFlow=True,
            notes="F.2.2b: false → search_failed log only (no create).",
        ),
        node(
            "f210010-0000-4000-8000-000000000002",
            "ERPNext Search Failed Logger",
            "n8n-nodes-base.code",
            2,
            [2240, 1020],
            {"jsCode": ERPNEXT_SEARCH_FAILED_LOGGER},
        ),
        node(
            "f210001-0000-4000-8000-000000000004",
            "IF ERPNext Lead Exists",
            "n8n-nodes-base.if",
            2.2,
            [2240, 820],
            {
                "conditions": {
                    "options": {
                        "caseSensitive": True,
                        "leftValue": "",
                        "typeValidation": "strict",
                        "version": 2,
                    },
                    "conditions": [
                        {
                            "id": "cond-erpnext-lead-exists",
                            "leftValue": "={{ $json.erpnext_lead_exists }}",
                            "rightValue": "",
                            "operator": {
                                "type": "boolean",
                                "operation": "true",
                                "singleValue": True,
                            },
                        }
                    ],
                    "combinator": "and",
                },
                "options": {},
            },
        ),
        node(
            "f210001-0000-4000-8000-000000000005",
            "Prepare ERPNext Lead Update",
            "n8n-nodes-base.code",
            2,
            [2380, 820],
            {"jsCode": PREPARE_ERPNEXT_UPDATE},
        ),
        node(
            "f210001-0000-4000-8000-000000000006",
            "Update ERPNext Lead",
            "n8n-nodes-base.httpRequest",
            4.2,
            [2760, 760],
            {
                "method": "PUT",
                "url": ERPNEXT_UPDATE_URL,
                "authentication": ERPNEXT_HTTP_AUTH["authentication"],
                "genericAuthType": ERPNEXT_HTTP_AUTH["genericAuthType"],
                "sendBody": True,
                "specifyBody": "json",
                "jsonBody": "={{ $json.erpnext_update_body }}",
                "options": ERPNEXT_HTTP_OPTIONS,
            },
            continueOnFail=True,
            onError="continueRegularOutput",
            credentials=ERPNEXT_CREDENTIALS,
        ),
        node(
            "f210001-0000-4000-8000-000000000007",
            "Prepare ERPNext Lead Create",
            "n8n-nodes-base.code",
            2,
            [2380, 980],
            {"jsCode": PREPARE_ERPNEXT_CREATE},
        ),
        node(
            "f210001-0000-4000-8000-000000000008",
            "Create ERPNext Lead",
            "n8n-nodes-base.httpRequest",
            4.2,
            [2760, 920],
            {
                "method": "POST",
                "url": ERPNEXT_CREATE_URL,
                "authentication": ERPNEXT_HTTP_AUTH["authentication"],
                "genericAuthType": ERPNEXT_HTTP_AUTH["genericAuthType"],
                "sendBody": True,
                "specifyBody": "json",
                "jsonBody": "={{ $json.erpnext_create_body }}",
                "options": ERPNEXT_HTTP_OPTIONS,
            },
            continueOnFail=True,
            onError="continueRegularOutput",
            credentials=ERPNEXT_CREDENTIALS,
        ),
        node(
            "f210001-0000-4000-8000-000000000009",
            "ERPNext Result Logger",
            "n8n-nodes-base.code",
            2,
            [2900, 900],
            {"jsCode": ERPNEXT_RESULT_LOGGER},
            notesInFlow=True,
            notes="F.2.1: console JSON log — does not affect customer reply path.",
        ),
        {
            "parameters": {
                "content": "## Unified customer ingress + E2 delivery PATCH\n\nTelegram + Instagram backend event → POST Backend → channel delivery → PATCH delivery outcome.\n\nWebsite channel is temporarily disabled until the Website Chat phase.\n\nRequires ALPSTEIN_OBSERVABILITY_TENANT_ID + ALPSTEIN_OBSERVABILITY_BUSINESS_ID (UUID).\n\nF.2.2: ERPNext tail — field dedupe + custom Lead fields — ALPSTEIN_ERPNEXT_LEAD_SYNC_ENABLED + erpnext_crm_api.\n\nT-N8N-IG-INGRESS: Instagram Meta webhook persists in backend, then dispatches here.",
                "height": 340,
                "width": 520,
                "color": 4,
            },
            "id": "e1800001-0000-4000-8000-000000000014",
            "name": "Sticky Note E1.8",
            "type": "n8n-nodes-base.stickyNote",
            "typeVersion": 1,
            "position": [40, 40],
        },
    ]

    connections = {
        "Telegram Trigger": {
            "main": [[{"node": "Normalize Telegram Incoming", "type": "main", "index": 0}]]
        },
        "Instagram Backend Event Webhook": {
            "main": [[{"node": "Normalize Instagram Incoming", "type": "main", "index": 0}]]
        },
        "Normalize Telegram Incoming": {
            "main": [[{"node": "Add Business Context", "type": "main", "index": 0}]]
        },
        "Normalize Instagram Incoming": {
            "main": [[{"node": "Add Business Context", "type": "main", "index": 0}]]
        },
        "Add Business Context": {
            "main": [[{"node": "POST Backend", "type": "main", "index": 0}]]
        },
        "POST Backend": {
            "main": [
                [
                    {
                        "node": "Shape Canonical Customer Reply",
                        "type": "main",
                        "index": 0,
                    },
                    {"node": "IF Notify Owner", "type": "main", "index": 0},
                    {
                        "node": "Prepare ERPNext Lead Payload",
                        "type": "main",
                        "index": 0,
                    },
                ]
            ],
            "error": [[{"node": "Format Channel Backend Error", "type": "main", "index": 0}]],
        },
        "Prepare ERPNext Lead Payload": {
            "main": [[{"node": "Search ERPNext Lead", "type": "main", "index": 0}]]
        },
        "Search ERPNext Lead": {
            "main": [[{"node": "Parse ERPNext Search", "type": "main", "index": 0}]]
        },
        "Parse ERPNext Search": {
            "main": [[{"node": "IF ERPNext Search OK", "type": "main", "index": 0}]]
        },
        "IF ERPNext Search OK": {
            "main": [
                [{"node": "IF ERPNext Lead Exists", "type": "main", "index": 0}],
                [{"node": "ERPNext Search Failed Logger", "type": "main", "index": 0}],
            ]
        },
        "IF ERPNext Lead Exists": {
            "main": [
                [{"node": "Prepare ERPNext Lead Update", "type": "main", "index": 0}],
                [{"node": "Prepare ERPNext Lead Create", "type": "main", "index": 0}],
            ]
        },
        "Prepare ERPNext Lead Update": {
            "main": [[{"node": "Update ERPNext Lead", "type": "main", "index": 0}]]
        },
        "Update ERPNext Lead": {
            "main": [[{"node": "ERPNext Result Logger", "type": "main", "index": 0}]]
        },
        "Prepare ERPNext Lead Create": {
            "main": [[{"node": "Create ERPNext Lead", "type": "main", "index": 0}]]
        },
        "Create ERPNext Lead": {
            "main": [[{"node": "ERPNext Result Logger", "type": "main", "index": 0}]]
        },
        "Shape Canonical Customer Reply": {
            "main": [
                [
                    {"node": "Route Reply Telegram", "type": "main", "index": 0},
                    {"node": "Route Reply Instagram", "type": "main", "index": 0},
                ]
            ]
        },
        "Format Channel Backend Error": {
            "main": [
                [
                    {"node": "Route Reply Telegram", "type": "main", "index": 0},
                    {"node": "Route Reply Instagram", "type": "main", "index": 0},
                ]
            ]
        },
        "Route Reply Telegram": {
            "main": [[{"node": "Telegram Send Message", "type": "main", "index": 0}]]
        },
        "Telegram Send Message": {
            "main": [[{"node": "Prepare Delivery PATCH", "type": "main", "index": 0}]]
        },
        "Route Reply Instagram": {
            "main": [[{"node": "Instagram Reply Disabled Logger", "type": "main", "index": 0}]]
        },
        "Prepare Delivery PATCH": {
            "main": [[{"node": "PATCH Delivery Outcome", "type": "main", "index": 0}]]
        },
        "IF Notify Owner": {
            "main": [[{"node": "Shape Owner Notification", "type": "main", "index": 0}]]
        },
        "Shape Owner Notification": {
            "main": [[{"node": "Telegram Owner Notify", "type": "main", "index": 0}]]
        },
    }

    workflow = {
        "id": "aYrRmAGKhP4TJbG9",
        "name": "alpstein-customer-ingress",
        "nodes": nodes,
        "connections": connections,
        "active": True,
        "settings": {"executionOrder": "v1"},
        "versionId": "f2.3-instagram-ingress-v2",
        "meta": {"templateCredsSetupCompleted": False},
        "tags": [
            {
                "name": "alpstein",
                "createdAt": "2026-05-28T00:00:00.000Z",
                "updatedAt": "2026-05-28T00:00:00.000Z",
                "id": "alpstein-tag",
            },
            {
                "name": "e2",
                "createdAt": "2026-05-28T00:00:00.000Z",
                "updatedAt": "2026-05-28T00:00:00.000Z",
                "id": "e2-tag",
            },
            {
                "name": "f2.1",
                "createdAt": "2026-05-29T00:00:00.000Z",
                "updatedAt": "2026-05-29T00:00:00.000Z",
                "id": "f21-tag",
            },
        ],
    }

    OUT.write_text(json.dumps(workflow, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {OUT} ({len(nodes)} nodes)")


if __name__ == "__main__":
    main()
