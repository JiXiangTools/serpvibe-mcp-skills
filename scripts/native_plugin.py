#!/usr/bin/env python3
"""Generate the Codex-native packaging overlay from the portable source.

Only packaging is adapted. Skill files, server names, URL and requested scopes
come from the existing source. Never mix the two MCP formats at the output root:
Codex 0.159.2 prefers mcp.json, whose extension fields it cannot yet parse.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


# Codex's public native client identity, not a secret or a server allowlist.
CODEX_CIMD = "https://chatgpt.com/oauth/codex/client.json"


def native_documents(manifest: dict, mcp: dict, marketplace: dict) -> dict[str, dict]:
    metadata_fields = ("name", "version", "description", "author", "homepage", "repository", "license", "keywords")
    if set(manifest) - {"$schema", *metadata_fields}:
        raise ValueError("unsupported native manifest mapping")
    native_manifest = {
        key: manifest[key]
        for key in metadata_fields
        if key in manifest
    }
    for key in ("name", "version", "description"):
        if not isinstance(native_manifest.get(key), str) or not native_manifest[key]:
            raise ValueError(f"missing plugin {key}")
    native_manifest.update(skills="./skills/", mcpServers="./.mcp.json")
    servers = {}
    for name, server in mcp["mcpServers"].items():
        auth = server["extensions"]["com.openai"]["auth"]
        # Fail closed if future source changes cannot be represented faithfully.
        scopes = auth.get("baseScopes")
        if (
            set(server) != {"type", "url", "extensions"}
            or set(server["extensions"]) != {"com.openai"}
            or set(server["extensions"]["com.openai"]) != {"auth"}
            or server["type"] != "streamable-http"
            or not isinstance(server["url"], str)
            or not server["url"].startswith("https://")
            or not isinstance(scopes, list)
            or not scopes
            or any(not isinstance(scope, str) or not scope or any(c.isspace() for c in scope) for scope in scopes)
            or len(set(scopes)) != len(scopes)
            or any(scope in {"openid", "profile", "email"} for scope in scopes)
            or auth != {
                "type": "oauth", "client": {"mode": "cimd"},
                "resource": server["url"], "baseScopes": scopes,
                "defaultScopes": [], "oidcEnabled": False,
            }
        ):
            raise ValueError(f"unsupported native OAuth mapping for {name}")
        servers[name] = {
            "url": server["url"],
            "scopes": scopes,
            "oauth": {
                "client_id": CODEX_CIMD,
                "callback_url": "http://127.0.0.1/callback",
            },
        }
        # No oauth_resource override: native discovery already supplies it.
    if not servers:
        raise ValueError("plugin has no MCP servers")
    catalog = json.loads(json.dumps(marketplace))
    entries = catalog.get("plugins", [])
    if len(entries) != 1 or entries[0].get("name") != manifest["name"]:
        raise ValueError("expected one matching marketplace entry")
    entries[0]["source"] = {"source": "local", "path": "./"}
    return {
        ".codex-plugin/plugin.json": native_manifest,
        ".mcp.json": {"mcpServers": servers},
        ".agents/plugins/marketplace.json": catalog,
    }


def generate(repository: Path, output: Path) -> None:
    if any((output / name).exists() for name in ("plugin.json", "mcp.json")):
        raise ValueError("native output must not contain the portable manifests")
    documents = native_documents(
        json.loads((repository / "plugin/plugin.json").read_text()),
        json.loads((repository / "plugin/mcp.json").read_text()),
        json.loads((repository / ".agents/plugins/marketplace.json").read_text()),
    )
    for relative, document in documents.items():
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    generate(args.repository, args.output)


if __name__ == "__main__":
    main()
