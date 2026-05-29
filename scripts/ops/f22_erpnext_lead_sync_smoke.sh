#!/usr/bin/env bash
# F.2.2 — ERPNext Lead sync live smoke (operator). No secrets printed.
set -euo pipefail

N8N_URL="${N8N_URL:-http://127.0.0.1:15679}"
WEBHOOK_WEBSITE="${N8N_URL}/webhook/alpstein/unified-customer-ingress/website-chat/incoming"
WEBHOOK_TG="${N8N_URL}/webhook/alpstein-telegram-customer-trigger-unified-inactive/webhook"
TG_SECRET="${TG_WEBHOOK_SECRET:-aYrRmAGKhP4TJbG9_e1800001-0000-4000-8000-000000000001}"
BUSINESS_ID="${ALPSTEIN_TELEGRAM_BUSINESS_ID:-alpstein_ai_demo_001}"

if [[ ! -f /etc/alpstein/erpnext-n8n-api.env ]]; then
  echo "MISSING /etc/alpstein/erpnext-n8n-api.env" >&2
  exit 1
fi
# shellcheck disable=SC1091
source /etc/alpstein/erpnext-n8n-api.env

erpnext_leads() {
  local filters="$1"
  curl -sS -G -H "Authorization: token ${ERPNEXT_API_KEY}:${ERPNEXT_API_SECRET}" \
    --data-urlencode "filters=${filters}" \
    --data-urlencode 'fields=["name","lead_name","alpstein_chat_id","alpstein_external_user_id","conversation_count","first_touch_source","telegram_username","telegram_language_code","utm_source"]' \
    --data-urlencode "limit_page_length=50" \
    "https://crm.alpstein-ai.ch/api/resource/Lead"
}

count_leads_for_chat() {
  local chat_id="$1"
  erpnext_leads "[[\"alpstein_chat_id\",\"=\",\"${chat_id}\"],[\"alpstein_business_id\",\"=\",\"${BUSINESS_ID}\"]]" \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('data',[])))"
}

post_telegram() {
  local user_id="$1" chat_id="$2" text="$3" username="${4:-}" lang="${5:-en}"
  local payload
  payload=$(python3 - <<PY
import json, time
print(json.dumps({
  "update_id": int(time.time()),
  "message": {
    "message_id": int(time.time()) % 100000,
    "date": int(time.time()),
    "chat": {"id": ${chat_id}, "type": "private"},
    "from": {
      "id": ${user_id},
      "is_bot": False,
      "first_name": "F22",
      "username": "${username}" or None,
      "language_code": "${lang}",
    },
    "text": "${text}",
  },
}))
PY
)
  curl -sS -o /tmp/f22-tg-resp.json -w '%{http_code}' \
    -H "Content-Type: application/json" \
    -H "X-Telegram-Bot-Api-Secret-Token: ${TG_SECRET}" \
    -d "${payload}" "${WEBHOOK_TG}"
}

post_website() {
  local visitor="$1" session="$2" utm_source="${3:-}"
  curl -sS -o /tmp/f22-web-resp.json -w '%{http_code}' \
    -H "Content-Type: application/json" \
    -d "{
      \"business_id\": \"${BUSINESS_ID}\",
      \"visitor_id\": \"${visitor}\",
      \"session_id\": \"${session}\",
      \"text\": \"F22 website smoke\",
      \"utm_source\": \"${utm_source}\",
      \"utm_medium\": \"cpc\",
      \"utm_campaign\": \"f22_test\",
      \"page_url\": \"https://alpstein-ai.ch/landing?utm_source=${utm_source}\"
    }" "${WEBHOOK_WEBSITE}"
}

echo "=== F.2.2 smoke business_id=${BUSINESS_ID} ==="
TS=$(date +%s)
TG_USER=$((9000000000 + TS % 999999))
TG_CHAT=$((8000000000 + TS % 999999))
WEB_VIS="f22-visitor-${TS}"

echo -n "Test website (sync flag as container env): "
WEB_CODE=$(post_website "${WEB_VIS}" "f22-session-${TS}" "google")
echo "http=${WEB_CODE}"
python3 -c "import json; d=json.load(open('/tmp/f22-web-resp.json')); print('  success=', d.get('success'))"

echo -n "Test telegram inject: "
TG_CODE=$(post_telegram "${TG_USER}" "${TG_CHAT}" "F22 telegram smoke" "f22user_${TS}" "de")
echo "http=${TG_CODE}"

sleep 3
echo -n "Lead count for telegram chat_id=${TG_CHAT}: "
count_leads_for_chat "${TG_CHAT}"

echo -n "Second telegram (dedupe): "
post_telegram "${TG_USER}" "${TG_CHAT}" "F22 telegram repeat" "f22user_${TS}" "de" >/dev/null
echo "ok"
sleep 3
echo -n "Lead count after repeat: "
count_leads_for_chat "${TG_CHAT}"

LEADS_JSON=$(erpnext_leads "[[\"alpstein_chat_id\",\"=\",\"${TG_CHAT}\"],[\"alpstein_business_id\",\"=\",\"${BUSINESS_ID}\"]]")
echo "${LEADS_JSON}" | python3 -c "
import json,sys
d=json.load(sys.stdin)
for row in d.get('data',[]):
  print('  lead_id=', row.get('name'))
  print('  conversation_count=', row.get('conversation_count'))
  print('  telegram_username=', row.get('telegram_username'))
  print('  telegram_language_code=', row.get('telegram_language_code'))
"

WEB_VIS2="f22-visitor-web-${TS}"
post_website "${WEB_VIS2}" "f22-session-web-${TS}" "facebook" >/dev/null
sleep 3
WEB_LEADS=$(erpnext_leads "[[\"alpstein_chat_id\",\"=\",\"${WEB_VIS2}\"],[\"alpstein_business_id\",\"=\",\"${BUSINESS_ID}\"]]")
echo "${WEB_LEADS}" | python3 -c "
import json,sys
d=json.load(sys.stdin)
rows=d.get('data',[])
print('Website leads:', len(rows))
if rows:
  r=rows[0]
  print('  lead_id=', r.get('name'))
  print('  first_touch_source=', r.get('first_touch_source'))
"

echo "Done. Check n8n executions for workflow aYrRmAGKhP4TJbG9"
