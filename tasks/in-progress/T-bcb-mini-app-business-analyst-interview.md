# T — BCB Mini App Business Analyst Interview Documents

## Goal

Turn the Mini App Interview tab into a verified Business Analyst Interview that stores answers, generates deterministic markdown documents, and lists/views saved documents.

## Scope

- Add Mini App interview endpoints under the existing Telegram BCB bridge.
- Store interview state and generated markdown under `/opt/alpstein-ai/docs/interview/{alpstein_business_id}/`.
- Derive business scope only from the verified Telegram allowlist record.
- Update the Mini App interview UI to show questions, generation, saved documents, and document view.

## Restrictions

- No OpenAI integration.
- No n8n workflow changes.
- No assistant runtime, prompt builder, or channel webhook changes.
- No frontend-selected file paths or business IDs.
- Stop before commit.
