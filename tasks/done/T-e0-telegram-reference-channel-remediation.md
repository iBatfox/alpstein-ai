# T-e0 — Telegram reference channel remediation

**Status:** done  
**Date closed:** 2026-05-28  
**Audit:** [`docs/audits/e0-telegram-reference-channel-remediation-2026-05-28.md`](../docs/audits/e0-telegram-reference-channel-remediation-2026-05-28.md)

## Goal

Close E0 blockers: portable compose n8n owns Telegram ingress; full path with real n8n execution IDs.

## Results

| Blocker | Result |
|---------|--------|
| E0-R1 compose `up n8n` | **Open** — `ContainerConfig`; `docker run` workaround documented |
| E0-R2 portable Telegram Trigger E2E | **Closed** — exec **222**, HTTPS inject **200** |
| E0-R3 password discipline | **Closed** (prior continuation) |
| E0-R4 Langfuse on compose | **Open** — backend not recreated; metadata trace empty |
| E0-R5 volume / dual owner | **Closed** — legacy stopped; single mount |
| E0-R6 host :8010 | **Open** for legacy path — portable owns smoke |

**Verdict:** **PASS WITH WARNINGS**  
**Telegram reference channel:** **YES WITH WARNINGS**

## Acceptance checklist

- [x] Portable n8n owns Telegram webhook during smoke (`getWebhookInfo` → `n8n.alpstein-ai.ch`, upstream `alpstein_n8n_compose:15679`)
- [x] n8n execution ID **222** recorded
- [x] POST Backend + AI reply in execution data
- [x] Owner notify branch executed (`notify_owner: true`)
- [ ] Customer Telegram handset delivery — **synthetic chat** (`chat not found`) — WARN
- [x] Backend healthy before/after
- [x] `prompt_runs` **e426d4bc-b91e-4d4d-872c-2bcf2b32cf3a**
- [x] G-EXP-2 PASS
- [x] Workflow deactivated post-smoke (`active=0`)

## Evidence

- Execution **222** · prompt_run `e426d4bc-b91e-4d4d-872c-2bcf2b32cf3a` · intent `social_greeting`
- Workflow `2lMuaSWD1XFOXLEK` deactivated after test
