# Website data model

The formal source of truth is `docs/workflows/website-management.md`. This reference summarizes the facts exposed through the Skill.

## Website

```text
Website
  site_ref
  canonical_url
  normalized_host
  aliases[]
  name
  description
  notes?
  exploration
  tag_codes[]
  quality?
  traffic_observations[]
  evidence[]
  revision
  created_at
  updated_at
  deleted_at?
```

`normalized_host` is the website identity. Scheme, port, path, query, fragment, host case, and a trailing dot do not change that identity. `www` remains distinct unless recorded as a verified alias. This host-only identity is intentionally different from a real page/resource URL, whose path and query remain significant and case-preserving.

## Exploration

```text
ExplorationConclusion
  status: unexplored | valid | invalid
  conclusion
  reason_codes[]
  checked_at
  next_check_at?
```

`unexplored` means the migrated record still needs validation. `invalid` is active negative knowledge, not deletion.

## Aliases

```text
SiteAlias
  url
  normalized_host
  relationship: verified_alias | canonical_redirect
  checked_at
```

Aliases use the same normalization as canonical URLs and may be written only when verified. Shared names or root domains are not alias evidence.

## Quality, traffic, and evidence

```text
SiteQuality
  score?
  grade?
  conclusion
  checked_at

TrafficObservation
  metric
  value
  unit
  source
  observed_at

Evidence
  kind
  source_url
  summary
  observed_at
```

Keep only observed values and concise supporting facts. A failed collection attempt is not a traffic observation. Do not store complete pages, browser state, credentials, or task history.

## Controlled tags

Tags are stable `dimension.value` codes backed by TagDimension and TagDefinition resources owned by `website_management`. Website arrays contain codes only, are deduplicated, and support exact `tags_all` and `tags_any` filtering.

Only active definitions may be added. Archived tags may remain on existing records and may be removed.

## Projections

- Every projection includes `site_ref`, `canonical_url`, and `normalized_host` as the Website identity.
- `summary`: identity, name, description, exploration status, tags, quality summary, revision, and update time.
- `standard`: summary plus aliases, notes, full exploration, and full quality.
- `full`: standard plus traffic observations, evidence, and deletion details.

Projection affects only the response. Website storage remains one canonical model.
