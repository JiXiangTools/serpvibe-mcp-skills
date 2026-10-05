---
name: website-management
description: Find and maintain websites and controlled tags with the Search Stack website_read and website_write tools. Use for catalog facts, not credentials, browser state, or task history.
---

# Website Management

Use only the exact MCP tools `website_read` and `website_write`. Do not use the internal Workflow ID `website_management` as a tool name. Do not use raw Elasticsearch, guessed tool names, or a local catalog copy. If a required tool/action is absent, or the connector validates it as another action, stop and refresh or reconnect the MCP before starting a new session; updating this Skill alone does not refresh tool schemas.

## Choose the operation

- `website_read` with `get`: resolve a canonical or alias URL to one website.
- `website_read` with `list`: browse by exploration status or controlled tags.
- `website_read` with `list_dimensions` or `list_tags`: inspect the controlled registry.
- `website_write` with `create`: add a website that is not already represented.
- `website_write` with `update`: replace or clear supported factual sections.
- `website_write` with `update_tags`: add or remove controlled tags without replacing a stale tag list.
- `website_write` with `delete`: retire the catalog record as a soft tombstone.
- `website_write` with dimension/tag mutations: maintain the controlled registry.

Inspect the live tool schema for exact fields. Use [references/tool-contract.json](references/tool-contract.json) only to verify generated schema, defaults, or scopes. Consult [references/mcp-contract.md](references/mcp-contract.md) for update, tag, projection, and concurrency semantics. Read [references/data-model.md](references/data-model.md) before writing aliases, exploration, quality, traffic, or evidence.

## Rules

- Pass observed URLs directly. Website identity is the normalized host, so scheme, port, path, query, fragment, case, and trailing dot are ignored. Do not strip `www` or invent aliases.
- This catalog identifies sites, not pages. Use Task Record resource URLs when path or query distinguishes the item.
- Use `summary` for lists, `standard` for normal lookup, and `full` only when detailed evidence, traffic, or deletion data is needed. An omitted projected field is not proof that stored data is absent.
- Record observed facts only. Aliases must be verified; evidence should be concise and attributable. Keep `invalid` exploration as negative knowledge rather than deleting it.
- Use live `dimension.value` tag codes and active definitions. Query the registry instead of relying on a copied list.
- Every mutation needs a globally unique `request_id` that is never recycled; reuse it only for the identical retry. Updates, tag changes, deletion, and registry changes also need the current revision.
- A connector-side schema rejection does not authorize a new `request_id` or a substitute action. After refresh, retry the identical request with its original ID; if delivery was ambiguous, inspect current state first.
- On `conflict`, read current state and reconsider. Do not overwrite blindly.
- Keep credentials, browser sessions, task execution state, raw pages, and browsing transcripts out of website records.
