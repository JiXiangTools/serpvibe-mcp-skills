---
name: website-management
description: Query and maintain the shared website catalog through Search Stack MCP. Use for URL lookup, controlled-tag search, website creation, factual updates, tag changes, and soft deletion; do not use for browser state, credentials, or task history.
---

# Website Management

Use `website_management` as the only website data path. Elasticsearch is the writable truth for the shared website catalog.

## Required MCP surface

Inspect the connected MCP catalog before the first operation and use only `website_management`.

Read [references/mcp-contract.md](references/mcp-contract.md) before the first call in a task. Read [references/data-model.md](references/data-model.md) before creating a website or changing aliases, exploration, quality, traffic, or evidence.

If the tool or compatible schema is absent, stop and report the missing capability. Do not fall back to raw Elasticsearch requests, guessed tool IDs, or local website copies.

## Basic use

- Use `get` to look up a website by canonical or alias URL.
- Use `list` with `tags_all` or `tags_any` to query websites by controlled tags.
- Use `create` to add a website that is not already present.
- Use `update` to change supported website facts with the current revision.
- Use `update_tags` to add or remove controlled tags with the current revision.
- Use `delete` only when the catalog record should become a soft tombstone.

## URL lookup

Pass the URL exactly as observed, with or without `http://` or `https://`. The Workflow normalizes it and performs exact canonical-host and alias-host matching. Do not implement URL normalization in prompts, use full-text URL search, strip `www`, or guess alias relationships.

`get` returning `not_found` means no active website matches the normalized canonical or alias host. A path-level URL matches its website record; this catalog does not track individual pages.

## Read projections

- Use `summary` for ordinary tag search.
- Use `standard` for normal URL lookup and site selection.
- Use `full` only when traffic observations, evidence, or deleted-state details are required.

Omitted fields may be outside the requested projection; do not treat them as missing stored facts.

## Writes

- Give every mutation a stable `request_id`. Reuse it only when retrying the same normalized operation.
- Preserve facts supported by actual exploration or use. Do not fill unknown values with guesses.
- Keep aliases, exploration conclusions, quality, traffic observations, and evidence attributable and current.
- Read the current revision before update, tag change, or delete unless it is already available in trusted task context.
- Use `update_tags` with explicit additions and removals; never replace tags from a stale copy.
- On `conflict`, read the current record and reconsider. Do not blindly retry or overwrite.
- Keep `invalid` websites as useful negative knowledge. Delete only when the catalog record itself should be retired.

## Tags

Use controlled `dimension.value` codes. Query the live tag registry when the appropriate code is not already known; do not keep a copied tag list in the Skill. Only active definitions may be added to a website.

## Boundaries

- Website records may contain aliases, name, description, notes, exploration conclusions, controlled tags, quality, traffic observations, and supporting evidence.
- Keep browser sessions, account credentials, task claims, retries, and complete task history outside website records.
- Store concise current facts and evidence references, not copied web pages or raw browsing transcripts.
- Skill instructions guide decisions; the MCP Workflow and Elasticsearch enforce normalization, permissions, revision CAS, and soft deletion.
