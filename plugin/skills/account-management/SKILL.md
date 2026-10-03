---
name: account-management
description: Store and retrieve website login credentials with the Search Stack account_management tool. Use for account records, not browsing, website catalog data, tasks, or memory.
---

# Account Management

Use only the exact MCP tool `account_management`. Do not use raw Elasticsearch, guessed tool names, or a local credential copy. If the tool or required action is absent, stop and report it.

## Choose the operation

- `create`: save a new website account.
- `get`: read one known `account_ref`.
- `list`: find accounts for a URL, optionally narrowed by DigitalHuman.
- `update`: change the password or DigitalHuman owner.
- `delete`: retire a credential while preserving its identity tombstone.

Inspect the live tool schema for exact fields. Use [references/tool-contract.json](references/tool-contract.json) only to verify generated schema, defaults, or scopes. Consult [references/mcp-contract.md](references/mcp-contract.md) when identity, mutation, or deletion semantics matter.

## Rules

- Create with `url`, never `platform`. Website identity is the normalized host; scheme, port, path, query, fragment, case, and trailing dot do not distinguish accounts. `www` remains distinct.
- The unique account identity is normalized host plus normalized username. URL and username are immutable.
- Send passwords as plaintext MCP fields. The server encrypts storage. Credential reads through `get` and `list` always return plaintext passwords.
- Never place a returned password in summaries, logs, tasks, website records, memory, evidence, or `request_id`.
- Every mutation needs a globally unique `request_id` that is never recycled; reuse it only for the identical retry. `update` and `delete` also need the current revision.
- On `conflict`, read current state and reconsider. Do not overwrite blindly.
- This Skill manages credentials only. It does not log in, browse, receive email, or prove an external action succeeded.
