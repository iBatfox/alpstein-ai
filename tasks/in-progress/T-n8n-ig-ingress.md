# T-N8N-IG-INGRESS — Instagram DM → n8n unified customer ingress

## Goal

After Instagram DM is persisted in PostgreSQL via `/webhooks/meta`, dispatch a normalized event to n8n unified ingress so ERPNext Lead sync tail runs. No direct backend → ERPNext. No Instagram auto-reply.

## Scope

- Backend n8n webhook dispatch (kill switch)
- n8n Instagram webhook branch + normalize + ERPNext tail updates
- Instagram reply disabled logger
- ERPNext Lead fields: instagram_username, instagram_display_name (script)

## Out of scope

- ERPNext Communication history
- Instagram outbound send / AI auto-reply
- Telegram / Website regression changes beyond shared ERPNext duplicate guard

## Done when

- Real Instagram DM → PG message → n8n execution → ERPNext Lead upsert
- Kill switch disables n8n dispatch only
- Tests pass
