# Website lookup and update rules

Exact actions and fields come from [tool-contract.json](tool-contract.json) or the live MCP schema.

## Identity and projections

- Canonical and alias lookup uses exact normalized-host identity, never full-text matching. URL input may omit the scheme; `www` stays distinct.
- `matched_by` reports `canonical` or `alias`.
- Every projection includes site identity. `summary` is the list default, `standard` is the get default, and explicit `full` adds traffic, evidence, and deletion details.

## Updates

- In a patch, omission means unchanged, `null` clears a nullable value, and a supplied section or collection replaces that whole section. Tags change only through `update_tags`.
- `delete` hides the website from default reads but retains its identity. Keep `invalid` exploration records instead of deleting them.

## Controlled tags

- Prefer existing tags from `list_tags`. If none fits, use `create_tag` explicitly; use `create_dimension` first only if the needed dimension does not exist. Registry maintenance uses the same `website:write` permission as website writes. Website tagging never creates registry entries implicitly.
- Use the complete registered `tag_code`, including every dot: `access.product_submission.free_path` belongs to dimension `access`, with value `product_submission.free_path`. Do not shorten it or infer parent tags.
- Adding tags through website `create` or `update_tags` requires both the tag and its dimension to be active. Check tag status with `list_tags` and dimension status and `selection_mode` with `list_dimensions`; an active tag alone does not establish that its dimension is active.
- `update_tags` rejects overlapping add/remove codes and enforces single-value dimensions. Replace a single-valued selection by removing the old code and adding the new one in the same request, using the website's current revision.
- Archived tags can remain on websites, be queried, or be removed, but cannot be added. Archiving a dimension does not rewrite its tags or existing website references; `list_tags` reports the tag's own status, not the dimension's status.
- Website filters match complete codes, not prefixes. `tags_all` requires every code; `tags_any` requires at least one. If both are present, both predicates must hold. Filters can find historical references to archived tags.
