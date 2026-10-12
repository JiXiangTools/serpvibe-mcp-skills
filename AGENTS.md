# Repository Instructions

## Repository Role

This repository is the public source and installation home for reusable
Serpvibe Skills. Project repositories continue to own their application,
service, connection, authentication, deployment, and runtime code.

- Store cross-project Skill source under `skills/<skill-name>/`. Treat that copy
  as canonical; do not maintain divergent copies in application repositories.
- In each originating project, replace the local
  `<project-root>/skills/<skill-name>` directory with a symlink to this
  repository's canonical `skills/<skill-name>` directory. Use project-level
  links only; do not install these development links into `~/.codex/skills`.
- The only installable surface in this repository is `skills/<skill-name>/`.
  Do not add MCP connection manifests, host-specific plugin adapters, server
  runtime code, or client configuration here.
- Keep unfinished or unapproved work under `staging/unpublished-skills/`.
  Publish it only by moving the reviewed source into `skills/<skill-name>/`.

## Search Stack MCP Skill Content (Owner Requirement)

Keep the account, website, and task Skills focused on using MCP: tool/action
selection, inputs, results, and necessary operational constraints. Keep detailed
usage references conditional and avoid duplicating them in `SKILL.md`.

Do not include server architecture, implementation explanations, deployment,
MCP connection installation, migration history, or speculative error diagnoses
in these Skill bundles. Keep those in the owning project documentation.
Generated Skill references must preserve interface fields and behavior without
copying server architecture; do not alter the public MCP contract to simplify
documentation.

## External Interface Freeze (Owner Requirement)

Externally exposed interfaces are frozen once published. This includes MCP endpoint
URLs, tool names, actions, input and output schemas, required fields, defaults,
annotations, outcome and error codes, authentication scopes and metadata, HTTP
behavior relied on by clients, and the matching Skill or plugin contract.

- Before making any externally observable interface change, stop and obtain the
  user's explicit approval. First state the exact contract diff, affected clients,
  compatibility impact, migration plan, and removal plan. A general request to
  fix, upgrade, refactor, release, or deploy is not approval to alter the public
  contract.
- Additive changes also require explicit approval because new tools, actions,
  fields, or annotations can change host and model behavior.
- Without separately approved contract changes, every upgrade must remain
  backward-compatible. Previously valid calls must keep routing successfully with
  the same semantics; existing clients must not be forced to refresh, reconnect,
  reinstall, or start a new session merely to retain working behavior.
- Do not remove, rename, repartition, or replace an existing public interface just
  because a new interface exists. Keep the published surface operational until
  the user explicitly approves its deprecation and, separately, its removal.
- A contract-version bump, updated documentation, changed Skill instructions,
  cache headers, or reconnect guidance does not substitute for compatibility or
  approval.
- Before release, compare the generated public contract with the production
  contract, run regression tests for the previously published tools/list and
  tools/call shapes, and verify representative old-client calls against the
  release candidate. If compatibility cannot be maintained, do not deploy; ask
  the user for a decision.
