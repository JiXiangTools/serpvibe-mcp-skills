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
7. Create accounts with `url`, never `platform`. The workflow uses the same URL normalization as `website_management`, so paths, queries, host case, trailing dots, and ports do not change website identity.
8. Read credentials with exact `get` or by listing a `url`. Both return plaintext passwords by default; set `include_password=false` when credentials are not needed. Do not repeat returned passwords in summaries or durable records.

## Resource rules

- One DigitalHuman may own multiple accounts on the same website. The same normalized URL host and username identify one external account globally; the account cannot belong to two DigitalHumans at once.
- URL and username are immutable after creation. Password and DigitalHuman ownership may be updated with revision CAS.
- The MCP runtime holds `ACCOUNT_KEYS_JSON` and `ACCOUNT_ACTIVE_KEY_ID`. Elasticsearch stores only an authenticated AES-256-GCM envelope.
- Exact reads and URL lists require `account:read` and return plaintext passwords by default. `include_password=false` is a response projection for callers that do not need credentials, not a separate authorization boundary.
- Never put passwords into summaries, task records, website documents, evidence, logs, memory, or a `request_id`.
- Deletion preserves a non-secret tombstone, clears the encrypted credential, and permanently reserves the account identity.

## Boundaries

- This Skill manages data. It does not browse websites, receive email, solve challenges, or claim those actions succeeded.
- MCP caller identity and authorization come from the validated OAuth Access Token. `digital_human_id` is account data, not an authentication principal.
- The Search Stack MCP is an independent Rust service. It does not use Kibana Workflow or expose arbitrary Elasticsearch requests.
