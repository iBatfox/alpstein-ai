# T-orange-park-budget-contact-guard

## Goal

Ensure Orange Park Telegram budget, price, availability, and current-options questions use the native Telegram contact-button handoff instead of free AI wording or manual phone collection.

## Scope

- Audit the active compose PostgreSQL Orange Park configuration for stale manual-contact rules.
- Validate the assembled prompt for `Які є варіанти до 100000 грн?`.
- Add a deterministic Orange Park Telegram intent guard for budget, price, availability, and current-options questions.
- Return the exact approved Ukrainian reply and Telegram contact-button metadata.
- Keep Orange Park lead creation disabled.
- Run the Orange Park seed against the active compose database.
- Rebuild/restart and validate the live backend response.

## Requirements

- Reply:
  `Актуальні варіанти в межах бюджету підтвердить менеджер.`

  `Для зв'язку з менеджером, будь ласка, натисніть кнопку «📱 Поділитися номером».`
- `metadata.telegram_contact_request.needed = true`.
- `metadata.telegram_contact_request.button_text = "📱 Поділитися номером"`.
- `lead_created = false`.
- Do not ask the customer to type a phone number.
- Do not invent current options.
- Preserve tenant and channel isolation.

## Tests

- Unit tests for `до 100000`, `до 1600000`, `які є варіанти`, and `що є в наявності`.
- Active DB stale-string search.
- Final assembled-prompt stale-string search.
- Seed dry-run and normal seed.
- Live compose backend webhook smoke test.
- Full backend test suite.

## Out Of Scope

- Bitrix changes.
- Lead creation.
- Other businesses.
- n8n architecture changes.
- Commit or push.

## Validation Report

Validation date: 2026-06-12

### Root Cause

Two independent defects were present:

1. Previous host-side DB checks and seed commands used `ALPSTEIN_AI_DATABASE_URL` pointing to local PostgreSQL on `localhost:5432`. The live backend uses compose PostgreSQL at `postgres:5432`, exposed on host port `15433`. The two databases have different Orange Park tenant/business IDs, so the active compose database retained the old configuration.
2. Budget/current-options questions were not recognized by the deterministic Orange Park Telegram contact state machine. They fell through to AI, which invented apartment suitability instead of returning the native contact-button handoff.

The pre-fix live response incorrectly claimed that `100000 грн` might suit one- or two-room apartments and contained no contact-button metadata.

### Active Compose DB Stale Search

Before the corrected compose seed:

| Stale phrase | Matches | Locations |
| --- | ---: | --- |
| `If phone is already provided` | 3 | AI metadata, business description, business limitations |
| `If phone is missing` | 3 | AI metadata, business description, conversation style |
| `Будь ласка, залиште дані у такому форматі` | 3 | AI metadata, business description, conversation style |
| `Залиште, будь ласка, ваш номер телефону` | 4 | AI metadata, business description, conversation style, FAQ |
| `Ім'я:` | 3 | AI metadata, business description, conversation style |
| `Напишіть, будь ласка, номер телефону` | 2 | business description, conversation style |
| `Прізвище:` | 3 | AI metadata, business description, conversation style |
| `Телефон:` | 3 | AI metadata, business description, conversation style |

After the corrected compose seed, all eight phrases returned `0` matches.

The compose seed used:

- Tenant ID: `7b09f9ce-a1c6-4189-9ace-73e4e8176a3e`
- Business ID: `d14a1161-292c-4f1d-b0b2-2034f3e2e30d`

Both compose-target dry-run and normal seed completed successfully.

### Implementation

`backend/app/services/webhook_message_service.py` now classifies Orange Park Telegram budget, price, availability, and current-options messages before AI orchestration.

Covered examples:

- `до 100000`
- `до 1600000`
- `які є варіанти`
- `що є в наявності`

The deterministic path:

- returns the approved Ukrainian reply;
- sets Telegram contact-request metadata;
- skips AI generation;
- skips lead creation;
- remains scoped to `business_id=orange-park` and `channel=telegram`.

### Final Assembled Prompt Search

The prompt was assembled inside the live backend container against compose PostgreSQL for:

`Які є варіанти до 100000 грн?`

All eight stale strings returned `0` matches.

### Final Live Webhook JSON

```json
{
  "success": true,
  "data": {
    "reply_to_customer": "Актуальні варіанти в межах бюджету підтвердить менеджер.\n\nДля зв'язку з менеджером, будь ласка, натисніть кнопку «📱 Поділитися номером».",
    "lead_created": false,
    "lead_updated": false,
    "notify_owner": false,
    "metadata": {
      "telegram_contact_request": {
        "needed": true,
        "button_text": "📱 Поділитися номером"
      }
    }
  }
}
```

Persisted incoming-message metadata:

```json
{
  "orange_park_contact_collection": {
    "stage": "orange_park_telegram_native_contact",
    "intent": "budget_or_current_options_requires_manager",
    "missing_fields": ["telegram_contact"],
    "external_crm_stage": "disabled_stage_1",
    "telegram_contact_request": true
  }
}
```

No lead was created.

### Runtime Deployment

- Rebuilt only the `backend` compose image.
- Recreated only the `backend` service.
- Backend health check returned healthy.
- Live webhook returned HTTP 200.
- No n8n, Bitrix, Mini App, or other-business changes were made.

### Tests

- Focused intent/service tests: `6 passed`.
- Full backend suite: `784 passed, 4 skipped`.
- `git diff --check`: passed.

### Git Status

Modified:

- `backend/app/services/webhook_message_service.py`
- `backend/tests/test_webhook_message_service.py`

Untracked task/report:

- `tasks/in-progress/T-orange-park-budget-contact-guard.md`

Pre-existing unrelated untracked files remain untouched:

- `docs/interview/`
- `tasks/done/T-bcb-separate-ba-telegram-bot-plan.md`

No commit or push was performed.
