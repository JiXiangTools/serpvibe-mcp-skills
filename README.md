# Serpvibe Search Stack Plugin

Public Agent Plugin that installs Serpvibe's typed business workflow Skills and
their authenticated MCP connection together.

## Included skills

- `account-management`: manage encrypted account records.
- `website-management`: query and maintain the shared website catalog.
- `task-management`: manage dynamic tasks and row-level processing state.
- `memory-management`: manage Role and DigitalHuman memory through Search Stack MCP.

All four skills use the public `search-stack-mcp` connection declared in
`mcp.json`. The account, website, and task workflows are available now. The
memory skill and its connection can be installed now; memory operations become
available when the two memory workflows are published by the same MCP service.

The public Search Stack MCP connection uses OAuth 2.1 discovery. Clients receive
short-lived Bearer Tokens and never receive the MCP server's Elasticsearch API
key. Account, website, and task read/write permissions are granted as OAuth
scopes by the service administrator.

## Repository boundary

This repository contains instructions, public tool contracts, and connection
metadata only. It must not contain Elasticsearch credentials, OAuth secrets,
account encryption keys, deployment configuration, or MCP server source code.

## Install in Codex

The repository is public and can be installed without a GitHub token, SSH
credentials, MCP token, or Elasticsearch key.

### Automatic plugin installation

Add the public Serpvibe marketplace:

```bash
codex plugin marketplace add JiXiangTools/serpvibe-mcp-skills --ref main
```

Restart the ChatGPT desktop app or Codex after adding the marketplace. The
`serpvibe-search-stack` entry is installed by default. Installation loads all
four Skills and the `search-stack-mcp` URL from the same package, then starts
the Auth0 OAuth flow. The resulting access token is short-lived and scoped;
the MCP server's Elasticsearch API key is never distributed to the client.

The marketplace behavior is declared in `.agents/plugins/marketplace.json`:

- `installation: INSTALLED_BY_DEFAULT` installs the plugin when the marketplace
  is added or refreshed.
- `authentication: ON_INSTALL` asks the host to authenticate the MCP connection
  during installation.

### Skills-only fallback

Use direct Skill installation only on clients that do not support Agent
Plugins. This installs the four instruction bundles but cannot install or
authenticate `mcp.json`:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-installer/scripts/install-skill-from-github.py" \
  --repo JiXiangTools/serpvibe-mcp-skills \
  --ref main \
  --path skills/account-management \
         skills/website-management \
         skills/task-management \
         skills/memory-management
```

Install one Skill the same way when only its instructions are needed:

For example, install only `account-management`:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-installer/scripts/install-skill-from-github.py" \
  --url https://github.com/JiXiangTools/serpvibe-mcp-skills/tree/main/skills/account-management
```

The direct installer stops instead of overwriting an existing Skill directory.
All directly installed Skills require a separately configured
`search-stack-mcp` connection.

## Package the complete plugin

Build a complete local plugin directory with all four Skills and the MCP
connection:

```bash
./scripts/package_plugin.sh 0.2.0 \
  account_management \
  website_management \
  task_management \
  memory_management
```

The generated directory is written under `target/plugins/` and contains a
content hash in `build.json`.
