#!/usr/bin/env python3
"""Generate e1_8_unified_customer_ingress_skeleton.json from canonical channel exports."""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "n8n/workflows/e1_8_unified_customer_ingress_skeleton.json"
WEBSITE_WF = REPO / "n8n/workflows/e1_6_workflow_website_chat_mvp_skeleton.json"

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
    },
  },
];"""

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
    website_code = next(
        n["parameters"]["jsCode"]
        for n in json.loads(WEBSITE_WF.read_text())["nodes"]
        if n["name"] == "Normalize Website Chat Incoming"
    )

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
            "e1800001-0000-4000-8000-000000000002",
            "Website Chat Webhook",
            "n8n-nodes-base.webhook",
            2,
            [0, 520],
            {
                "httpMethod": "POST",
                "path": "alpstein/unified-customer-ingress/website-chat/incoming",
                "responseMode": "responseNode",
                "options": {},
            },
            webhookId="alpstein-unified-website-chat-ingress",
            notesInFlow=True,
            notes="E1.8 INACTIVE: non-prod path. Production uses alpstein/website-chat/incoming.",
        ),
        node(
            "e1800001-0000-4000-8000-000000000003",
            "IF Website Chat Enabled",
            "n8n-nodes-base.if",
            2.2,
            [280, 520],
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
                            "id": "cond-website-chat-enabled",
                            "leftValue": "={{ $env.ALPSTEIN_WEBSITE_CHAT_ENABLED }}",
                            "rightValue": "true",
                            "operator": {"type": "string", "operation": "equals"},
                        }
                    ],
                    "combinator": "and",
                },
                "options": {},
            },
            notesInFlow=True,
            notes="E1.6.6 kill switch — Website branch only.",
        ),
        node(
            "e1800001-0000-4000-8000-000000000004",
            "Respond Website Chat Disabled",
            "n8n-nodes-base.respondToWebhook",
            1.1,
            [560, 420],
            {
                "respondWith": "json",
                "responseBody": "={{ { success: false, error: { code: 'WEBSITE_CHAT_DISABLED', message: 'Website chat is temporarily disabled.' } } }}",
                "options": {"responseCode": 503},
            },
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
            "e1800001-0000-4000-8000-000000000006",
            "Normalize Website Chat Incoming",
            "n8n-nodes-base.code",
            2,
            [560, 620],
            {"jsCode": website_code},
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
            "e1800001-0000-4000-8000-00000000000c",
            "Route Reply Website",
            "n8n-nodes-base.if",
            2.2,
            [1600, 360],
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
                            "id": "cond-channel-website",
                            "leftValue": "={{ $json.channel }}",
                            "rightValue": "website_chat",
                            "operator": {"type": "string", "operation": "equals"},
                        }
                    ],
                    "combinator": "and",
                },
                "options": {},
            },
        ),
        node(
            "e1800001-0000-4000-8000-00000000000d",
            "Route Error Website",
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
                            "id": "cond-channel-website-err",
                            "leftValue": "={{ $json.channel }}",
                            "rightValue": "website_chat",
                            "operator": {"type": "string", "operation": "equals"},
                        }
                    ],
                    "combinator": "and",
                },
                "options": {},
            },
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
            "e1800001-0000-4000-8000-00000000000f",
            "Respond Website Reply",
            "n8n-nodes-base.respondToWebhook",
            1.1,
            [1860, 360],
            {
                "respondWith": "json",
                "responseBody": "={{ $json }}",
                "options": {"responseCode": 200},
            },
        ),
        node(
            "e1800001-0000-4000-8000-000000000010",
            "Respond Website Error",
            "n8n-nodes-base.respondToWebhook",
            1.1,
            [1860, 520],
            {
                "respondWith": "json",
                "responseBody": "={{ $json }}",
                "options": {"responseCode": 502},
            },
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
        {
            "parameters": {
                "content": "## Unified customer ingress + E2 delivery PATCH\n\nTelegram + Website → POST Backend → channel delivery → PATCH delivery outcome.\n\nRequires ALPSTEIN_OBSERVABILITY_TENANT_ID + ALPSTEIN_OBSERVABILITY_BUSINESS_ID (UUID).",
                "height": 300,
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
        "Website Chat Webhook": {
            "main": [[{"node": "IF Website Chat Enabled", "type": "main", "index": 0}]]
        },
        "IF Website Chat Enabled": {
            "main": [
                [{"node": "Normalize Website Chat Incoming", "type": "main", "index": 0}],
                [{"node": "Respond Website Chat Disabled", "type": "main", "index": 0}],
            ]
        },
        "Normalize Telegram Incoming": {
            "main": [[{"node": "Add Business Context", "type": "main", "index": 0}]]
        },
        "Normalize Website Chat Incoming": {
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
                ]
            ],
            "error": [[{"node": "Format Channel Backend Error", "type": "main", "index": 0}]],
        },
        "Shape Canonical Customer Reply": {
            "main": [
                [
                    {"node": "Route Reply Telegram", "type": "main", "index": 0},
                    {"node": "Route Reply Website", "type": "main", "index": 0},
                ]
            ]
        },
        "Format Channel Backend Error": {
            "main": [
                [
                    {"node": "Route Reply Telegram", "type": "main", "index": 0},
                    {"node": "Route Error Website", "type": "main", "index": 0},
                ]
            ]
        },
        "Route Reply Telegram": {
            "main": [[{"node": "Telegram Send Message", "type": "main", "index": 0}]]
        },
        "Telegram Send Message": {
            "main": [[{"node": "Prepare Delivery PATCH", "type": "main", "index": 0}]]
        },
        "Route Reply Website": {
            "main": [[{"node": "Respond Website Reply", "type": "main", "index": 0}]]
        },
        "Respond Website Reply": {
            "main": [[{"node": "Prepare Delivery PATCH", "type": "main", "index": 0}]]
        },
        "Route Error Website": {
            "main": [[{"node": "Respond Website Error", "type": "main", "index": 0}]]
        },
        "Respond Website Error": {
            "main": [[{"node": "Prepare Delivery PATCH", "type": "main", "index": 0}]]
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
        "name": "alpstein-customer-ingress",
        "nodes": nodes,
        "connections": connections,
        "active": False,
        "settings": {"executionOrder": "v1"},
        "versionId": "e2-delivery-outcome-patch-v1",
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
        ],
    }

    OUT.write_text(json.dumps(workflow, indent=2) + "\n")
    print(f"Wrote {OUT} ({len(nodes)} nodes)")


if __name__ == "__main__":
    main()
