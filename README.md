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

## Package

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

Individual skills can also be installed directly from GitHub:

```bash
python3 "$CODEX_HOME/skills/.system/skill-installer/scripts/install-skill-from-github.py" \
  --repo JiXiangTools/serpvibe-mcp-skills \
  --path skills/account-management \
         skills/website-management \
         skills/task-management \
         skills/memory-management
```
