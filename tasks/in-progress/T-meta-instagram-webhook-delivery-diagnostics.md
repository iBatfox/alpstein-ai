# T-meta-instagram-webhook-delivery-diagnostics

## Goal

Diagnose Meta to Instagram webhook delivery only.

## Scope

- Check Meta app webhook configuration against the expected Instagram callback URL.
- Check Instagram account/page webhook subscriptions and required fields/events.
- Check token validity and permissions using safe diagnostics only.
- Separate webhook URL mismatch, missing subscription, invalid/expired token, permission/app mode issue, and Instagram account/page connection issue.

## Requirements

- Do not modify backend code.
- Do not modify Telegram flow.
- Do not modify AI orchestration.
- Do not modify n8n workflows except read/export for diagnostics.
- Do not print secrets.

## Tests

- Run read-only local config and runtime checks.
- Run read-only Graph API diagnostics if tokens are available.
- Provide exact shell commands and Meta Developer Console UI steps.

## Out Of Scope

- Backend code changes.
- n8n workflow edits.
- Telegram or AI changes.
- Meta app mutation unless explicitly requested later.
