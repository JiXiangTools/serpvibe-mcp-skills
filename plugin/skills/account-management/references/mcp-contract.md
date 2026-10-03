# Account behavior

Exact actions and fields come from [tool-contract.json](tool-contract.json) or the live MCP schema.

## Identity and reads

- Website identity is host-only and shared with `website_management`; it ignores scheme, port, path, query, fragment, host case, and trailing dot. `www` remains distinct.
- Normalized host plus normalized username is globally unique. `account_ref`, URL, and username are immutable.
- `get` and URL `list` always return plaintext passwords. Credential reads have one permission and one response contract, without a redaction switch.

## Mutations

- `request_id` is globally unique forever and may be reused only for the identical retry. Changed input returns `rejected / request_id_reused`.
- Existing-record mutations use revision CAS. A stale revision returns `conflict / revision_conflict`; re-read before deciding.
- `update` may change only password or `digital_human_id`.
- `delete` clears the encrypted credential but preserves a permanent identity tombstone.

Passwords are plaintext only across the trusted MCP call; Elasticsearch stores the encrypted envelope. Reads require `account:read`, mutations require `account:write`, and `digital_human_id` is data rather than an authorization principal.
