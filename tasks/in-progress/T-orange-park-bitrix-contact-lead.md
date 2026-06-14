# T-orange-park-bitrix-contact-lead

## Goal

Create or update an Orange Park Bitrix24 lead when the Telegram customer shares
their native contact payload.

## Scope

- Add a backend Bitrix24 adapter/service for Orange Park.
- Read `ORANGE_PARK_BITRIX_WEBHOOK_URL` from backend settings.
- Gate the integration by Orange Park, Telegram, native contact capture, complete
  contact data, and flow metadata.
- Normalize the phone, search by phone, update an existing lead, or create a new
  lead.
- Use standard Bitrix24 lead fields only.
- Build a bounded conversation context summary and latest-customer-message
  section.
- Store Bitrix lead id, action, and timestamp in inbound message metadata.
- Return create/update flags and keep owner notification disabled for this
  external CRM handoff.

## Requirements

- Source is Telegram and business is Orange Park.
- Do not create duplicate leads for the same phone.
- Do not create Bitrix leads on ordinary messages.
- Missing webhook configuration disables the integration safely.
- Keep tenant and business scoped database reads.
- Do not print, log, document, test-fixture, or commit the webhook URL.
- Do not add custom Bitrix24 fields without an existing approved mapping.

## Tests

- Create a new lead when phone search returns no lead.
- Update an existing lead found by phone.
- Missing webhook env disables Bitrix safely.
- Repeated phone uses update and does not create a duplicate.
- Only Orange Park native Telegram contact capture triggers Bitrix.
- Run a harmless live profile/current check after mocked tests pass.
- Run one controlled live create/update test and report only the lead id.

## Out Of Scope

- n8n workflow changes unless the normalized contact payload is insufficient.
- Custom Bitrix24 fields.
- Other businesses or channels.
- Refactoring the general lead pipeline.
- Committing or pushing changes.

## Implementation Result

- Added an Orange Park-only Bitrix24 backend service.
- Enabled the active Orange Park flow through migration `0027`.
- Used standard lead fields only:
  - `SOURCE_ID=OTHER`
  - `SOURCE_DESCRIPTION=Telegram / Orange Park Telegram Bot`
  - Telegram and handoff context in `COMMENTS`
- Added Compose pass-through for the existing environment secret.
- No n8n workflow changes were required.

## Verification

- Harmless Bitrix profile call passed.
- Full backend suite: `792 passed, 4 skipped`.
- Secret scan: clean.
- Live test:
  - first contact action: create
  - repeated phone action: update
  - same Bitrix lead id: `39001`
  - owner notification: false
