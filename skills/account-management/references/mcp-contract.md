# Account management MCP contract

This is the required contract for the independent Search Stack MCP tool. Index names, mappings, encryption envelopes, and physical document IDs are server implementation details.

## Common request and result

The tool name is `account_management`. It accepts an `action`-tagged object and rejects unknown fields.

Every successful mutation is idempotent for its target account. `create`, `update`, and `delete` require a globally unique caller-generated `request_id` containing 1-128 ASCII letters, digits, `_`, `-`, `.`, or `:`. Reuse it only to retry the same logical mutation. Replaying the same ID and canonical input returns the original successful result without incrementing `revision`; reusing that ID with different canonical input returns `rejected / request_id_reused`.

Existing-record mutations require `expected_revision`. A successful new mutation increments `revision` exactly once. A stale revision returns `conflict / revision_conflict` with `current_revision`.

Every result has `outcome` and `code`. Stable combinations include:

```text
ok / created | found | listed | updated | deleted
not_found / account_not_found
conflict / url_username_exists | revision_conflict
rejected / request_id_reused
invalid / <validation_code>
forbidden / oauth_scope_required
unavailable / workflow_unavailable
```

A missing or invalid Bearer Token is rejected by the MCP transport as HTTP `401 / invalid_token`, before the Tool runs. Elasticsearch authorization and connectivity failures are not exposed directly and map to `unavailable / workflow_unavailable`.

All list operations use bounded pagination and an opaque cursor.

## `account_management`

Supported actions:

```text
create
  request_id
  digital_human_id
  url
  username
  password

get
  account_ref
  include_password: boolean = true

list
  url
  digital_human_id?
  include_password: boolean = true
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

One DigitalHuman may own multiple accounts on the same website. The workflow shares URL normalization with `website_management`: path, query, fragment, host case, trailing dot, and port do not affect website identity. The normalized host and normalized username pair is globally unique. Creating an existing pair with a different request returns `conflict / url_username_exists`.

`account_ref`, URL, and username are immutable. An update may change the password or `digital_human_id` and always requires revision CAS.

Passwords cross the trusted MCP transport as plaintext request values. The server validates them, encrypts them with AES-256-GCM, and writes only the authenticated envelope to Elasticsearch. Exact `get` and URL `list` decrypt and return matching passwords by default. Passing `include_password=false` omits passwords as a response projection without changing authorization.

Delete keeps `account_ref`, `digital_human_id`, URL identity, username, revision, timestamps, and `deleted_at`, but clears the encrypted credential. The tombstone is not restorable as a usable credential and its identity cannot be reused silently.

## Security and logging

- Each HTTP caller supplies an OAuth Bearer Token. The MCP's Elasticsearch service key never leaves the server.
- Reads, including plaintext password retrieval, require `account:read`; mutations require `account:write`.
- `digital_human_id` remains account data and does not provide a separate application-level authorization boundary.
- Passwords and authorization headers must not appear in server logs, error messages, idempotency receipts, or other workflow records.
- Raw Elasticsearch request tools are not part of the Bot-visible tool surface.
