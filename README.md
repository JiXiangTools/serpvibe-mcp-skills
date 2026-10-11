# Serpvibe Search Stack Plugin

Private Agent Plugin that installs Serpvibe's shared production Skills. It bundles
the authenticated Search Stack MCP connection required by the business-workflow
Skills; standalone Skills declare their own runtime boundary.

OAuth rollout status (2026-10-11): the authentication changes below are an
unpublished release candidate, not a completed production migration. Codex
0.159.2 silently drops the MCP server when the candidate's authentication
extension is present. Packaging is blocked by a real-client preflight until
the supported installation path is verified. Auth0 administration and a fresh
end-to-end login are still required. Existing production connections are not
changed by this candidate.

## Included skills

- `account-management`: manage URL-keyed credentials and operate server-side registration, login, credential injection, and password changes.
- `website-management`: query and maintain the shared website catalog.
- `task-management`: manage dynamic tasks and row-level processing state.
- `proxy-manager`: acquire, release, and report failures for proxy leases from the dedicated trusted-LAN Proxy Manager service.

The installable `plugin/` tree exposes exactly these four directories from
`plugin/skills/`. The account, website, and task Skills use the authenticated
`search-stack-mcp` connection declared in `plugin/mcp.json`. `proxy-manager` uses
the LAN service URL supplied by the user or `PROXY_MANAGER_URL` and has no MCP
dependency.

The Search Stack MCP connection uses OAuth 2.1 discovery. Clients receive
short-lived Bearer Tokens and never receive the MCP server's Elasticsearch API
key. Account, website, and task read/write permissions are granted as OAuth
scopes by the service administrator.

The installed MCP surface contains exactly eight tools:
`account_read`, `account_write`, `account_browser`, `website_read`,
`website_write`, `task_read`, `task_write`, and `task_check_duplicate`.
The `*_management` names are internal Workflow IDs, not callable tools.
Read-only tools are separated from state-changing tools so compatible hosts can
apply confirmation policy from each tool's actual intent.

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

This installs the four Skills and the `search-stack-mcp` connection from one
package. You can also open `/plugins` inside Codex and install
`serpvibe-search-stack` from the `Serpvibe Plugins` marketplace. Start a new
chat after installation so the new Skill catalog is loaded.

The approved candidate requires the service administrator to register the
stable OpenAI CIMD clients in Auth0 so installation and explicit login use the
same client identity. `plugin/mcp.json` fixes `client.mode = cimd`,
the MCP resource, and the exact base scopes: `offline_access` plus
`account:read`, `account:write`, `website:read`, `website:write`, `task:read`,
and `task:write`. It sets `defaultScopes` to an empty list and
`oidcEnabled = false`, so OpenAI hosts do not copy unrelated OIDC scopes from
Auth0 discovery. These extension fields require a host that actually supports
them; they are not effective in the tested Codex 0.159.2 portable-plugin parser.
For a separately configured Codex MCP connection, the explicit command below
has been verified to generate the approved authorization parameters (this is
not yet proof of successful login):

```bash
codex mcp login search-stack-mcp \
  --oauth-client-registration cimd \
  --scopes offline_access,account:read,account:write,website:read,website:write,task:read,task:write
```

The resulting access token is short-lived and scoped; the MCP server's
Elasticsearch API key is never distributed to the client.

Updating this plugin or its Skills does not by itself refresh a connector's
saved MCP tool schema. After a release changes tool names, descriptions,
actions, input schemas, or annotations,
refresh or reconnect `search-stack-mcp` and start a new session. In ChatGPT
Developer Mode, use `Refresh` on the plugin connection detail page. If another
client has no schema-refresh action, remove and re-add the MCP connection. Do
not substitute another action merely to satisfy an old local validator.

Verify that Codex sees the installation with:

```bash
codex plugin list --marketplace serpvibe-plugins
```

The intended ChatGPT setup is a private connection carrying the same non-OIDC
OAuth settings. Its actual private-installation UI must be verified before
publishing instructions. Adding only the MCP URL does not carry the candidate
manifest's authentication overrides and is not an acceptance test of them.

The marketplace behavior is declared in `.agents/plugins/marketplace.json`.
Its source is `plugin/`, so repository files outside that directory are never
installed with the plugin:

- `installation: AVAILABLE` exposes the plugin for an explicit, reviewable
  install.
- `authentication: ON_INSTALL` asks the host to authenticate the MCP connection
  during installation when that host provides an install-time connection UI.

The approved Auth0 rollout uses CIMD as the primary OpenAI registration path.
The administrator must import `https://chatgpt.com/oauth/codex/client.json` for
Linux and macOS Codex and `https://chatgpt.com/oauth/client.json` for ChatGPT Web,
grant each client the six business scopes shown above, and promote the login
connection to domain level. The candidate requests those scopes with
`offline_access` and deliberately
does not request `openid`, `profile`, `email`, or other OIDC scopes.
Dynamic Client Registration remains enabled for existing connections and
non-OpenAI clients; no existing DCR token or client must be removed merely to
install this plugin.

### Skills-only fallback

Use direct Skill installation only on clients that do not support Agent
Plugins. This installs the four instruction bundles but cannot install or
authenticate `mcp.json`:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-installer/scripts/install-skill-from-github.py" \
  --repo JiXiangTools/serpvibe-mcp-skills \
  --ref main \
  --path plugin/skills/account-management \
         plugin/skills/website-management \
         plugin/skills/task-management \
         plugin/skills/proxy-manager
```

Install one Skill the same way when only its instructions are needed:

For example, install only `account-management`:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-installer/scripts/install-skill-from-github.py" \
  --url https://github.com/JiXiangTools/serpvibe-mcp-skills/tree/main/plugin/skills/account-management
```

The direct installer stops instead of overwriting an existing Skill directory.
Direct installations of `account-management`, `website-management`, and
`task-management` require a separately configured `search-stack-mcp` connection.
`proxy-manager` instead requires the trusted-LAN service URL.

## Package the production plugin

Build a local plugin directory containing the four production Skills and the
MCP connection:

```bash
./scripts/package_plugin.sh
```

The release ID defaults to the version in `plugin/plugin.json`. The generated
directory is written under `target/plugins/`; `build.json` contains its content
hash and MCP contract version. Packaging fails if the three generated MCP
contracts do not share one version or if `plugin/skills/` contains anything
outside the four production Skills.

Packaging also runs `scripts/codex_plugin_preflight.py` against the local
release candidate using the installed Codex app-server. It fails if Codex
silently drops, adds, or renames an MCP server, or reads a different installed
copy. This test does not install the plugin or authenticate a user, and does
not replace fresh-login, token-refresh, and tool-call acceptance tests.

The authenticated tenant audit on 2026-10-11 found the stable ChatGPT CIMD
already registered and authorized, but the Codex CIMD was absent. After
owner-approved cleanup of four unused registrations, the official native Codex
CIMD was imported with an explicit grant for the six business permissions.
All five applications authorized by the owner's user were preserved and
rechecked. The unused M2M test application was subsequently deleted after the
owner's separate confirmation; six applications remain, including the new Codex
CIMD. Both official CIMD clients now pass the no-cookie authorization
preflight; existing DCR support remains enabled. This does not resolve the
portable-plugin parser issue described above, and must not be reported as
completed fresh-login, token-refresh, or tool-call acceptance.

The release target is one package for ChatGPT Web, macOS Codex, and Linux
Codex CLI; the OAuth candidate has not yet passed that cross-client acceptance.
`account_browser` runs Chrome on the MCP host, so none of those clients needs a
local password or browser extension.
