# Account management MCP contract

This is the required contract for the independent Search Stack MCP tool. Index names, mappings, encryption envelopes, and physical document IDs are server implementation details.

## Common request and result

The tool name is `account_management`. It accepts an `action`-tagged object and rejects unknown fields.

Every successful mutation is idempotent within its target account identity. `create`, `update`, and `delete` require a caller-generated `request_id` containing 1-128 ASCII letters, digits, `_`, `-`, `.`, or `:`. Replaying the same ID and canonical input returns the original successful result without incrementing `revision`. Reusing that ID with different canonical input for the same account returns `rejected / request_id_reused`.

Existing-record mutations require `expected_revision`. A successful new mutation increments `revision` exactly once. A stale revision returns `conflict / revision_conflict` with `current_revision`.

Every result has `outcome` and `code`. Stable combinations include:

```text
ok / created | found | listed | updated | deleted
not_found / account_not_found
conflict / platform_username_exists | revision_conflict
rejected / request_id_reused
invalid / <validation_code>
unauthorized / elasticsearch_unauthorized
forbidden / elasticsearch_forbidden
unavailable / workflow_unavailable
```

All list operations use bounded pagination and an opaque cursor.

## `account_management`

Supported actions:

```text
create
  request_id
  digital_human_id
  platform
  username
  password

get
  account_ref
  include_password: boolean = false

list
  digital_human_id
  platform?
  cursor?
  limit?

update
  request_id
  account_ref
  expected_revision
  password?
  digital_human_id?

delete
  request_id
  account_ref
  expected_revision
```

One DigitalHuman may own multiple accounts on the same platform. The workflow normalizes `platform` and `username`, and the pair is globally unique. Creating an existing pair with a different request returns `conflict / platform_username_exists`.

`account_ref`, platform, and username are immutable. An update may change the password or `digital_human_id` and always requires revision CAS.

Passwords cross the trusted MCP transport as plaintext request values. The server validates them, encrypts them with AES-256-GCM, and writes only the authenticated envelope to Elasticsearch. `get(include_password=false)` and every `list` result omit the password. `get(include_password=true)` decrypts server-side and returns plaintext for the exact account.

Delete keeps `account_ref`, `digital_human_id`, platform, username, revision, timestamps, and `deleted_at`, but clears the encrypted credential. The tombstone is not restorable as a usable credential and its identity cannot be reused silently.

## Security and logging

- Each HTTP caller supplies an OAuth Bearer Token. The MCP's Elasticsearch service key never leaves the server.
- Reads require `account:read`; mutations require `account:write`; plaintext password reads additionally require `account:credentials:read`.
- `digital_human_id` remains account data and does not provide a separate application-level authorization boundary.
- Passwords and authorization headers must not appear in server logs, error messages, idempotency receipts, or other workflow records.
- Raw Elasticsearch request tools are not part of the Bot-visible tool surface.
