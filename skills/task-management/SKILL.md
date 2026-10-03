---
name: task-management
description: Manage generic table-shaped tasks and their records through the Search Stack MCP. Use when work needs a dynamic schema, row-by-row progress, configurable deduplication, or coordinated processing by multiple bots; do not use it to perform the external work itself or store credentials and browser sessions.
---

# Task Management

Use Search Stack MCP as the only data access path. Elasticsearch is the only writable truth. Do not maintain a local task copy or use raw Elasticsearch tools.

## Required MCP surface

Before the first operation, inspect the connected MCP tool catalog and locate `task_management` by its exact advertised name. Do not guess a prefixed name.

Read [references/mcp-contract.md](references/mcp-contract.md) before invoking the workflow for the first time in a task. If the workflow is unavailable or its input schema is incompatible, stop and report the missing capability. Do not fall back to arbitrary Elasticsearch requests, ES|QL writes, index names, or guessed tool IDs.

## Workflow

1. Treat a Task as a dynamic table and a Record as one row. Never assume business columns such as URL, anchor text, email, or result fields.
2. When creating a Task, define only the columns needed for that work. Add one composite dedupe rule when duplicates matter; use global scope unless the requested workflow explicitly requires uniqueness only inside each Task.
3. For ordinary facts already known to be complete, use `create_record`.
4. Before an external side effect, use `reserve_record`. Perform the effect only after `record_reserved`, renew a short lease when needed, then call `finish_record` immediately.
5. Use `check_duplicate` only for inspection. A read-only check is never permission to perform an external effect.
6. Use one globally unique `request_id` for each mutation and reuse it after timeouts. Never reuse that ID for another mutation, including after the server's completed-receipt retention window has elapsed. For updates, read the current revision unless it is already present in trusted context.
7. Treat `conflict`, `busy`, `lease_lost`, and `uncertain` as fresh-decision boundaries. Never blindly retry an external effect.

## Recording rules

- Write one Record per logical row and finish it promptly; do not defer all results until the Task ends.
- Put scenario data in `values` according to the Task columns. The MCP validates types, derives normalization and fingerprints, and owns all system fields.
- Treat a `url` column as a real resource URL, not a website identity. Supply an absolute HTTP(S) URL. The MCP normalizes scheme/host, default ports, and fragments while preserving non-default ports, path case, query case, values, and parameter order. Do not reduce it to a host unless the business value is explicitly only a host.
- Do not modify values used by the dedupe rule. Create a new Record when the unique identity changes.
- Record `failed` only when the external effect is known not to have happened. If it may have happened, record `uncertain`, verify externally, then use `resolve_record`.
- Use `update_record` for later changes to non-dedupe columns. Deletes are business tombstones and do not erase completed dedupe history.
- Complete or cancel a Task only after all reserved and uncertain Records are resolved.

## Boundaries

- Read actions require `task:read`; task, record, reservation, and resolution mutations require `task:write`.
- This Skill manages task data. It does not execute the task, browse websites, receive email, solve challenges, or claim external actions succeeded.
- External execution requires the appropriate separate tool or Skill and the user's existing authorization.
- Account credentials, cookies, tokens, private keys, complete website or account documents, runtime sessions, transcripts, and memory do not belong in task records.
- Skill instructions guide decisions; MCP and Elasticsearch enforce schemas, identity, idempotency, revisions, claims, leases, tombstones, and allowed state transitions.
- Never expose raw index names or unrestricted query/write primitives to an untrusted Bot.
- The Search Stack MCP is an independent Rust service with compile-time Workflow registration. It is not a Kibana Workflow, a runtime script plugin, or an arbitrary Elasticsearch proxy.
