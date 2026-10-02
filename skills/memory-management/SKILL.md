---
name: memory-management
description: Manage Role shared memory and DigitalHuman important memory through the Kibana MCP backed by Elasticsearch. Use for explicit memory create, read, update, list, or delete requests; do not use for task records, credentials, runtime sessions, or automatic memory extraction.
---

# Memory Management

Use Kibana MCP as the only data access path. Elasticsearch is the only writable truth for Role shared-memory entries and DigitalHuman important-memory entries. Do not call legacy memory repositories or keep memory copies in files, prompts, or task records.

## Required MCP surface

Before the first operation, inspect the connected Kibana MCP tool catalog. Use only:

- `serpvibe.role_memory`
- `serpvibe.digital_human_memory`

Read [references/mcp-contracts.md](references/mcp-contracts.md) before invoking either workflow for the first time in a task. If the required workflow or compatible schema is absent, stop and report the missing capability. Do not fall back to raw Elasticsearch writes or guessed tool IDs.

## Select the memory owner

- Use Role memory only for durable facts or experience intended for every DigitalHuman assigned to that Role.
- Use DigitalHuman memory only for durable facts belonging to one exact DigitalHuman.
- Do not copy the same fact into both scopes. If ownership is unclear, ask for the intended scope before writing.
- Persona, credentials, website records, task records, runtime Sessions, transcripts, checkpoints, and mechanically generated work history are not memory entries managed by this Skill.

## Workflow

1. Require an explicit user or trusted task request before creating, changing, or deleting memory. Never mine ordinary conversation or completed work automatically.
2. Resolve the exact `role_ref` or `digital_human_id`; never select an owner from a display name when more than one match exists.
3. For `update` and `delete`, read the current entry unless its revision is already present in trusted task context.
4. Invoke one named workflow with a stable `request_id`. Let the workflow enforce ownership, authorization, schema validation, idempotency, revision CAS, and tombstones.
5. On `conflict`, read the new version and reconsider. Do not overwrite the newer memory or silently merge different facts.
6. Return the stable `memory_ref`, scope, outcome, and revision. Do not reproduce unrelated memory entries.

## Memory quality

- Store one independently correctable fact or compact experience per entry.
- Preserve the user's meaning. Distinguish observed fact, user assertion, preference, and operational lesson using the workflow's `memory_kind`.
- Include a rationale or source reference when supplied; do not invent evidence.
- Correct an entry in place with its revision. Create a separate entry only when it is a distinct fact.
- Delete through the Workflow tombstone operation. Never delete an entire Role or DigitalHuman memory root.

## Boundaries

- This Skill does not change Role identity, Role persona, DigitalHuman identity, or Role membership.
- Runtime Session and work-history lifecycle remain mechanical and read-only to this Skill.
- Account passwords and other credentials belong only in the account store and must never enter memory.
- Skill instructions guide memory decisions; Kibana Workflows and Elasticsearch enforce permissions and consistency.
