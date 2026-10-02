# Digital-human memory MCP contracts

The two workflows share an entry-oriented contract while preserving separate owner scopes and authorization. Physical index aliases, mappings, scripts, and document IDs remain hidden implementation details.

## Memory entry

```text
memory_ref
scope: role | digital_human
owner_ref
memory_kind: fact | user_assertion | preference | operational_lesson
content
rationale?
source_refs[]
revision
created_at
updated_at
deleted_at?
```

Each entry contains one independently correctable fact or compact experience. `memory_ref`, scope, owner, caller identity, timestamps, and revision are Workflow-owned fields.

## Common behavior

Every mutation accepts a stable `request_id`. Replaying the same request and canonical input returns the original outcome. Reusing the request ID with different canonical input returns `rejected`.

`update` and `delete` require `expected_revision`. A stale revision returns `conflict` and a safe current projection without changing the entry. Delete creates a tombstone and never reassigns `memory_ref`.

Common outcomes:

```text
created | found | listed | updated | deleted | unchanged
not_found | conflict | rejected | unauthorized
```

## `serpvibe.role_memory`

```text
create
  request_id
  role_ref
  memory_kind
  content
  rationale?
  source_refs?

get
  memory_ref

list
  role_ref
  memory_kind?
  query?
  cursor?
  limit?

update
  request_id
  memory_ref
  expected_revision
  memory_kind?
  content?
  rationale?
  source_refs?

delete
  request_id
  memory_ref
  expected_revision
  reason
```

Only trusted Role maintainers may mutate Role memory. Reading follows Role visibility. A workflow must reject attempts to move an entry to another Role or change its scope.

## `serpvibe.digital_human_memory`

```text
create
  request_id
  digital_human_id
  memory_kind
  content
  rationale?
  source_refs?

get
  memory_ref

list
  digital_human_id
  memory_kind?
  query?
  cursor?
  limit?

update
  request_id
  memory_ref
  expected_revision
  memory_kind?
  content?
  rationale?
  source_refs?

delete
  request_id
  memory_ref
  expected_revision
  reason
```

Only the exact DigitalHuman or an authorized operator may mutate its important memory. A workflow must reject attempts to change `digital_human_id`, convert personal memory into Role memory, replace the complete memory collection, or write Session/transcript/task/credential content.

## Security and retrieval

- Each Bot uses its own Kibana MCP identity.
- List and query are always restricted by the exact owner reference.
- Cross-owner search is unavailable to ordinary Bots.
- Raw Elasticsearch request tools are not part of the Bot-visible tool surface.
