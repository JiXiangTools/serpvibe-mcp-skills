# Task management MCP contract

This is the required `task_management` Workflow contract. A Task is a dynamic table, its columns are the schema, and each Record is one row. Business field names are never fixed by the Skill.

## Common request and result

Every mutation accepts a caller-generated stable `request_id`. Replaying the same logical request with the same canonical input must return the same completed outcome. Reusing it with different canonical input must return `rejected`.

Mutations of existing Tasks or Records require `expected_revision`. Successful mutations increment `revision` exactly once. A stale revision returns `conflict` with the current safe projection; it never performs a last-write-wins update.

Common outcomes and codes include:

```text
ok | not_found | conflict | invalid | rejected
unauthorized | forbidden | unavailable

task_created | task_found | task_listed | task_updated
task_completed | task_cancelled | task_deleted
record_created | record_reserved | record_completed
record_failed | record_uncertain | record_resolved
record_found | record_listed | record_updated | record_deleted
available | duplicate | busy | lease_lost
```

All list operations use bounded pagination and an opaque cursor.

## Task schema

`create_task` accepts:

```text
request_id
task_name
description?
columns[]
dedupe?
```

Each column has `key`, `label`, `type`, `required`, optional `description`, and optional `deprecated`. Supported types are `string`, `text`, `integer`, `number`, `boolean`, `date`, `datetime`, `url`, and `json`.

A Task has at most one dedupe rule:

```text
namespace
rule_key
components[]             ordered slot-to-column mappings
scope                    global | task; default global
normalization_version    returned by the server
```

The write scope is fixed by the Task and cannot be overridden by a Record mutation. A read-only duplicate check may use global or task scope. `case_sensitive` defaults to true for string components. The server assigns `normalization_version`; callers cannot choose it. `text` and `json` columns cannot be dedupe components.

## Supported actions

### Tasks

```text
create_task
  request_id, task_name, description?, columns, dedupe?

get_task
  task_ref

list_tasks
  status?, cursor?, limit?

update_task
  request_id, task_ref, expected_revision
  task_name?, description?, columns?, dedupe?

complete_task | cancel_task
  request_id, task_ref, expected_revision

delete_task
  request_id, task_ref, expected_revision, reason
```

Task status is `active | completed | cancelled`. Completed and cancelled Tasks reject new Records. Completion and cancellation require no reserved or uncertain Records. Delete is a tombstone and only accepts a terminal Task.

### Records

```text
check_duplicate
  task_ref, values, scope?, limit?

create_record
  request_id, task_ref, values

reserve_record
  request_id, task_ref, values, lease_seconds?

renew_reservation
  request_id, record_ref, lease_ref, expected_revision, lease_seconds?

finish_record
  request_id, record_ref, lease_ref, expected_revision
  outcome, values_patch?, error_code?, error_message?

resolve_record
  request_id, record_ref, expected_revision
  resolution, values_patch?, reason

get_record
  record_ref

list_records
  task_ref, status?, created_after?, created_before?, cursor?, limit?

update_record
  request_id, record_ref, expected_revision, values_patch

delete_record
  request_id, record_ref, expected_revision, reason
```

`create_record` writes a completed row for an already-known fact. `reserve_record` is mandatory before an external side effect and atomically performs dedupe plus a lease. `check_duplicate` is advisory only.

Calling `check_duplicate` for a Task without a dedupe rule returns `invalid`.

Record status is:

```text
reserved | completed | failed | uncertain | duplicate
```

`failed` means the external effect is confirmed not to have occurred and releases the Claim. `uncertain` blocks duplicates until `resolve_record` confirms completed or failed. A duplicate Record points to the existing Record and does not own a Claim.

Lease duration defaults to 300 seconds and must be between 30 and 1800 seconds. An expired lease returns `lease_lost` and becomes uncertain; it is never automatically reassigned. The caller must verify the external system and resolve the Record before any retry.

`update_record` may patch only non-dedupe values. Reserved and uncertain Records cannot be deleted. Deleting a completed Record does not release its dedupe history.

For `values_patch`, JSON `null` clears an optional non-dedupe column. Required and dedupe columns cannot be cleared. Mutation `request_id` values must be globally unique, not merely unique inside one Task.

## Dedupe

The Workflow derives fingerprints from the Task rule and original values. Callers never provide normalized values or fingerprints.

- Global scope compares compatible Tasks sharing `namespace + rule_key + normalization_version`.
- Task scope adds `task_ref` to the identity.
- Tasks sharing a namespace and rule key must use compatible components, types, normalization, and write scope.
- Records store a scope-independent match fingerprint for read-only cross-task lookup; Claims use a second fingerprint that includes the configured write scope and task_ref when needed.
- String normalization uses Unicode NFKC, trim, whitespace collapse, and the configured case behavior.
- URL normalization lowercases scheme and host, removes default ports and fragments, normalizes an empty path to `/`, and preserves path case and query ordering.

The Workflow owns stable IDs, schema validation, dedupe profile compatibility, normalization, claims, lease expiry handling, timestamps, allowed state transitions, revisions, idempotency, recovery, and tombstones.

## Security and logging

- Each Bot uses its own MCP/Elasticsearch identity. Shared unrestricted API keys are invalid.
- The Workflow executes with least-privilege access to its fixed index.
- Workflow traces contain request metadata and outcomes, not Authorization, lease references, full values, credentials, or unrestricted payloads.
- Raw Elasticsearch request tools are not part of the Bot-visible tool surface.
