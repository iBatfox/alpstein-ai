# Business Context Builder Telegram Mini App

Static design-first prototype for the future Business Context Builder user
experience.

This UI is intentionally frontend-only. It uses mock data and local click state
only. It does not call backend APIs, write to the database, change assistant
configuration, alter prompts, or trigger integrations.

## Files

- `index.html` — prototype shell and screens.
- `styles.css` — Swiss SaaS mobile-first visual styling.
- `src/app.js` — local prototype navigation and wizard state.
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
http://127.0.0.1:5174/
```

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
