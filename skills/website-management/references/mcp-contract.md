# Website management MCP contract

The formal source of truth is `docs/workflows/website-management.md`. Use only the `website_management` MCP Tool.

## Website actions

```text
create
  request_id
  url
  name
  description
  exploration
  tag_codes[]?
  aliases[]?
  notes?
  quality?
  traffic_observations[]?
  evidence[]?

get
  url
  projection?: summary | standard | full = standard
  include_deleted?: boolean = false

list
  tags_all[]?
  tags_any[]?
  exploration_status?: unexplored | valid | invalid
  projection?: summary | standard | full = summary
  include_deleted?: boolean = false
  cursor?
  limit?

update
  request_id
  url
  expected_revision
  patch

update_tags
  request_id
  url
  expected_revision
  add_tag_codes[]?
  remove_tag_codes[]?

delete
  request_id
  url
  expected_revision
```

`get`, `update`, `update_tags`, and `delete` accept canonical or alias URLs. The Workflow applies site-identity normalization before exact keyword lookup and mutates the canonical Website. Scheme, port, path, query, fragment, host case, and a trailing dot do not affect this identity; `www` is not removed.

For update patches, an omitted field is unchanged and an explicit `null` clears a nullable field. A provided section or collection replaces that complete section. Tags change only through `update_tags`.

## Tag registry actions

```text
list_dimensions
  lifecycle_status?: active | archived
  cursor?
  limit?

list_tags
  dimension_code?
  lifecycle_status?: active | archived
  cursor?
  limit?

create_dimension
  request_id
  dimension_code
  display_name
  selection_mode: single | multiple
  description?

update_dimension
  request_id
  dimension_code
  expected_revision
  display_name?
  description?

archive_dimension
  request_id
  dimension_code
  expected_revision

create_tag
  request_id
  tag_code
  display_name
  description?

update_tag
  request_id
  tag_code
  expected_revision
  display_name?
  description?

archive_tag
  request_id
  tag_code
  expected_revision
```

The Workflow owns these resources. List actions are read-only; create, update, and archive actions require Elasticsearch write permission for the tag registry indices.

## URL results

```text
ok / website_found
  matched_by: canonical | alias
  website

not_found / website_not_found
```

URL input may omit the scheme. URL lookup never uses full-text analysis. This Tool answers which website a URL belongs to; it does not compare page/resource URLs. Page equality must preserve path and query, including their case and query ordering.

## Tag queries

`tags_all` requires every supplied code. `tags_any` requires at least one supplied code. When both are present, both conditions must hold. Tag fields use exact keyword matching.

`update_tags` requires at least one non-empty add or remove array. It validates active definitions, deduplicates additions and removals, rejects the same code in both lists, enforces single-value dimensions, and performs one Website revision CAS update.

## Projections

- Every projection returns `site_ref`, `canonical_url`, and `normalized_host`.
- `summary` is the default for list.
- `standard` is the default for get.
- `full` is explicit and includes traffic observations, evidence, and deletion details.

## Results and consistency

```text
outcome: ok | not_found | conflict | invalid | rejected | unauthorized | forbidden | unavailable
code
website? | websites?
matched_by?: canonical | alias
current_revision?
next_cursor?
```

Every mutation requires a globally unique stable `request_id`, reused only to retry the same normalized operation. A replay does not write again; reusing the ID for different input returns `rejected / request_id_reused`. Create uses normalized-host identity and create-only semantics. Update, tag change, delete, and registry update/archive actions require `expected_revision`. A stale revision returns `conflict / revision_conflict` without changing data.

A missing or invalid Bearer Token is rejected by the MCP transport as HTTP `401 / invalid_token`, before the Tool runs. A valid token without the action scope returns `forbidden / oauth_scope_required`. Elasticsearch authorization and connectivity failures map to `unavailable / workflow_unavailable`.

Delete is a soft tombstone. Default get and list omit deleted records; `invalid` exploration remains active catalog data.
