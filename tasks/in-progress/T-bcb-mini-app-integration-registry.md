# T — BCB Mini App Read-Only Integration Registry

## Goal

Show owner-managed connected integrations in the Business Context Builder Mini App after Telegram access verification.

## Scope

- Add BCB schema integration registry table.
- Add `alpstein_business_id` to Mini App allowed users.
- Return verified user's business id and integrations from `verify-access`.
- Render integration cards/details in the Mini App without edit/control actions.

## Restrictions

- Do not modify n8n workflows.
- Do not modify assistant runtime, Telegram webhook, or Instagram webhook logic.
- Do not add external foreign keys.
- Do not trust frontend-supplied business ids.
- Stop before commit.
