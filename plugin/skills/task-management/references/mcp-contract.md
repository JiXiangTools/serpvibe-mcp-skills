# Task usage details

Use the live schema or [tool-contract.json](tool-contract.json) for exact fields.

## Continue work

| Current system status | Next action |
| --- | --- |
| `failed` | `retry_record` with its reference, current revision, and reason |
| `uncertain` | Verify externally; `resolve_record` as completed or failed |
| `completed`, but completion was a verified recording error | `correct_record_outcome`, then `retry_record` |
| `reserved` | Continue with the valid lease; renew before expiry |
| `completed` with a real external result, or `duplicate` | Preserve the result; do not resubmit |

For correction, call `task_write` with:

```json
{
  "action": "correct_record_outcome",
  "request_id": "unique-correction-id",
  "record_ref": "<original record reference>",
  "expected_revision": 5,
  "reason": "A login checkpoint was recorded as submission completion",
  "evidence": "Describe the verified external evidence that the target action did not occur"
}
```

Replace the example reference, revision, ID, reason, and evidence with current
facts. Evidence must be nonempty and at most 8192 UTF-8 bytes; reason must be
nonempty and at most 2000 characters. Optional `values_patch` updates business
notes without changing dedupe fields. The server stores the supplied evidence;
the caller must verify its truth. A missing receipt alone is insufficient.

Success returns `record_outcome_corrected` and the corrected Record, with no
lease. Pass its reference and returned revision to `retry_record` with a new
request ID and reason. Only `record_reserved` allows execution. The new Record's
`retry_of` links to the source; historical evidence is retained. A stale revision
returns `revision_conflict`; a non-completed source returns `record_not_completed`.

`retry_record` also requires an active parent Task and a free duplicate claim.
It returns `busy`, `uncertain`, or `duplicate` when another attempt blocks it.
Leases default to 300 seconds, configurable from 30 to 1800. An expired lease
becomes uncertain; inspect and reconcile before retrying. Do not keep an
execution lease merely while researching or waiting for login.

## Import and update

`create_records` accepts 1–500 items, each with its own `request_id`, `values`,
and outcome. Prefer 100–200 per request; use larger batches for small records.
Results follow input order. Retry identical unconfirmed items with their original
IDs. Changed input under a used ID returns `request_id_reused`.

Business values live under `record.values`; names such as `status` and `result`
are business columns and do not replace system fields. Define only needed
columns, following the live schema's naming rules. Credentials and sessions
belong in account/browser tools.

## Duplicate identity

`task_check_duplicate` searches globally by normalized resource URL unless
`task_ref` or `task_name` narrows it. Completed, reserved, and uncertain records
count as existing; failed and duplicate audit rows do not. Its boolean result
does not reserve work or explain which record owns the claim.

Write dedupe is the Task's configured rule. Use global scope when compatible
Tasks should share uniqueness. Resource URLs preserve path and query identity;
do not reduce them to hosts. Dedupe fields are immutable. Deleting a completed
Record does not free its identity, and correcting a Record does not reopen a
completed or cancelled Task.
