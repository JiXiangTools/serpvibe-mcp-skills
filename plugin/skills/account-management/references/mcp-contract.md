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

## Server-side website operations

The companion `account_browser` tool performs registration, login, and password
changes through a server-side nodriver worker. All actions require both
`account:read` and `account:write`. The bot receives only a redacted interactive-element snapshot
and opaque `element_ref` values; credential injection has no password argument
or result.

Start/resume/complete mutations are durable and idempotent by the original
`request_id`. Individual browser actions use a session-scoped `action_id` and
cannot provide exactly-once guarantees across a lost external connection.
Registration and password changes become account records only after the bot
observes site success and calls `complete`. A revision collision enters
`reconciliation_required` while retaining the encrypted pending password.

Browser URLs use resource normalization, so path/query case is preserved, while
all navigation remains on the account's normalized host. CAPTCHA and human
verification are never bypassed.

`act` uses a flat request shape. `command` is a top-level sibling of `action`,
`operation_ref`, and `action_id`: `navigate` requires `url`, `click` requires
`element_ref`, `fill` requires `element_ref` plus `text`, and `select` requires
`element_ref` plus `value`. Do not wrap those fields in a nested command object.
