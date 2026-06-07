# Business Context Builder Flow Specification

## 1. Purpose

This document defines the interview lifecycle for Business Context Builder.

The flow collects structured business information and produces draft onboarding artifacts. It does not publish those artifacts to active AI assistants.

---

# 2. High-Level Lifecycle

```text
Create interview session
    ↓
Create first assistant question
    ↓
User answers
    ↓
Save user message
    ↓
Generate placeholder next question
    ↓
Save assistant message
    ↓
Repeat until required sections are collected
    ↓
Complete session
    ↓
Generate draft structured context
    ↓
Generate draft system prompt
    ↓
Save result
```

Future-only steps:

```text
Generate context file
    ↓
Attach file to CRM
    ↓
Export through n8n
    ↓
Publish to production assistant
```

Future-only steps must not run in the MVP.

---

# 3. Session States

Allowed states:

```text
created
in_progress
completed
archived
```

State meanings:

| State | Meaning |
|-------|---------|
| created | Session record exists but the interview has not meaningfully started. |
| in_progress | Interview is active and can accept user messages. |
| completed | Required sections were collected and a draft result may be generated. |
| archived | Session is retained but no longer active. |

State transitions:

```text
created → in_progress → completed → archived
created → archived
in_progress → archived
```

The MVP does not define reopening completed sessions.

---

# 4. Full Interview Lifecycle

## Step 1: Start Session

Caller creates a session for a tenant and business.

System behavior:

- validate `tenant_id`;
- validate `business_id`;
- create session;
- set `status` to `in_progress`;
- set `current_step` to the first interview section;
- create first assistant message.

MVP assistant message is static placeholder text.

---

## Step 2: Send User Message

Caller sends a user answer to an active session.

System behavior:

- verify session exists;
- verify session belongs to `tenant_id` and `business_id`;
- reject completed or archived sessions;
- save the user message;
- update progress for `current_step`;
- generate the next placeholder assistant question;
- save the assistant message;
- return the saved messages and session state.

---

## Step 3: Continue Interview

The message cycle repeats until required sections are collected.

```text
assistant question → user answer → saved messages → next step
```

MVP logic may use deterministic step ordering and static question templates.

---

## Step 4: Complete Session

Caller requests completion.

System behavior:

- verify session exists;
- verify tenant and business scope;
- verify required sections are present or accept MVP placeholder completion rules;
- set `status` to `completed`;
- set `completed_at`;
- generate `structured_context`;
- generate `generated_prompt`;
- create one result record.

Completing a session must not publish data to active assistants.

---

## Step 5: Retrieve Contexts

Caller lists saved draft contexts.

System behavior:

- require tenant scope;
- filter by `tenant_id`;
- filter by `business_id` when provided or required by caller context;
- return draft result summaries.

No production assistant data is included.

---

# 5. Message Flow

```text
POST /sessions
    ↓
assistant message saved
    ↓
POST /sessions/{session_id}/messages
    ↓
user message saved
    ↓
placeholder progress update
    ↓
assistant message saved
    ↓
response returned
```

Message roles:

```text
assistant
user
system
```

MVP should primarily use:

```text
assistant
user
```

`system` is reserved for internal lifecycle notes if needed by a later implementation.

---

# 6. Required Interview Sections

The interview should collect:

- company information;
- business description;
- AI assistant goals;
- services;
- target customers;
- common questions;
- lead qualification;
- communication style;
- restrictions and handoff rules.

These sections are the minimum structure for `structured_context`.

---

# 7. Interview Section Details

## Company Information

Collect:

- company name;
- website;
- industry;
- country;
- languages.

## Business Description

Collect:

- what the company does;
- main products;
- main services;
- unique value proposition.

## AI Assistant Goals

Collect expected assistant use:

- lead generation;
- customer support;
- sales;
- appointment booking;
- internal assistant.

## Services

For each service collect:

- service name;
- description;
- pricing information;
- restrictions.

## Target Customers

Collect:

- customer type;
- pain points;
- buying motivations.

## Common Questions

Collect:

