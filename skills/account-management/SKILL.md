---
name: account-management
description: Manage Serpvibe account credentials through the account_management tool exposed by the Search Stack MCP. Use for creating, reading, updating, listing, or deleting account records; do not use for tasks, websites, browser interaction, or digital-human memory.
---

# Account Management

Use the independent Search Stack MCP as the only account-data access path. Elasticsearch is the only writable truth. Do not use raw Elasticsearch tools, guessed index names, or a local account copy.

## Required MCP surface

Before the first operation, inspect the connected MCP tool catalog and require this business tool:

- `account_management`

Read [references/mcp-contract.md](references/mcp-contract.md) before the first invocation in a task. If the tool is unavailable or its schema is incompatible, stop and report the missing capability.

## Workflow

1. Determine the action, exact account, and requested change.
2. For `create`, `update`, and `delete`, generate one stable `request_id` and reuse it for every retry of the same logical mutation. Never reuse it with changed input.
3. For `update` and `delete`, read the current record when its revision is not already present in trusted task context.
4. Send a password directly in the `password` field. Do not pre-encrypt it or send an encryption envelope. The MCP encrypts it before Elasticsearch storage.
5. Invoke one matching `account_management` action. Let the workflow normalize identities, validate the schema, apply revision CAS, enforce request-id idempotency, and check the caller's OAuth scopes.
6. Treat `conflict` as a fresh-decision boundary: read the new current record and reconsider the change. Never blindly overwrite it.
7. Request `include_password=true` only when the caller explicitly needs that exact credential. The response then contains the plaintext password; do not repeat it in summaries or durable records.

## Resource rules

- One DigitalHuman may own multiple accounts on the same platform. The same normalized platform and username identify one external account globally; the account cannot belong to two DigitalHumans at once.
- Platform and username are immutable after creation. Password and DigitalHuman ownership may be updated with revision CAS.
- The MCP runtime holds `ACCOUNT_KEYS_JSON` and `ACCOUNT_ACTIVE_KEY_ID`. Elasticsearch stores only an authenticated AES-256-GCM envelope.
- Lists and ordinary reads omit passwords. Exact `get` may return plaintext only when `include_password=true` and the caller has both `account:read` and `account:credentials:read`.
- Never put passwords into summaries, task records, website documents, evidence, logs, memory, or a `request_id`.
- Deletion preserves a non-secret tombstone, clears the encrypted credential, and permanently reserves the account identity.

## Boundaries

- This Skill manages data. It does not browse websites, receive email, solve challenges, or claim those actions succeeded.
- MCP caller identity and authorization come from the validated OAuth Access Token. `digital_human_id` is account data, not an authentication principal.
- The Search Stack MCP is an independent Rust service. It does not use Kibana Workflow or expose arbitrary Elasticsearch requests.
