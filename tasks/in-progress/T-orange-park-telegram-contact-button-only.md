# T-orange-park-telegram-contact-button-only

## Goal

Make the native Telegram contact button the only phone collection method for Orange Park Telegram MVP.

## Scope

- `business_id=orange-park`
- `channel=telegram`
- Backend Orange Park contact collection wording and metadata.
- Orange Park Telegram workflow export/runtime only if backend metadata shape changes.

## Requirements

- When contact collection is required, backend requests Telegram contact button metadata.
- Reply before button:
  `Для зв'язку з менеджером, будь ласка, натисніть кнопку «📱 Поділитися номером».`
- Do not use old Ukrainian/Russian manual contact forms while the Telegram contact button is available.
- After contact share, reply:
  `Дякуємо. Запит передано менеджеру. Очікуйте дзвінок.`
- Do not ask for phone again after Telegram contact is received.
- Do not ask for first/last name again when Telegram provided them.
- If Telegram omits name fields, ask only for the missing name fields.
- Keep Bitrix lead creation disabled unless explicitly enabled by flow config.
- Do not affect other businesses or channels.

## Validation

- Backend tests pass.
- Orange Park Telegram workflow keeps contact button behavior.
- Live Telegram path: `Давай` -> button -> contact share -> final acknowledgement.

## Implementation Notes

- Backend deployed in `alpstein_backend` with Orange Park Telegram button-only contact collection.
- Synthetic live-backend validation passed:
  - `Давай` returns Telegram contact request metadata and `lead_created=false`.
  - Manually typed phone still returns Telegram contact request metadata and `lead_created=false`.
  - Normalized Telegram contact payload returns `Дякуємо. Запит передано менеджеру. Очікуйте дзвінок.` and `lead_created=false`.
- Full backend suite passed: `781 passed, 4 skipped`.
- Manual Telegram UI validation still requires pressing the contact button from a Telegram client.
