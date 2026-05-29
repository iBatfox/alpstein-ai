# T-ops-n8n-manual-update — Safe manual n8n update

## Goal

Safely update the personal Alpstein AI n8n environment while preserving recovery capability.

## Scope

- Analyze current Docker Compose configuration for n8n.
- Determine current n8n version, image source, container names, volume mappings, and database backend.
- Create recovery artifacts before update:
  - export all workflows;
  - export credentials if supported;
  - document active Docker volumes;
  - create git tag `pre-n8n-update-<date>`.
- Verify recovery capability before update.
- Run the n8n update using the actual repository/runtime structure.
- Run post-update checks.
- Generate an update report with rollback instructions.

## Requirements

- Personal environment only; no customer production traffic or live client dependencies.
- Preserve Docker volumes.
- Do not run `docker compose down -v`, `docker-compose down -v`, `docker volume rm`, or destructive cleanup commands.
- Stop and report if runtime topology or recovery capability is uncertain.
- Do not expose secrets from `.env`, n8n credentials, or workflow data.

## Tests / Verification

- Compose configuration validates.
- Workflows are exported before update.
- Credential export is attempted only if supported and non-secret handling is understood.
- Database backup procedure is documented or created.
- n8n container starts after update.
- UI endpoint is reachable.
- Workflows and credentials are present after update.
- Startup logs show no migration/startup errors.

## Out of Scope

- Workflow redesign or activation changes.
- Backend code changes.
- PostgreSQL schema changes.
- n8n volume deletion or reset.
- Committing code or pushing tags.
