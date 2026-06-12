# T-orange-park-knowledge-first-behavior

## Goal

Make Orange Park Telegram assistant use loaded business documentation and retrieved knowledge before redirecting to manager handoff.

## Scope

- Orange Park behavior docs.
- Orange Park seed configuration.
- Orange Park seed tests.

## Requirements

- Answer stable documented facts from business context and tenant knowledge.
- Use manager handoff only for unstable/time-sensitive data such as exact price, exact availability, discounts, booking, active financing terms, and legal guarantees.
- Preserve Telegram MVP boundaries: no n8n changes, no Bitrix changes, no commits.
