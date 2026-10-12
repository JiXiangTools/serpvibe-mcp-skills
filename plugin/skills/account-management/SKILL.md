---
name: account-management
description: Manage website credentials and operate registration, login, or password changes with the Search Stack account_read, account_write, and account_browser tools. Use for account lifecycle work, not website catalog data, tasks, or memory.
---

# Account Management

Use `account_read`, `account_write`, and `account_browser` through MCP. Read the live schema for exact fields; [tool-contract.json](references/tool-contract.json) is the generated reference. Do not substitute database access, local credential copies, or a general browser tool for password operations.

## Choose the operation

- `account_read`: `get` by `account_ref`; `list` by `url`, optionally filtered by `digital_human_id`. Both return plaintext passwords.
- `account_write`: `create` with `url`, `username`, `password`, and `digital_human_id`; `update` the password or owner; `delete` the credential. Send passwords as plaintext MCP fields.
- For website registration, login, or password changes, use `account_browser` as described in [browser operations](references/mcp-contract.md). Do not read a password just to copy it into another tool.

## Call rules

- Identify the website with `url`, never `platform`. Host case, trailing dot, scheme, port, path, query, and fragment are ignored; `www` remains distinct. Normalized host plus normalized username is unique. `account_ref`, URL, and username are immutable; deletion does not free the identity.
- Never place a returned password in summaries, logs, tasks, website records, memory, evidence, or `request_id`.
- `account_write` mutations need a globally unique `request_id`; never recycle it except for the identical retry. `update` and `delete` also need the current `expected_revision`. Browser IDs follow the [browser rules](references/mcp-contract.md).
- On `revision_conflict`, re-read before deciding. On `request_id_reused`, do not change the ID to force the write. After an ambiguous response or schema rejection, inspect state before retrying; keep the original ID and input for an identical retry.
- Reads require `account:read`, writes require `account:write`, and browser operations require both. On `insufficient_scope` or `oauth_scope_required`, let the host authorize; if still denied, report and stop. Do not reinstall or loop retries. `digital_human_id` does not grant permissions.
- For a missing tool or cancellation, report the actual error and stop the affected operation; do not guess another tool name or replay a write whose delivery is unknown.
