# Repository Instructions

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

