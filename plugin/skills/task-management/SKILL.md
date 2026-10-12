---
name: task-management
description: Track table-shaped work, row results, reservations, and duplicate checks with the Search Stack task_read, task_write, and task_check_duplicate tools. Use for coordinated progress, not for performing the external work or storing credentials.
---

# Task Management

Use `task_read`, `task_write`, and `task_check_duplicate` through MCP. Read the
live schema for fields; [tool-contract.json](references/tool-contract.json) is
the generated reference. Use other authorized tools for external work; keep
credentials and browser sessions out of task records.

## Choose the action

- Inspect: `task_read` with `get_task`, `list_tasks`, `get_record`, or `list_records`.
- Manage Tasks: `task_write` with `create_task`, `update_task`, `complete_task`,
  `cancel_task`, or `delete_task`; define only needed business columns.
- Check a URL: `task_check_duplicate` with `url`; optional `task_ref` and
  `task_name` narrow the search together. No `action` or `scope`. `exists` is
  advisory, not permission to execute.
- Import known results: `task_write` with `create_records`, 1–500 items and an
  explicit outcome per item. A single fact is a one-item batch. Inspect each
  result because a batch may partially succeed.
- Start work: `reserve_record`; continue a failed attempt: `retry_record`.
  Proceed only on `record_reserved`; use `renew_reservation` before the lease
  expires, then close with `finish_record`.
- Reconcile an unknown result: verify externally, then `resolve_record`.
- Correct a mistaken completion: verify that the target action did not happen,
  then `correct_record_outcome`; use `retry_record` for a new execution lease.
  Read [usage details](references/mcp-contract.md) for correction, leases, imports,
  and duplicate checks.

## Record outcomes

- `completed`: the intended action happened. Finishing research, signing in,
  pausing, or merely saving a row does not complete a submission.
- `failed`: the intended action definitely did not happen; it may be retried.
- `uncertain`: the action may have happened; verify it before another attempt.

`create_records` defaults to `completed` when outcome is omitted. Changing a
business field such as `values.status` does not change the system outcome.
Preserve history and identity; do not delete records or change URLs to bypass
duplicate protection.

## Call rules

Every mutation needs a globally unique `request_id` (per item for imports).
Reuse it only for an identical retry. Existing-record changes need the current
revision. On `revision_conflict`, re-read; on `request_id_reused`, do not change
the ID to force the write. After an ambiguous response, inspect state before
acting. Complete or cancel a Task only when reserved and uncertain work is
resolved; terminal Tasks accept no new attempts.

Reads and duplicate checks require `task:read`; writes require `task:write`.
On `insufficient_scope` or `oauth_scope_required`, let the host authorize; if
still denied, report and stop. Do not reinstall or loop retries. For a missing
tool or cancellation, report the actual error and stop the affected operation;
do not guess another tool name or replay a write whose delivery is unknown.
