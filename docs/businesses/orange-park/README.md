# Orange Park Dialog Engine v3

The six active Orange Park knowledge sources are:

1. `01_business_profile`
2. `02_sales_presentation`
3. `03_sales_scenarios`
4. `04_purchase_rules`
5. `05_apartment_catalog`
6. `06_commercial_catalog`

The backend seed writes these sources with `dialog_engine_version` set to
`orange_park_v3` and deactivates older Orange Park knowledge rows.

These six documents are the only active Orange Park behavior and knowledge
sources. Old FAQ, pricing, AI-policy, contact-form, and conversation-style
documents are historical and are not runtime sources. Do not restore them to
the active seed.

Runtime responsibilities:

- backend owns dialog state and Bitrix contact synchronization;
- n8n normalizes Telegram input and delivers backend responses;
- secrets remain in environment variables or external credential storage;
- all database records remain scoped by `tenant_id` and `business_id`.

Dialog Engine v3 scenarios consume explicit `intent`, `stage`, and state fields
from the active turn. They must not infer active dialog state from stale
history. Short confirmations and numeric replies advance only a compatible
active stage.

The platform end-to-end message trace remains active for deterministic and AI
paths across all businesses and channels. Langfuse observes those paths in
every environment when its credentials are configured; environment or
feature-flag values do not disable it. Langfuse is separate from `PromptRun`,
and deterministic replies must not create a `PromptRun` solely for tracing.

`00_intake` contains the original client input and is not active assistant
behavior. Catalog files are extension points and contain no live availability,
prices, photos, or gallery data.
