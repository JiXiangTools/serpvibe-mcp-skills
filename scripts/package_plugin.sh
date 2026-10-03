#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLUGIN_ROOT="$ROOT/plugin"
OUTPUT_ROOT="${PLUGIN_OUTPUT_ROOT:-$ROOT/target/plugins}"
PRODUCTION_WORKFLOWS=(account_management website_management task_management)
EXPECTED_SKILLS=$'account-management\ntask-management\nwebsite-management'

die() {
    echo "plugin packaging failed: $*" >&2
    exit 1
}

[[ $# -le 1 ]] || die "usage: $0 [release-id]"
[[ -f "$PLUGIN_ROOT/plugin.json" ]] || die "missing plugin/plugin.json"
[[ -f "$PLUGIN_ROOT/mcp.json" ]] || die "missing plugin/mcp.json"
jq -e '
    .name == "serpvibe-search-stack"
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
mkdir -p "$PACKAGE/skills"
cp "$PLUGIN_ROOT/plugin.json" "$PACKAGE/plugin.json"
cp "$PLUGIN_ROOT/mcp.json" "$PACKAGE/mcp.json"

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
    cp -a "$source_dir" "$PACKAGE/skills/$skill"
done

CONTENT_SHA256="$(
    cd "$PACKAGE"
    find . -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum | awk '{print $1}'
)"
WORKFLOWS_JSON="$(jq -cn --args '$ARGS.positional' "${PRODUCTION_WORKFLOWS[@]}")"
jq -n \
    --arg release_id "$RELEASE_ID" \
    --arg content_sha256 "$CONTENT_SHA256" \
    --argjson workflows "$WORKFLOWS_JSON" \
    '{release_id: $release_id, content_sha256: $content_sha256, workflows: $workflows}' \
    >"$PACKAGE/build.json"

mv "$PACKAGE" "$DESTINATION"
echo "$DESTINATION"
