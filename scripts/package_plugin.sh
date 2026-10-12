#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLUGIN_ROOT="$ROOT/plugin"
OUTPUT_ROOT="${PLUGIN_OUTPUT_ROOT:-$ROOT/target/plugins}"
PRODUCTION_WORKFLOWS=(account_management website_management task_management)
STANDALONE_SKILLS=(proxy-manager)
EXPECTED_SKILLS=$'account-management\nproxy-manager\ntask-management\nwebsite-management'
MCP_RESOURCE_URI="https://mcp-serpvibe.ficory.com/mcp"
OAUTH_PRIMARY_REGISTRATION="cimd"
OAUTH_COMPATIBLE_REGISTRATIONS=(cimd dcr)
OAUTH_SCOPES=(
    account:read
    account:write
    website:read
    website:write
    task:read
    task:write
)
OAUTH_BASE_SCOPES=(offline_access "${OAUTH_SCOPES[@]}")
OPENAI_CIMD_CLIENTS=(
    https://chatgpt.com/oauth/codex/client.json
    https://chatgpt.com/oauth/client.json
)

die() {
    echo "plugin packaging failed: $*" >&2
    exit 1
}

FORMAT=portable
if [[ "${1:-}" == --format ]]; then
    [[ $# -ge 2 ]] || die "--format requires portable or codex"
    FORMAT="$2"
    shift 2
fi
[[ "$FORMAT" == portable || "$FORMAT" == codex ]] || die "unknown package format: $FORMAT"
[[ $# -le 1 ]] || die "usage: $0 [--format portable|codex] [release-id]"
[[ -f "$PLUGIN_ROOT/plugin.json" ]] || die "missing plugin/plugin.json"
[[ -f "$PLUGIN_ROOT/mcp.json" ]] || die "missing plugin/mcp.json"
jq -e \
    --arg resource "$MCP_RESOURCE_URI" \
    --argjson base_scopes "$(jq -cn --args '$ARGS.positional' "${OAUTH_BASE_SCOPES[@]}")" '
    .["$schema"] == "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json"
    and (.mcpServers | keys) == ["search-stack-mcp"]
    and .mcpServers["search-stack-mcp"].type == "streamable-http"
    and .mcpServers["search-stack-mcp"].url == $resource
    and .mcpServers["search-stack-mcp"].extensions["com.openai"].auth == {
        type: "oauth",
        client: {mode: "cimd"},
        resource: $resource,
        baseScopes: $base_scopes,
        defaultScopes: [],
        oidcEnabled: false
    }
' "$PLUGIN_ROOT/mcp.json" >/dev/null || die "search-stack-mcp resource URI differs from the production OAuth contract"
rg -Fq '`client.mode = cimd`' "$ROOT/README.md" || \
    die "README must document CIMD as the packaged OpenAI client mode"
if rg -Fq -- '--oauth-client-registration dcr' "$ROOT/README.md"; then
    die "README must not make DCR the primary Codex login"
fi
rg -Fq '`oidcEnabled = false`' "$ROOT/README.md" || \
    die "README must document that packaged OpenAI login disables OIDC scopes"
for scope in "${OAUTH_SCOPES[@]}"; do
    rg -Fq "$scope" "$ROOT/README.md" || die "README is missing OAuth scope: $scope"
done
for client in "${OPENAI_CIMD_CLIENTS[@]}"; do
    rg -Fq "$client" "$ROOT/README.md" || die "README is missing OpenAI CIMD client: $client"
done
jq -e '
    .["$schema"] == "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
    and .name == "serpvibe-search-stack"
    and (.version | type == "string" and length > 0)
    and (.description | type == "string" and length > 0)
    and (.author.name | type == "string" and length > 0)
' "$PLUGIN_ROOT/plugin.json" >/dev/null || die "invalid plugin manifest"
PLUGIN_VERSION="$(jq -er '.version' "$PLUGIN_ROOT/plugin.json")"
RELEASE_ID="${1:-$PLUGIN_VERSION}"
[[ "$RELEASE_ID" =~ ^[A-Za-z0-9._-]+$ ]] || die "invalid release ID"

ACTUAL_SKILLS="$(
    find "$PLUGIN_ROOT/skills" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort
)"
[[ "$ACTUAL_SKILLS" == "$EXPECTED_SKILLS" ]] || {
    printf 'expected production skills:\n%s\nactual plugin skills:\n%s\n' \
        "$EXPECTED_SKILLS" "$ACTUAL_SKILLS" >&2
    die "root skills directory does not match the production install surface"
}

mkdir -p "$OUTPUT_ROOT"
DESTINATION="$OUTPUT_ROOT/serpvibe-search-stack-$RELEASE_ID"
if [[ "$FORMAT" == codex ]]; then
    DESTINATION="$DESTINATION-codex"
fi
[[ ! -e "$DESTINATION" ]] || die "plugin destination already exists: $DESTINATION"
TEMP_DIR="$(mktemp -d "$OUTPUT_ROOT/.build.XXXXXXXX")"

cleanup() {
    local exit_code=$?
    if [[ -n "${TEMP_DIR:-}" && -d "$TEMP_DIR" ]]; then
        rm -rf -- "$TEMP_DIR"
    fi
    exit "$exit_code"
}
trap cleanup EXIT

PACKAGE="$TEMP_DIR/package"
MCP_CONTRACT_VERSION=""
mkdir -p "$PACKAGE/skills"
if [[ "$FORMAT" == portable ]]; then
    cp "$PLUGIN_ROOT/plugin.json" "$PACKAGE/plugin.json"
    cp "$PLUGIN_ROOT/mcp.json" "$PACKAGE/mcp.json"
else
    python3 "$ROOT/scripts/native_plugin.py" --repository "$ROOT" --output "$PACKAGE"
fi

for workflow in "${PRODUCTION_WORKFLOWS[@]}"; do
    case "$workflow" in
        account_management) skill="account-management"; dependency="search-stack-mcp" ;;
        website_management) skill="website-management"; dependency="search-stack-mcp" ;;
        task_management) skill="task-management"; dependency="search-stack-mcp" ;;
        *) die "no skill mapping for enabled workflow: $workflow" ;;
    esac
    source_dir="$PLUGIN_ROOT/skills/$skill"
    [[ -f "$source_dir/SKILL.md" ]] || die "missing skill manifest: $source_dir/SKILL.md"
    manifest_name="$(sed -n 's/^name:[[:space:]]*//p' "$source_dir/SKILL.md" | head -n 1)"
    [[ "$manifest_name" == "$skill" ]] || die "skill name mismatch for $skill"
    [[ -f "$source_dir/agents/openai.yaml" ]] || die "missing OpenAI metadata for $skill"
    rg -q "value:[[:space:]]*\"$dependency\"" "$source_dir/agents/openai.yaml" \
        || die "$skill does not depend on $dependency"
    jq -e --arg dependency "$dependency" '.mcpServers[$dependency] != null' "$PLUGIN_ROOT/mcp.json" >/dev/null \
        || die "$skill dependency is missing from mcp.json: $dependency"
    contract_version="$(jq -er '.contract_version' "$source_dir/references/tool-contract.json")"
    [[ "$contract_version" =~ ^[1-9][0-9]*$ ]] || die "$skill has an invalid MCP contract version"
    if [[ -z "$MCP_CONTRACT_VERSION" ]]; then
        MCP_CONTRACT_VERSION="$contract_version"
    elif [[ "$MCP_CONTRACT_VERSION" != "$contract_version" ]]; then
        die "production Skills do not share one MCP contract version"
    fi
    cp -a "$source_dir" "$PACKAGE/skills/$skill"