- FAQ;
- objections;
- common requests.

## Lead Qualification

Collect:

- required fields;
- qualification rules;
- handoff criteria.

Example fields:

```text
name
phone
email
budget
timeline
requested_service
```

## Communication Style

Collect:

- tone;
- formality;
- answer length;
- preferred language.

## Restrictions

Collect:

- forbidden actions;
- unsupported promises;
- escalation conditions;
- human handoff rules.

---

# 8. Placeholder Interview Logic

The MVP must not call OpenAI or any AI provider.

Placeholder rules:

- ask one predefined question per step;
- store every user message;
- store every assistant placeholder response;
- move `current_step` deterministically;
- allow completion only through the completion endpoint;
- generate a simple placeholder `structured_context`;
- generate a simple placeholder `generated_prompt`.

Example first question:

```text
Hello. I will help you create a draft Business Context. What is the name of your company?
```

---

# 9. Completion Rules

Target completion requires all required sections to be collected.

For the MVP placeholder implementation, completion may be allowed when:

- the session is `in_progress`;
- at least one user message exists;
- the completion endpoint is explicitly called.

Future AI interview service may enforce stricter per-section completeness.

Completion must create a result only once per session. If a result already exists, the backend should return the existing result or a documented conflict response.

---

# 10. Result Generation

On completion, the backend creates:

- `structured_context` as JSONB;
- `generated_prompt` as TEXT;
- result record in `business_context_builder.results`.

The generated result is a draft and must not be used automatically by production assistants.

The generated prompt must remain subordinate to Alpstein AI platform safety rules. Tenant-provided information must not override core system prompt policy.

---

# 11. Future Context File Flow

Future versions may generate:

```text
business_context.md
business_context.txt
```

Future file flow:

```text
completed result
    ↓
generate context file
    ↓
store file
    ↓
save context_file_path / context_file_url
```

MVP limitation:

- no file generation;
- no file storage;
- no file URL returned except reserved nullable fields.

---

# 12. Future CRM Attachment Flow

Future versions may attach generated context files to a CRM customer record.

Future CRM flow:

```text
completed result
    ↓
context file generated
    ↓
operator chooses CRM attachment
    ↓
CRM upload
    ↓
CRM file reference saved
```

MVP limitation:

- no CRM calls;
- no automatic CRM attachment;
- no synchronization.

---

# 13. Future Publish-To-Assistant Flow

Future versions may support explicit publication into production assistant configuration.

Future publish flow:

```text
completed draft result
    ↓
operator review
    ↓
explicit publish action
    ↓
validation against platform safety rules
    ↓
controlled update to production assistant configuration
```

MVP limitation:

- no publish endpoint;
- no writes to production assistant tables;
- no automatic assistant update;
- no prompt template modification.

---

# 14. Future n8n Export Flow

Future versions may allow n8n to export completed draft contexts after explicit backend approval.

MVP limitation:

- no n8n export;
- no n8n trigger on completion;
- no n8n direct PostgreSQL write;
- no workflow side effects.

---

# 15. Future AI Interview Service

Future versions may replace placeholder logic with an AI interview service.

Future AI rules:

- AI provider calls must go through AI Gateway Service;
- prompt construction must use Prompt Builder Service;
- platform safety rules remain non-overridable;
- AI must not write to PostgreSQL directly;
- backend service validates and persists AI outputs.

---

# 16. Safety Rules

- Business Context Builder data is draft-only.
- Always enforce `tenant_id` and `business_id` scope.
- Never modify active AI assistant business contexts from this module.
- Never write Business Context Builder data into production assistant tables.
- Never publish automatically.
- Never call n8n, CRM, Telegram, or OpenAI in the MVP.
- Publishing requires a separate explicit workflow and separate spec.

---

# 17. Related Specifications

- [business-context-builder-mvp.md](business-context-builder-mvp.md)
- [business-context-builder-database.md](business-context-builder-database.md)
- [business-context-builder-api.md](business-context-builder-api.md)
- [business-context-builder-architecture.md](business-context-builder-architecture.md)
