---
name: website-management
description: Find and maintain websites and controlled tags with the Search Stack website_management tool. Use for catalog facts, not credentials, browser state, or task history.
---

# Website Management

Use only the exact MCP tool `website_management`. Do not use raw Elasticsearch, guessed tool names, or a local catalog copy. If the tool or required action is absent, stop and report it.

## Choose the operation

- `get`: resolve a canonical or alias URL to one website.
- `list`: browse by exploration status or controlled tags.
- `create`: add a website that is not already represented.
- `update`: replace or clear supported factual sections.
- `update_tags`: add or remove controlled tags without replacing a stale tag list.
- `delete`: retire the catalog record as a soft tombstone.
- Dimension/tag actions: inspect or maintain the controlled registry.

Inspect the live tool schema for exact fields. Use [references/tool-contract.json](references/tool-contract.json) only to verify generated schema, defaults, or scopes. Consult [references/mcp-contract.md](references/mcp-contract.md) for update, tag, projection, and concurrency semantics. Read [references/data-model.md](references/data-model.md) before writing aliases, exploration, quality, traffic, or evidence.

## Rules

- Pass observed URLs directly. Website identity is the normalized host, so scheme, port, path, query, fragment, case, and trailing dot are ignored. Do not strip `www` or invent aliases.
- This catalog identifies sites, not pages. Use `task_management` resource URLs when path or query distinguishes the item.
- Use `summary` for lists, `standard` for normal lookup, and `full` only when detailed evidence, traffic, or deletion data is needed. An omitted projected field is not proof that stored data is absent.
- Record observed facts only. Aliases must be verified; evidence should be concise and attributable. Keep `invalid` exploration as negative knowledge rather than deleting it.
- Use live `dimension.value` tag codes and active definitions. Query the registry instead of relying on a copied list.
- Every mutation needs a globally unique `request_id` that is never recycled; reuse it only for the identical retry. Updates, tag changes, deletion, and registry changes also need the current revision.
- On `conflict`, read current state and reconsider. Do not overwrite blindly.
- Keep credentials, browser sessions, task execution state, raw pages, and browsing transcripts out of website records.
