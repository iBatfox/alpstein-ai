# T-orange-park-response-quality-seed

## Goal

Improve Orange Park Telegram MVP seeded AI behavior and documentation so future seeded Orange Park configuration handles language, repetition, and response style issues found during testing.

## Scope

- Update Orange Park documentation under `docs/businesses/orange-park/`.
- Update `backend/app/seed/orange_park_configuration.py`.
- Update `backend/tests/test_orange_park_configuration_seed.py`.
- Validate with the Orange Park seed test and dry-run script.

## Requirements

- Telegram `/start` and first greeting must be Ukrainian by default.
- After a customer message, mirror the customer's language: Ukrainian customer gets Ukrainian replies, Russian customer gets Russian replies.
- Never output English unless the customer explicitly writes in English.
- Never mix languages in the same sentence and avoid hybrid words such as `hesitуйте`.
- Do not repeat location, apartment types, or other facts already provided in the current conversation unless the customer asks again.
- Use conversation history to avoid repeating the same answer.
- Answer the immediate question first, then ask only one useful qualification question.
- Keep Telegram replies concise.
- Avoid overusing manager-confirmation language; give useful stable context first.
- For unstable topics, say the manager will confirm current details while still giving safe general context.
- After collecting phone number, acknowledge and close naturally.
- Short handoff intent such as `давай`, `з'єднуй`, `так`, and `ок` must ask only for the customer's phone when phone is missing.
- Contact requests such as `номер телефону`, `дай контакти`, `дай дані`, and `номер` must not invent official Orange Park contacts; if no official contact exists in the current business context, ask the customer to leave their phone.
- Avoid repeating the same refusal or manager-confirmation loop.
- Do not mention Bitrix, CRM, or lead creation.

## Out Of Scope

- No platform/global prompt changes unless absolutely necessary.
- No changes to other businesses.
- No n8n changes.
- No Mini App changes.
- No Bitrix integration.
- No secrets.
- No commit or push.

## Validation

- `cd backend && .venv/bin/pytest tests/test_orange_park_configuration_seed.py`
- `cd backend && set -a; . ../.env; set +a; .venv/bin/python scripts/seed_orange_park_configuration.py --dry-run`
- `cd backend && .venv/bin/pytest tests/test_orange_park_configuration_seed.py tests/test_flow_service.py tests/test_webhook_message_service.py`
- `cd backend && set -a; . ../.env; set +a; .venv/bin/python scripts/seed_orange_park_configuration.py`
