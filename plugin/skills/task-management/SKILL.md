---
name: task-management
description: Track table-shaped work, row results, reservations, and duplicate checks with the Search Stack task_read, task_write, and task_check_duplicate tools. Use for coordinated progress, not for performing the external work or storing credentials.
---

# Task Management

Use only the exact MCP tools `task_read`, `task_write`, and `task_check_duplicate`. `task_management` is an internal Workflow ID whose former public tool name is retired; never call it. If it appears in the current tool list, or a read-only call is reported as user-cancelled without an explicit user rejection, the connector or session has stale schema or annotations. Stop without retrying or substituting another tool, refresh or reconnect the MCP, verify the exact current tools, and start a new session. Updating this Skill alone does not refresh tool schemas. A Task is a table definition; a Record is one row. Do not use raw Elasticsearch, guessed tool names, or a local task copy.

## Choose the operation

- `task_check_duplicate`: advisory URL existence check; pass `url` and optional `task_ref` / `task_name` directly, with no `action`.
- `task_read`: inspect Tasks or Records with `get_task`, `list_tasks`, `get_record`, or `list_records`.
- `task_write` with `create_records`: import 1–500 facts with a known outcome; use a one-item batch for a single fact. Omitted `outcome` means `completed`.
- `task_write` with `reserve_record`: claim work before an external side effect.
- `task_write` with `retry_record`: create a new leased attempt from an existing `failed` Record without resupplying its URL or values.
- `task_write` with `renew_reservation`: extend a live claim.
- `task_write` with `finish_record`: close reserved work as completed, failed, or uncertain.
- `task_write` with `resolve_record`: reconcile uncertain work after checking the external system.
- `task_write`: create, update, complete/cancel, or tombstone Tasks and Records.

Inspect the live tool schema for exact fields. Use [references/tool-contract.json](references/tool-contract.json) only to verify generated schema, defaults, or scopes. Consult [references/mcp-contract.md](references/mcp-contract.md) before using dedupe, leases, uncertain resolution, or terminal task actions.

## Rules

- Define only needed columns. Business keys and values remain under `record.values`, so common names such as `result`, `status`, `revision`, and `task_ref` are valid and never collide with system fields. Follow the live key schema's syntax and sensitive-data restrictions.
- In `create_records`, give every item its own permanently unique `request_id` and classify its known outcome: `completed` for confirmed success, `failed` for confirmed no external effect (including researched but not submitted), or `uncertain` when the effect cannot be verified. Omission remains `completed`. Inspect every ordered item result; batches may partially succeed. Retry the unchanged batch or only failed items, never rewrite successful items under new IDs. Prefer 100–200 items unless small records justify using the 500-item maximum.
- Add a write dedupe rule only when uniqueness matters; default to global unless uniqueness is intentionally per Task.
- Research before taking an execution lease. Immediately before an external side effect, call `reserve_record`, or `retry_record` when continuing a known `failed` Record, and proceed only after `record_reserved`. Finish promptly and renew before a lease expires.
- Mark `failed` only when the effect definitely did not happen. If it may have happened, use `uncertain`, verify externally, then resolve it.
- Retry only a current `failed` Record with its `record_ref` and revision. Do not delete history, alter a URL, or reconstruct values to bypass dedupe. The new reserved Record links back through `retry_of`; `completed` and `uncertain` remain blocked.
- `task_check_duplicate` takes `url` directly; add `task_ref` and/or `task_name` as AND conditions. Never pass `action`, `scope`, or `values`. It returns `exists` and is never permission to act.
- URL columns are resource URLs: path and query remain identity-bearing. Do not collapse them to website hosts.
- Every mutation needs a globally unique `request_id` that is never recycled; reuse it only for the identical retry. Existing-resource changes also need the current revision.
- A connector-side schema rejection does not authorize new per-item IDs or a substitute action. After refresh, retry the identical batch or only its unconfirmed items with their original IDs; if delivery was ambiguous, inspect current state first.
- Treat `conflict`, `busy`, `lease_lost`, and `uncertain` as reasons to inspect current state, not to retry blindly.
- Complete or cancel a Task only after reserved and uncertain Records are resolved. Deletion is a tombstone and does not erase completed dedupe facts.
- Keep credentials, sessions, raw transcripts, memory, and full website/account documents out of task records. This Skill tracks work; another authorized tool performs it.