done

for skill in "${STANDALONE_SKILLS[@]}"; do
    source_dir="$PLUGIN_ROOT/skills/$skill"
    [[ -f "$source_dir/SKILL.md" ]] || die "missing skill manifest: $source_dir/SKILL.md"
    manifest_name="$(sed -n 's/^name:[[:space:]]*//p' "$source_dir/SKILL.md" | head -n 1)"
    [[ "$manifest_name" == "$skill" ]] || die "skill name mismatch for $skill"
    [[ -f "$source_dir/agents/openai.yaml" ]] || die "missing OpenAI metadata for $skill"
    cp -a "$source_dir" "$PACKAGE/skills/$skill"
done

if [[ "$FORMAT" == codex ]]; then
    python3 "$ROOT/scripts/codex_plugin_preflight.py" --plugin-root "$PACKAGE" >&2 || \
        die "the installed Codex runtime cannot load the Codex adapter"
fi

CONTENT_SHA256="$(
    cd "$PACKAGE"
    find . -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum | awk '{print $1}'
)"
WORKFLOWS_JSON="$(jq -cn --args '$ARGS.positional' "${PRODUCTION_WORKFLOWS[@]}")"
OAUTH_REGISTRATIONS_JSON="$(jq -cn --args '$ARGS.positional' "${OAUTH_COMPATIBLE_REGISTRATIONS[@]}")"
OAUTH_SCOPES_JSON="$(jq -cn --args '$ARGS.positional' "${OAUTH_SCOPES[@]}")"
OAUTH_BASE_SCOPES_JSON="$(jq -cn --args '$ARGS.positional' "${OAUTH_BASE_SCOPES[@]}")"
OPENAI_CIMD_CLIENTS_JSON="$(jq -cn --args '$ARGS.positional' "${OPENAI_CIMD_CLIENTS[@]}")"
jq -n \
    --arg release_id "$RELEASE_ID" \
    --arg content_sha256 "$CONTENT_SHA256" \
    --argjson mcp_contract_version "$MCP_CONTRACT_VERSION" \
    --argjson workflows "$WORKFLOWS_JSON" \
    --arg resource "$MCP_RESOURCE_URI" \
    --arg primary_registration "$OAUTH_PRIMARY_REGISTRATION" \
    --argjson compatible_registrations "$OAUTH_REGISTRATIONS_JSON" \
    --argjson scopes "$OAUTH_SCOPES_JSON" \
    --argjson base_scopes "$OAUTH_BASE_SCOPES_JSON" \
    --argjson openai_cimd_clients "$OPENAI_CIMD_CLIENTS_JSON" \
    '{
        release_id: $release_id,
        content_sha256: $content_sha256,
        mcp_contract_version: $mcp_contract_version,
        workflows: $workflows,
        oauth: {
            resource: $resource,
            primary_client_registration: $primary_registration,
            compatible_client_registrations: $compatible_registrations,
            scopes: $scopes,
            base_scopes: $base_scopes,
            default_scopes: [],
            oidc_enabled: false,
            openai_cimd_clients: $openai_cimd_clients
        }
    }' \
    >"$PACKAGE/build.json"

mv "$PACKAGE" "$DESTINATION"
echo "$DESTINATION"
