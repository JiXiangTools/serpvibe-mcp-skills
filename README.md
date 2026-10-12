# Serpvibe Skills

Public, canonical Skill source for Serpvibe workflows. This repository publishes
instructions and generated tool-contract references only. MCP services, remote
connection settings, OAuth, deployment, and runtime code stay in their owning
projects.

## One-request installation

In Codex, ask:

> Use `$skill-installer` to install `account-management`, `proxy-manager`,
> `task-management`, and `website-management` from
> `JiXiangTools/serpvibe-mcp-skills` under `skills/<skill-name>`.

The installer can fetch all four paths in one operation. Open a new conversation
after installation so the newly installed Skills are discovered.

For an already cloned checkout, the equivalent local installation is:

```bash
python3 scripts/install_skills.py
```

Use `--destination <skills-directory>` for another Skill root. The installer
is idempotent for identical copies and refuses to overwrite a changed or
symlinked destination.

This installs Skill instructions only. It never builds a plugin, edits an MCP
connection, starts a server, or copies credentials.

## Published Skills

- `account-management`: account records and server-side registration, login,
  credential injection, and password changes through `search-stack-mcp`.
- `website-management`: website catalog and controlled tags through
  `search-stack-mcp`.
- `task-management`: table-shaped tasks, row results, reservations, and
  duplicate checks through `search-stack-mcp`.
- `proxy-manager`: leases from the independent trusted-LAN proxy service.
- `browser-env-manager`: managed browser environments through the Browser
  Environment Manager service. It is published independently and is not part of
  the default Search Stack installation above.

The three Search Stack business Skills declare the dependency name
`search-stack-mcp`. The MCP project owns its remote URL, OAuth settings, tool
schemas, deployment, and connection instructions. Installing a Skill does not
create or authenticate that connection.

## Repository boundary

Canonical Skill source lives at `skills/<skill-name>/`. Unpublished work stays
under `staging/unpublished-skills/` and is not installable.

Generated `references/tool-contract.json` files are synchronized from the
owning MCP implementation. They are usage references, not a second service
contract. Skill content must describe how to call the exposed tools without
copying server architecture or client-specific installation logic.

There is intentionally no plugin marketplace, MCP manifest, native adapter, or
package builder in this repository. A client connects to each remote MCP service
through that client's native connection mechanism.

Public MCP interfaces remain frozen under `AGENTS.md`. Updating a Skill cannot
replace server-side compatibility or authorization checks.
