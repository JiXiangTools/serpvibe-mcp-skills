# Serpvibe Search Stack Plugin

Private Agent Plugin that installs Serpvibe's three production business-workflow
Skills and their authenticated MCP connection together.

## Included skills

- `account-management`: manage URL-keyed credentials and operate server-side registration, login, credential injection, and password changes.
- `website-management`: query and maintain the shared website catalog.
- `task-management`: manage dynamic tasks and row-level processing state.

The installable `plugin/` tree exposes exactly these three directories from
`plugin/skills/`. All three Skills use the authenticated `search-stack-mcp` connection
declared in `plugin/mcp.json`.

The Search Stack MCP connection uses OAuth 2.1 discovery. Clients receive
short-lived Bearer Tokens and never receive the MCP server's Elasticsearch API
key. Account, website, and task read/write permissions are granted as OAuth
scopes by the service administrator.

## Repository boundary

This repository contains instructions, tool contracts, and connection
metadata only. It must not contain Elasticsearch credentials, OAuth secrets,
account encryption keys, deployment configuration, or MCP server source code.

## Install in Codex

The repository may remain private. Codex needs ordinary GitHub or local
filesystem access to install it, but never needs an Elasticsearch key or an
MCP bearer token in the repository.

### Install the plugin (recommended)

Add the private GitHub or local Serpvibe marketplace:

```bash
codex plugin marketplace add JiXiangTools/serpvibe-mcp-skills --ref main
codex plugin add serpvibe-search-stack@serpvibe-plugins
```

This installs the three Skills and the `search-stack-mcp` connection from one
package. You can also open `/plugins` inside Codex and install
`serpvibe-search-stack` from the `Serpvibe Plugins` marketplace. Start a new
chat after installation so the new Skill catalog is loaded.

Complete OAuth when prompted. With Codex CLI, it can also be started explicitly:

```bash
codex mcp login search-stack-mcp \
  --oauth-client-registration dcr \
  --scopes account:read,account:write,website:read,website:write,task:read,task:write
```

The resulting access token is short-lived and scoped; the MCP server's
Elasticsearch API key is never distributed to the client.

Verify that Codex sees the installation with:

```bash
codex plugin list --marketplace serpvibe-plugins
```

In the ChatGPT desktop app, install the plugin from the Plugins Directory and
complete the connection prompt. In ChatGPT Web Developer Mode, add
`https://mcp-serpvibe.ficory.com/mcp` as a personal or workspace-only plugin;
public Plugin Directory submission is not required.

The marketplace behavior is declared in `.agents/plugins/marketplace.json`.
Its source is `plugin/`, so repository files outside that directory are never
installed with the plugin:

- `installation: AVAILABLE` exposes the plugin for an explicit, reviewable
  install.
- `authentication: ON_INSTALL` asks the host to authenticate the MCP connection
  during installation when that host provides an install-time connection UI.

The Auth0 tenant must enable Dynamic Client Registration under
`Settings > Advanced`. The `serpvibe-mcp` API must grant the six scopes shown in
the login command as the default user-delegated permissions for third-party
applications. That lets compatible OAuth clients register themselves
without receiving an Auth0 secret or the server's Elasticsearch key.

### Skills-only fallback

Use direct Skill installation only on clients that do not support Agent
Plugins. This installs the three instruction bundles but cannot install or
authenticate `mcp.json`:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-installer/scripts/install-skill-from-github.py" \
  --repo JiXiangTools/serpvibe-mcp-skills \
  --ref main \
  --path plugin/skills/account-management \
         plugin/skills/website-management \
         plugin/skills/task-management
```

Install one Skill the same way when only its instructions are needed:

For example, install only `account-management`:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-installer/scripts/install-skill-from-github.py" \
  --url https://github.com/JiXiangTools/serpvibe-mcp-skills/tree/main/plugin/skills/account-management
```

The direct installer stops instead of overwriting an existing Skill directory.
All directly installed Skills require a separately configured
`search-stack-mcp` connection.

## Package the production plugin

Build a local plugin directory containing the three production Skills and the
MCP connection:

```bash
./scripts/package_plugin.sh
```

The release ID defaults to the version in `plugin/plugin.json`. The generated
directory is written under `target/plugins/` and contains a content hash in
`build.json`. Packaging fails if `plugin/skills/` contains anything outside the
three production Skills.

The same package is used by ChatGPT Web, macOS Codex, and Linux Codex CLI.
`account_browser` runs Chrome on the MCP host, so none of those clients needs a
local password or browser extension.
