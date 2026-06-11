# T-orange-park-legacy-webhook-fallback

## Goal

Make `POST /api/v1/webhook/message` work on production DB revision `0007`, where `flows` and later observability/replay tables do not exist.

## Scope

- Add a narrow legacy-compatible webhook fallback for missing `flows`.
- Keep current flow-based behavior unchanged when `flows` exists.
- Preserve tenant and business isolation by `tenant_id` and `business_id`.
- Add focused backend tests.
- Validate Orange Park webhook smoke.

## Requirements

- Do not run Alembic migrations.
- Do not create `flows` manually.
- Do not change n8n.
- Do not change Mini App.
- Do not add Bitrix.
- Do not commit or push.
- Catch only missing-table compatibility cases; do not hide unrelated DB errors.
- Log: `flows table unavailable; using legacy webhook flow fallback`.

## Validation

- Targeted backend tests.
- Orange Park webhook smoke sequence.
