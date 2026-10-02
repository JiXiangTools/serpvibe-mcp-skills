# Serpvibe Search Stack Skills

Public Agent Plugin package for Serpvibe's typed business workflows.

## Included skills

- `account-management`: manage encrypted account records.
- `website-management`: query and maintain the shared website catalog.
- `task-management`: manage dynamic tasks and row-level processing state.
- `memory-management`: manage Role and DigitalHuman memory through Kibana MCP.

The first three skills use the public `search-stack-mcp` connection declared in
`mcp.json`. `memory-management` requires a separately configured `kibana` MCP
connection and is not provided by the public Search Stack MCP endpoint.

## Repository boundary

This repository contains instructions, public tool contracts, and connection
metadata only. It must not contain Elasticsearch credentials, OAuth secrets,
account encryption keys, deployment configuration, or MCP server source code.

## Install in Codex

The repository is public and can be installed without a GitHub token or SSH
credentials.

### Ask Codex to install the skills

Invoke `$skill-installer` and provide this repository:

```text
Install all skills from https://github.com/JiXiangTools/serpvibe-mcp-skills
```

### Install all four skills from the command line

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-installer/scripts/install-skill-from-github.py" \
  --repo JiXiangTools/serpvibe-mcp-skills \
  --ref main \
  --path skills/account-management \
         skills/website-management \
         skills/task-management \
         skills/memory-management
```

### Install one skill

For example, install only `account-management`:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-installer/scripts/install-skill-from-github.py" \
  --url https://github.com/JiXiangTools/serpvibe-mcp-skills/tree/main/skills/account-management
```

The installer stops instead of overwriting an existing skill directory. Move
or remove an old installation only after preserving any local changes, then run
the command again. Newly installed skills are available to Codex on the next
turn or in a new chat.

Direct Skill installation copies the selected `skills/<name>` directories. It
does not install the repository-level `mcp.json`. The first three skills still
require a configured `search-stack-mcp` connection, and `memory-management`
requires a configured `kibana` MCP connection.

## Package the complete plugin

Build a complete local plugin directory with all four skills:

```bash
./scripts/package_plugin.sh 0.1.0 \
  account_management \
  website_management \
  task_management \
  memory_management
```

The generated directory is written under `target/plugins/` and contains a
content hash in `build.json`.
