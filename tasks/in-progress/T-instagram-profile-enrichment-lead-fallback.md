# T-instagram-profile-enrichment-lead-fallback — Instagram Lead profile enrichment fallback

## Goal

Diagnose and fix why Instagram sender `800712929645409` created an ERPNext Lead with fallback name instead of profile data.

## Scope

- Trace backend logs, PostgreSQL message/customer data, n8n execution data, and ERPNext Lead payload for sender `800712929645409`.
- Add safe backend logs for Instagram profile enrichment:
  - `instagram_profile_enrichment_started`
  - `instagram_profile_enrichment_succeeded`
  - `instagram_profile_enrichment_failed`
- Add a retry/backfill script that fetches an Instagram profile for a sender id and updates an ERPNext Lead only when profile data is available.
- Keep fallback behavior when Meta does not provide a profile.
- Ensure null profile data does not overwrite existing non-empty Lead profile fields.
- Add or update focused tests.

## Rules

- Do not change UI, ERPNext conversation history, Telegram, AI logic, or lead dedupe.
- Do not create a new workflow.
- Do not manually fix only one Lead without identifying the root cause.
- Do not log tokens or secrets.
- Stop before commit.

## Validation

- Verify the exact n8n execution and ERPNext Lead payload for sender `800712929645409`.
- Verify direct Instagram profile retry result.
- Run focused backend/n8n tests.
- If Meta returns profile data, update Lead `CRM-LEAD-2026-00017`; otherwise report the exact Meta limitation/error.
