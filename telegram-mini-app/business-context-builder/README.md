# Business Context Builder Telegram Mini App

Static design-first prototype for the future Business Context Builder user
experience with backend Telegram access verification.

The production default is fail-closed. On load, the app sends Telegram WebApp
`initData` to the backend verification endpoint and only shows the UI when the
validated Telegram user ID exists in the backend allowlist with `active` status.
Local mock mode is available only when `api_mode=mock` is explicitly set.
On public hostnames, mock mode is ignored and Telegram verification is still
required.

The UI still uses mock data and local click state after access is granted. It
renders read-only integration registry data from the access response. It does
not write Business Context data, change assistant configuration, alter prompts,
control workflows, or trigger integrations.

## Files

- `index.html` — prototype shell and screens.
- `styles.css` — Swiss SaaS mobile-first visual styling.
- `src/app.js` — access verification, local prototype navigation, and wizard state.
- `src/apiClient.js` — legacy API adapter retained for rollback compatibility;
  the current prototype UI does not import it.

## Screens

- Login
- Bots dashboard
- Business Context Builder
- Interview wizard
- Bot settings

## Local Run

From this directory:

```bash
python3 -m http.server 5174
```

Open:

```text
http://127.0.0.1:5174/?api_mode=mock
```

Without `api_mode=mock`, browser preview shows the access-denied screen because
Telegram `initData` is unavailable outside Telegram.

Mock mode is accepted only on `localhost` or `127.0.0.1`.

## Owner-Managed Access

Users cannot self-register. The owner/admin adds allowed users directly in the
backend database for now:

```sql
INSERT INTO business_context_builder.mini_app_allowed_users (
  id,
  telegram_user_id,
  display_name,
  company_name,
  alpstein_business_id,
  status,
  notes
) VALUES (
  '<generated-uuid>',
  123456789,
  'Customer Name',
  'Customer Company',
  'alpstein-ai',
  'active',
  'Added by owner'
);
```

Set `status` to `disabled` to block a previously allowed user.

Connected channels are managed in:

```text
business_context_builder.business_integrations
```

The Mini App displays these rows as read-only channel cards scoped by the
verified user's `alpstein_business_id`.

## Rollback

The previous Mini App was copied to:

```text
telegram-mini-app/business-context-builder-legacy-backup/
```

To rollback the source tree, copy the backed-up files from that directory back
into:

```text
telegram-mini-app/business-context-builder/
```

No backend, nginx, Docker, database, workflow, prompt builder, or assistant
logic changes are part of this prototype.
