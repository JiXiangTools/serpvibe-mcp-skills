# Task behavior

Exact actions and fields come from [tool-contract.json](tool-contract.json) or the live MCP schema. A Task defines a dynamic table; each Record is one row.

## Idempotency and revisions

- `request_id` is globally unique forever and may be reused only for the identical retry. Changed input returns `rejected / request_id_reused`.
- Existing-resource mutations use revision CAS. A stale revision returns `conflict`; re-read before deciding.

## Dynamic column namespace

- Column keys and their values are always nested under `record.values`; system fields remain at the Record root and never share that namespace.
- Common business keys such as `result`, `status`, `revision`, and `task_ref` are valid. Do not rename them merely because an identically named system field exists outside `values`.
- The live key schema defines lowercase identifier syntax and rejects credential/session-like names. The runtime uses the same policy constants and returns `invalid / invalid_column_key` for violations.

## Records and leases

- `create_record` writes a completed fact. `reserve_record` atomically checks write dedupe and creates a lease before an external effect.
- Only `record_reserved` permits the caller to proceed. Renew long-running work before expiry, then call `finish_record`.
- `failed` means the effect definitely did not happen and releases the claim. `uncertain` keeps the claim until external verification and `resolve_record`.
- An expired lease becomes uncertain and is never automatically reassigned. `busy`, `lease_lost`, and `uncertain` require inspection rather than blind retry.

## Duplicate checks

- `check_duplicate` normalizes the required resource `url` and returns `duplicate_checked` with `exists: bool`.
- With URL alone it searches globally. Optional `task_ref` and `task_name` are AND conditions; there is no `scope`, field-name, `values`, or query parameter.
- It works without a Task write-dedupe rule.
- Completed, reserved, and uncertain Records count as existing. Failed and duplicate audit rows do not.

## Write dedupe and lifecycle

- A Task may define one ordered write-dedupe rule. Global scope shares compatible rules across Tasks; task scope adds `task_ref`.
- URL dedupe preserves path/query case and order while normalizing scheme, IDNA host, host case/trailing dot, default port, fragment, and empty path.
- Dedupe values are immutable. Deleting a completed Record does not release its identity.
- Completed or cancelled Tasks reject new Records. Complete or cancel only after reserved and uncertain work is resolved. Delete accepts only a terminal Task and creates a tombstone.
