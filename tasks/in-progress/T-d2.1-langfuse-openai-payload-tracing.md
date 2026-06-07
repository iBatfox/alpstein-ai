# T-d2.1 — Langfuse OpenAI payload tracing

## Goal

Improve backend Langfuse tracing so full OpenAI `messages` payload is visible in a generation input and long prompt/context values are not stored in metadata attributes.

## Scope

- Find the assembled prompt and OpenAI request path.
- Keep Langfuse metadata short:
  - `business_id`
  - `channel`
  - `user_external_id` when available
  - `conversation_id`
  - `prompt_version` when available
- Record full OpenAI `messages` payload in Langfuse generation input.
- Record model response in Langfuse generation output.
- Add backend diagnostic log with:
  - `channel`
  - `business_id`
  - `operator_business_context_length`
  - first 500 chars of `operator_business_context`
  - whether assembled prompt contains `linkedin.com/in/ibatfox`
  - whether assembled prompt contains `instagram.com/alpstein_ai`

## Tests

- Langfuse span/trace metadata does not include long `operator_business_context` or `assembled_prompt`.
- Langfuse generation input includes full OpenAI `messages` payload.
- Diagnostic prompt source log reports marker presence and operator context preview.

## Out Of Scope

- Do not change AI behavior.
- Do not change prompt builder ordering or content.
- Do not change Instagram or Telegram send paths.
- Do not change n8n workflows.
- Do not add new product features.
