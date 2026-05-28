# T-e3.3a — Adapter health model

**Status:** todo (blocked on E3.3 design approval)

## Goal

`AdapterMonitoringService` + `adapter_health_policy` deriving metrics from existing tables.

## Requirements

- No new tables
- Aggregates: message_traces, delivery_events, retry_attempts, dead_letter_events
- Channels: `telegram`, `website_chat`
- Env window + thresholds

## Design

[`docs/audits/e3-3-adapter-monitoring-design.md`](../../docs/audits/e3-3-adapter-monitoring-design.md) §3–4
