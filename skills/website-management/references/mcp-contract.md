# Website lookup and update rules

Exact actions and fields come from [tool-contract.json](tool-contract.json) or the live MCP schema.

## Identity and projections

- Canonical and alias lookup uses exact normalized-host identity, never full-text matching. URL input may omit the scheme; `www` stays distinct.
- `matched_by` reports `canonical` or `alias`.
- Every projection includes site identity. `summary` is the list default, `standard` is the get default, and explicit `full` adds traffic, evidence, and deletion details.

## Updates and tags

- In a patch, omission means unchanged, `null` clears a nullable value, and a supplied section or collection replaces that whole section. Tags change only through `update_tags`.
- `tags_all` requires every code; `tags_any` requires at least one. If both are present, both predicates must hold.
- `update_tags` validates active definitions, rejects overlapping add/remove codes, and enforces single-value dimensions.

- `delete` hides the website from default reads but retains its identity. Keep `invalid` exploration records instead of deleting them.
