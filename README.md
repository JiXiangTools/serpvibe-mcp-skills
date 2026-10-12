# Serpvibe Search Stack Plugin

Private Skill and MCP package. The repository contains instructions, generated
tool contracts and connection metadata, never server credentials or runtime code.

Release line (2026-10-12): contract 13. The server's live response header and
release manifest identify the deployed version. The owner approved fresh installations, without migration of the old
three Bots or a legacy permissions fallback. Linux Codex 0.159.2 has passed real
signup, website-only access and native token refresh. macOS, ChatGPT Web and
Cursor installation paths are not yet end-to-end verified. A separate real-host
regression against candidate authorization code also passed scope denial,
subsequent website operations, idempotency and native refresh with local OAuth/ES
fixtures; it is not another real Auth0 signup test.

## Included Skills

- `account-management`: URL-keyed credentials and server-side registration, login, injection and password changes.
- `website-management`: website catalog and controlled tags.
- `task-management`: tasks, row results, reservations and duplicate checks.
- `proxy-manager`: independent trusted-LAN proxy service; not a Search Stack MCP tool.

The three business Skills use `search-stack-mcp`. Memory management is not
published. Skills only describe how to use services; installation and architecture
belong outside their instruction bundles.

Public tools: `account_read`, `account_write`, `account_browser`, `website_read`,
`website_write`, `task_read`, `task_write`, `task_check_duplicate`.
Workflow IDs ending in `_management` are not tool names.

## Portable MCP + Skill package

The primary distribution is one portable package containing the same MCP
connection definition and Skills for every host. Build it from this repository:

```bash
bash scripts/package_plugin.sh
```

