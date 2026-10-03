---
name: task-management
description: Track table-shaped work, row results, reservations, and duplicate checks with the Search Stack task_management tool. Use for coordinated progress, not for performing the external work or storing credentials.
---

# Task Management

Use only the exact MCP tool `task_management`. A Task is a table definition; a Record is one row. Do not use raw Elasticsearch, guessed tool names, or a local task copy. If a required tool/action is absent, or the connector validates it as another action, stop and refresh or reconnect the MCP before starting a new session; updating this Skill alone does not refresh tool schemas.

## Choose the operation

- `create_records`: record 1–500 facts already known to be complete; use a one-item batch for a single fact.
- `reserve_record`: claim work before an external side effect.
- `renew_reservation`: extend a live claim.
- `finish_record`: close reserved work as completed, failed, or uncertain.
- `resolve_record`: reconcile uncertain work after checking the external system.
- `check_duplicate`: advisory URL existence check; it never reserves work.
- Task and ordinary record actions: create, inspect, update, complete/cancel, or tombstone their resources.

Inspect the live tool schema for exact fields. Use [references/tool-contract.json](references/tool-contract.json) only to verify generated schema, defaults, or scopes. Consult [references/mcp-contract.md](references/mcp-contract.md) before using dedupe, leases, uncertain resolution, or terminal task actions.

## Rules

- Define only needed columns. Business keys and values remain under `record.values`, so common names such as `result`, `status`, `revision`, and `task_ref` are valid and never collide with system fields. Follow the live key schema's syntax and sensitive-data restrictions.
- In `create_records`, give every item its own permanently unique `request_id`. Inspect every ordered item result; batches may partially succeed. Retry the unchanged batch or only failed items, never rewrite successful items under new IDs. Prefer 100–200 items unless small records justify using the 500-item maximum.
- Add a write dedupe rule only when uniqueness matters; default to global unless uniqueness is intentionally per Task.
- Before any external side effect, call `reserve_record` and proceed only after `record_reserved`. Finish promptly and renew before a lease expires.
- Mark `failed` only when the effect definitely did not happen. If it may have happened, use `uncertain`, verify externally, then resolve it.
- `check_duplicate` takes `url`; add `task_ref` and/or `task_name` as AND conditions. It returns `exists` and is never permission to act.
- URL columns are resource URLs: path and query remain identity-bearing. Do not collapse them to website hosts.
- Every mutation needs a globally unique `request_id` that is never recycled; reuse it only for the identical retry. Existing-resource changes also need the current revision.
- A connector-side schema rejection does not authorize new per-item IDs or a substitute action. After refresh, retry the identical batch or only its unconfirmed items with their original IDs; if delivery was ambiguous, inspect current state first.
- Treat `conflict`, `busy`, `lease_lost`, and `uncertain` as reasons to inspect current state, not to retry blindly.
- Complete or cancel a Task only after reserved and uncertain Records are resolved. Deletion is a tombstone and does not erase completed dedupe facts.
- Keep credentials, sessions, raw transcripts, memory, and full website/account documents out of task records. This Skill tracks work; another authorized tool performs it.
