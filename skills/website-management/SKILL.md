---
name: website-management
description: Find and maintain websites and controlled tags with the Search Stack website_read and website_write tools. Use for catalog facts, not credentials, browser state, or task history.
---

# Website Management

Use `website_read` and `website_write` through MCP, not database access or a local catalog copy. Read the live schema for exact fields; [tool-contract.json](references/tool-contract.json) is the generated reference.

## Choose the operation

- `website_read`: `get` by canonical or alias `url`; `list` by exploration status or tags; `list_dimensions` and `list_tags` for available tag codes.
- `website_write`: `create`, `update`, `update_tags`, or `delete` a website; use dimension/tag actions to maintain the registry.

Read [update and lookup rules](references/mcp-contract.md) for patches and projections, and its [controlled tag rules](references/mcp-contract.md#controlled-tags) before choosing, creating, applying, or filtering tags. Read [field rules](references/data-model.md) before writing aliases, exploration, quality, traffic, or evidence.

## Call rules

- Reads require `website:read`; writes require `website:write`. On `insufficient_scope` or `oauth_scope_required`, let the host authorize; if still denied, report and stop. Do not reinstall or loop retries. Account and task permissions are not needed.
- Pass observed URLs directly. Website identity is the normalized host, so scheme, port, path, query, fragment, case, and trailing dot are ignored. Do not strip `www` or invent aliases.
- Before `create`, `get` the candidate URL. If found, reuse or update it; if not found, try `create`. Treat `website_exists` or `host_already_claimed` as a duplicate: inspect the existing Website and stop without changing the `request_id`.
- Use task records rather than website records for page-level tracking. Keep credentials, sessions, task execution state, raw pages, and browsing transcripts out of the catalog.
- Use `summary` for lists, `standard` for lookups, and `full` for traffic, evidence, or deletion details. Omitted fields may still be stored.
- Every mutation needs a globally unique `request_id` that is never recycled; reuse it only for the identical retry. Updates, tag changes, deletion, and registry changes also need the current revision.
- On `revision_conflict`, re-read before deciding. On `request_id_reused`, do not change the ID to force the write. After an ambiguous response or schema rejection, inspect state before retrying; keep the original ID and input for an identical retry.
- For a missing tool or cancellation, report the actual error and stop the affected operation; do not guess another tool name or replay a write whose delivery is unknown.
