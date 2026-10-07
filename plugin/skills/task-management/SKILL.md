---
name: task-management
description: Track table-shaped work, row results, reservations, and duplicate checks with the Search Stack task_read, task_write, and task_check_duplicate tools. Use for coordinated progress, not for performing the external work or storing credentials.
---

# Task Management

A Task is a table; a Record is one attempt or recorded fact. Use `task_read`,
`task_write`, and `task_check_duplicate`. Another authorized tool performs the
external work. Keep credentials and browser sessions out of task records.

## Choose the action

- Inspect: `task_read` with `get_task`, `list_tasks`, `get_record`, or `list_records`.
- Create, update, complete or cancel a Task with `task_write`; define only the
  business columns needed for the work.
- Check a URL: `task_check_duplicate` with `url`; optional `task_ref` and
  `task_name` narrow the search together. No `action` or `scope`. `exists` is
  advisory, not permission to execute.
- Import known results: `task_write` with `create_records`, 1–500 items and an
  explicit outcome per item. A single fact is a one-item batch. Inspect each
  result because a batch may partially succeed.
- Start work: `reserve_record`; continue a failed attempt: `retry_record` with
  its reference, current revision, and reason. Proceed only on `record_reserved`.
  Renew before the lease expires, then close with `finish_record`.
- Reconcile an unknown result: verify externally, then `resolve_record`.
- Correct a mistaken completion: verify that the target action did not happen,
  then `correct_record_outcome` with the record reference, current revision,
  reason, and evidence. Success changes it to `failed`; use `retry_record` to
  obtain a new attempt and lease. Correction alone does not permit execution.

## Choose the outcome

- `completed`: the intended action happened. Finishing research, signing in,
  pausing, or merely saving a row does not complete a submission.
- `failed`: the intended action definitely did not happen; it may be retried.
- `uncertain`: the action may have happened; verify it before another attempt.

`create_records` defaults to `completed` when outcome is omitted. Changing a
business field such as `values.status` does not change the system outcome.
Missing receipts or a duplicate warning alone do not justify correction.
Preserve history and identity; do not delete records or change URLs to bypass
duplicate protection.

Every mutation needs a globally unique `request_id` (per item for imports).
Reuse it only for an identical retry. Existing-record changes need the current
revision. After a conflict, re-read; after an ambiguous response, inspect state
before acting. Complete or cancel a Task only when reserved and uncertain work
is resolved; terminal Tasks accept no new attempts.

Use the live tool schema for fields. Read [usage details](references/mcp-contract.md)
for correction, leases, and dedupe; [tool-contract.json](references/tool-contract.json)
is the generated schema reference. If a new action is missing from the host's
schema, refresh its tool definitions to discover it; existing actions remain
usable. A cancellation message alone does not identify the failure's cause.
