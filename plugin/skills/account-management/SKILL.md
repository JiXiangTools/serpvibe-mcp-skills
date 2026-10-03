---
name: account-management
description: Manage website credentials and operate registration, login, or password changes with the Search Stack account_management and account_browser tools. Use for account lifecycle work, not website catalog data, tasks, or memory.
---

# Account Management

Use only the exact MCP tools `account_management` and `account_browser`. Do not use raw Elasticsearch, guessed tool names, a local credential copy, or a general browser tool for passwords. If the required tool or action is absent, stop and report it.

## Choose the operation

- `create`: save a new website account.
- `get`: read one known `account_ref`.
- `list`: find accounts for a URL, optionally narrowed by DigitalHuman.
- `update`: change the password or DigitalHuman owner.
- `delete`: retire a credential while preserving its identity tombstone.

Use `account_browser` when the requested outcome happens on a website:

- `start_registration`: generate a password server-side and open the exact registration URL.
- `start_login`: open the exact login URL for a stored `account_ref`.
- `start_password_change`: escrow a generated new password and open the settings URL.
- `observe` / `act`: inspect elements and fill only non-secret fields.
- `inject_credentials`: identify the returned username/password element refs; the service injects secrets without returning them.
- `complete`: call only after the page proves success; this commits the registered or changed credential.
- `resume`: recreate a lost browser session from durable operation state.
- `cancel`: close the session and clear an uncommitted generated credential.

Inspect the live tool schema for exact fields. Use [references/tool-contract.json](references/tool-contract.json) only to verify generated schema, defaults, or scopes. Consult [references/mcp-contract.md](references/mcp-contract.md) when identity, mutation, or deletion semantics matter.

## Rules

- Create with `url`, never `platform`. Website identity is the normalized host; scheme, port, path, query, fragment, case, and trailing dot do not distinguish accounts. `www` remains distinct.
- The unique account identity is normalized host plus normalized username. URL and username are immutable.
- Send passwords as plaintext MCP fields. The server encrypts storage. Credential reads through `get` and `list` always return plaintext passwords.
- For website registration, login, or password changes, prefer `account_browser`; do not first read a password and copy it into another tool. `account_browser` has no password input or output.
- Browser page URLs preserve path and query case. They must remain on the account's normalized host; use only `element_ref` values from the latest snapshot.
- Never use `act.fill` for a password field. Use `inject_credentials`, even if another tool could reveal the password.
- Treat `act`, `inject_credentials`, and `complete` as external side effects. Never bypass CAPTCHA, email/device verification, or user confirmation.
- Registration and password change are two-phase operations. Call `complete` only after visible site success. On `reconciliation_required`, re-read the account revision and retry `complete` with that revision; do not generate a second password.
- Never place a returned password in summaries, logs, tasks, website records, memory, evidence, or `request_id`.
- Every mutation needs a globally unique `request_id` that is never recycled; reuse it only for the identical retry. `update` and `delete` also need the current revision.
- On `conflict`, read current state and reconsider. Do not overwrite blindly.
- Page observation is evidence, not a transactional guarantee. If the site result is ambiguous, do not call `complete`; keep or cancel the operation and report the uncertainty.
