#!/usr/bin/env bash
# Install an already-built native package using the host's own installer/OAuth.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CODEX_BIN="${CODEX_BIN:-codex}"
LOGIN=true
NO_BROWSER=false
[[ $# -ge 1 ]] || { echo "usage: $0 <native-package> [--no-login|--no-browser]" >&2; exit 2; }
PACKAGE="$(cd "$1" && pwd)"
shift
for option in "$@"; do
    case "$option" in
        --no-login) LOGIN=false ;;
        --no-browser) NO_BROWSER=true ;;
        *) echo "unknown option: $option" >&2; exit 2 ;;
    esac
done

[[ -f "$PACKAGE/.codex-plugin/plugin.json" && -f "$PACKAGE/.mcp.json" ]] || {
    echo 'This installer requires the optional Codex adapter; build it with scripts/package_plugin.sh --format codex. The default package is portable.' >&2
    exit 2
}
python3 "$ROOT/scripts/codex_plugin_preflight.py" --codex "$CODEX_BIN" --plugin-root "$PACKAGE"
SERVER_NAME="$(jq -er '.mcpServers | keys | if length == 1 then .[0] else error("expected one server") end' "$PACKAGE/.mcp.json")"

check_connection() {
    "$CODEX_BIN" mcp list --json | python3 "$ROOT/scripts/check_codex_connection.py" \
        --package "$PACKAGE" --codex "$CODEX_BIN" "$@"
}
# Check before installation and afterwards: manual/workspace config can shadow a
# plugin even when the host reports that plugin installation itself succeeded.
check_connection --allow-absent
python3 "$ROOT/scripts/install_codex_package.py" --package "$PACKAGE" --codex "$CODEX_BIN"
AUTH_STATUS="$(check_connection)"
if [[ "$LOGIN" == true ]]; then
    if [[ "$AUTH_STATUS" == "not_logged_in" ]]; then
        if [[ "$NO_BROWSER" == true ]]; then
            "$CODEX_BIN" mcp login "$SERVER_NAME" --no-browser
        else
            "$CODEX_BIN" mcp login "$SERVER_NAME"
        fi
    elif [[ "$AUTH_STATUS" == "o_auth" ]]; then
        echo 'Matching MCP connection is already authenticated.'
    else
        echo 'Installed connection does not support the required OAuth login.' >&2
        exit 1
    fi
fi
echo "Plugin installed. Open a new conversation to load its Skills."
