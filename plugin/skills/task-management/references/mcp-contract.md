# Task behavior

Exact actions and fields come from [tool-contract.json](tool-contract.json) or the live MCP schema. A Task defines a dynamic table; each Record is one row.

Use `task_read` for the four read actions and `task_write` for every mutation.
Use the standalone `task_check_duplicate` tool for duplicate lookup;
`task_management` is the internal Workflow ID, not an MCP tool name.

## Idempotency and revisions

- `request_id` is globally unique forever and may be reused only for the identical retry. Changed input returns `rejected / request_id_reused`.
- `create_records` carries `request_id` per item rather than at batch level. A batch is an ordered processing container, not one atomic mutation.
- Existing-resource mutations use revision CAS. A stale revision returns `conflict`; re-read before deciding.

## Dynamic column namespace

- Column keys and their values are always nested under `record.values`; system fields remain at the Record root and never share that namespace.
- Common business keys such as `result`, `status`, `revision`, and `task_ref` are valid. Do not rename them merely because an identically named system field exists outside `values`.
- The live key schema defines lowercase identifier syntax and rejects credential/session-like names. The runtime uses the same policy constants and returns `invalid / invalid_column_key` for violations.

## Records and leases

- `create_records` writes 1–500 completed facts and is also the single-fact interface. Results preserve input order and report per-item outcome, code, and references plus batch counts. Batches of 100–200 are the normal default; use the maximum only for small records when fewer round trips matter.
- Batch items are independent: one invalid, conflicting, or unavailable item does not roll back successful items. The whole batch is rejected before writes only when its shape is invalid, including empty or oversized input and repeated item `request_id` values.
- Retry the identical batch or only failed items with their original `request_id`. Do not assign new IDs to successful items. The HTTP body limit may impose a lower practical item count for large values.
- If the connector rejects `create_records` as though `action` must equal another value, its cached tool schema is stale. Refresh or reconnect the MCP and start a new session; updating the Skill alone is insufficient. A connector-local rejection may be retried with the original item IDs, but ambiguous delivery requires a state check first.
- `reserve_record` remains single-item because it atomically checks write dedupe and creates a lease before an external effect.
- Only `record_reserved` permits the caller to proceed. Renew long-running work before expiry, then call `finish_record`.
- `failed` means the effect definitely did not happen and releases the claim. `uncertain` keeps the claim until external verification and `resolve_record`.
- An expired lease becomes uncertain and is never automatically reassigned. `busy`, `lease_lost`, and `uncertain` require inspection rather than blind retry.

## Duplicate checks

- `task_check_duplicate` accepts a direct object without `action`, normalizes the required resource `url`, and returns `duplicate_checked` with `exists: bool`.
- With URL alone it searches globally. Optional `task_ref` and `task_name` are AND conditions; there is no `scope`, field-name, `values`, or query parameter.
- It works without a Task write-dedupe rule.
- Completed, reserved, and uncertain Records count as existing. Failed and duplicate audit rows do not.

## Write dedupe and lifecycle

- A Task may define one ordered write-dedupe rule. Global scope shares compatible rules across Tasks; task scope adds `task_ref`.
- URL dedupe preserves path/query case and order while normalizing scheme, IDNA host, host case/trailing dot, default port, fragment, and empty path.
- Dedupe values are immutable. Deleting a completed Record does not release its identity.
- Completed or cancelled Tasks reject new Records. Complete or cancel only after reserved and uncertain work is resolved. Delete accepts only a terminal Task and creates a tombstone.
