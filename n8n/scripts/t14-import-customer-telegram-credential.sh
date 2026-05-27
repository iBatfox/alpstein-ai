#!/usr/bin/env bash
# T14.2 — Import customer Telegram credential into n8n (token never printed).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${ROOT}/.env.telegram.customer"
CONTAINER="${N8N_CONTAINER:-alpstein_n8n}"
CRED_PREFIX="${TELEGRAM_CUSTOMER_CRED_PREFIX:-telegram_customer}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "MISSING_ENV_FILE=${ENV_FILE}" >&2
  echo "Copy n8n/.env.telegram.customer.example and set TELEGRAM_CUSTOMER_BOT_TOKEN." >&2
  exit 1
fi

# shellcheck disable=SC1090
source "${ENV_FILE}"

if [[ -z "${TELEGRAM_CUSTOMER_BOT_TOKEN:-}" ]]; then
  echo "MISSING_TELEGRAM_CUSTOMER_BOT_TOKEN" >&2
  exit 1
fi

BUSINESS_ID="${TELEGRAM_CUSTOMER_BUSINESS_EXTERNAL_ID:-demo_barbershop_001}"
CRED_NAME="${CRED_PREFIX}_${BUSINESS_ID}"

IMPORT_JSON="$(mktemp)"
trap 'rm -f "${IMPORT_JSON}"' EXIT

python3 - <<'PY' "${IMPORT_JSON}" "${CRED_NAME}" "${TELEGRAM_CUSTOMER_BOT_TOKEN}"
import json, sys
out, name, token = sys.argv[1], sys.argv[2], sys.argv[3]
payload = [{
    "name": name,
    "type": "telegramApi",
    "data": {"accessToken": token},
}]
with open(out, "w", encoding="utf-8") as f:
    json.dump(payload, f)
PY

docker cp "${IMPORT_JSON}" "${CONTAINER}:/tmp/t14-customer-cred.json"
docker exec "${CONTAINER}" n8n import:credentials --input=/tmp/t14-customer-cred.json
docker exec "${CONTAINER}" rm -f /tmp/t14-customer-cred.json

echo "IMPORT_OK credential_name=${CRED_NAME}"
