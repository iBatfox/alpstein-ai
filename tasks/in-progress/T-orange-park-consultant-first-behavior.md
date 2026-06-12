# T-orange-park-consultant-first-behavior

## Goal

Make the Orange Park Telegram assistant behave like a helpful consultant first, not a lead form.

## Scope

- Orange Park runtime language/contact helper behavior.
- Orange Park AI behavior seed/configuration.
- Orange Park business behavior docs.
- Focused backend tests.

## Requirements

- Latest customer message controls response language; default Ukrainian.
- Conversation history must not switch a Ukrainian/ambiguous latest message to Russian.
- Answer stable questions from business context and knowledge before collecting phone.
- Collect phone only for price, availability, discount, booking, viewing, financing, manager consultation, or after needs are understood.
- Never say a request was passed before phone, first name, and last name are collected.
- No n8n, Bitrix, commit, or push.