The default output is `target/plugins/serpvibe-search-stack-<release-id>` with
`plugin.json`, `mcp.json` and `skills/`, using the
[portable Agent Plugins layout](https://developers.openai.com/plugins/build/plugins).
The release ID defaults to `plugin/plugin.json`'s version; an explicit release ID
can be passed as the last argument. `build.json` records the content hash and MCP
contract version. No Codex executable, login or client profile is needed to build it.

Import this package through a host that supports its portable format, then use
that host's own OAuth login flow. If a host supports only MCP connections and
separate Skills, use the same MCP URL and the packaged Skill directories through
its supported installation mechanism. An MCP URL alone does not install Skills.
Do not copy another client's OAuth identity or invent an unsupported import UI.

Client-specific packaging is optional adaptation, not a different service,
permission model or Skill source. A host failing to parse this format does not
make the portable source obsolete. A successful build does not prove that every
host can import and authenticate it; host-specific end-to-end checks remain separate.

## Optional Codex adapter

Codex CLI 0.159.2 was observed to drop the MCP entry in the portable package.
For that host, explicitly build the adapter and use its native installer:

```bash
package="$(bash scripts/package_plugin.sh --format codex)"
bash scripts/install_codex_plugin.sh "$package"
```

This output ends in `-codex` and uses `.codex-plugin/plugin.json` and `.mcp.json`.
Only this optional build runs the actual Codex parser as a required preflight.
Its installer rejects a portable package before changing the client profile.

The installer uses the host's own plugin installation and OAuth commands.
`--no-browser` supports remote terminals; `--no-login` installs without login.
First login and consent require the user. No hand-entered Token, Client ID, scope,
Elasticsearch key or TOML edit is required for a clean installation.
Open a new conversation to load installed Skills.

Before and after installation, the script checks effective host configuration.
A manually configured `search-stack-mcp` would shadow the plugin: installation
fails clearly before changing the profile, even if that manual entry is disabled.
Remove only that explicitly identified entry and retry. The script never deletes
manual entries, overwrites other MCP connections or copies tokens.
Repeated installation of the same package is idempotent; a matching authenticated
plugin connection is not logged out.
To update, pass the newly built package to the same installer, even if its
directory has changed. It switches only this plugin's local marketplace source
using native Codex commands, refreshes installed files, and restores the previous
source and package if installation fails. Git-backed or multi-plugin marketplaces
are not silently replaced; unrelated connections and OAuth credentials are untouched.

Check the installation:

```bash
codex plugin list --marketplace serpvibe-plugins
codex mcp list
```

To start login manually after a files-only installation:

```bash
codex mcp login search-stack-mcp
```

## Source and package boundary

`plugin/plugin.json`, `plugin/mcp.json` and `plugin/skills/` are the shared source.
The repository marketplace still points to this portable source; it has not been
deleted or replaced with a Codex-only entry. Its usability depends on the host's
portable format support. It is not a working direct-install path for Codex 0.159.2.

`scripts/native_plugin.py` derives the native manifest, MCP configuration and
local marketplace without duplicating Skill content or permission definitions.
The Codex adapter is kept in a separate output directory, without a portable root
manifest, because mixing both formats was not correctly parsed by that CLI version.
The same marketplace, plugin and MCP server identities are preserved.

This packaging adapter does not add client-brand branches to the MCP server.
It is not the default distribution or a prerequisite for other hosts.

## Authentication and permissions

MCP URL: `https://mcp-serpvibe.ficory.com/mcp`.

The existing, namespaced OpenAI authentication extension specifies
`client.mode = cimd`, the MCP resource, empty
`defaultScopes`, and `oidcEnabled = false`. Requested scopes are
`offline_access`, `account:read`, `account:write`, `website:read`,
`website:write`, `task:read`, and `task:write`.
This extension does not bind other hosts to OpenAI's client identity. Other hosts
use standard MCP OAuth discovery with their own client registration. The optional
native generator maps these settings to Codex's supported fields.

The official public CIMD identities are
`https://chatgpt.com/oauth/codex/client.json` and
`https://chatgpt.com/oauth/client.json`. They are not secrets or a backend
allowlist. CIMD, DCR and pre-registration remain standard registration options;
they are not retained solely for old Bots. No registration is deleted by install.

Each user signs in independently. An application's permission grant only allows
it to request scopes. New users receive no business permissions automatically.
A website-only user is assigned `website:read` and `website:write` by the
administrator; installing other Skills does not grant their permissions.

Contract 13 authorizes only granted token scopes. Insufficient scope returns
HTTP 403 / `insufficient_scope`, preserving the MCP business error body.
`account_browser` needs both account scopes; Chrome and secret injection run
on the server and require no local browser/password extension.

## Other hosts and instruction-only installation

When only Skill instructions are needed, install the relevant directory from
`plugin/skills/<skill-name>/` using the host's Skill installer, and configure
MCP through that host's standard connection flow. Direct Skill installation does
not install or authenticate MCP. `proxy-manager` uses its own trusted-LAN URL.

Do not promise an untested private-plugin UI or universal plugin file format.
Do not require a client to impersonate Codex or ChatGPT to call the MCP server.

## Validation and release

```bash
python3 -m unittest discover -s scripts/tests -v
SERPVIBE_CODEX_INTEGRATION=1 python3 -m unittest discover -s scripts/tests -v
```

Portable packaging checks the declared format, unchanged connection/auth settings,
exact Skill set and matching tool-contract versions, without starting a host.
Tests build with Codex absent from PATH. The optional Codex adapter additionally
checks the actual Codex parser, exact tool connection and Skill set.
Isolated real-CLI tests cover repeat installation, different-directory upgrades,
same-directory updates, invalid packages, failed-upgrade recovery, conflicting
manual settings, and the generated OAuth request. They stop before login and do not replace the
separate real-user signup, tool-call and refresh acceptance.

Public interfaces are frozen under `AGENTS.md`. Normal updates cannot require
reconnection to retain existing behavior. The owner-approved fresh-install
cutover is specific to this release, not permission for future breaking changes.
Detailed server-side acceptance and deployment records live in the MCP repository,
not in the three usage Skills.
