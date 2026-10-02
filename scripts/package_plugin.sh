#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_ROOT="${PLUGIN_OUTPUT_ROOT:-$ROOT/target/plugins}"

die() {
    echo "plugin packaging failed: $*" >&2
    exit 1
}

[[ $# -ge 2 ]] || die "usage: $0 <release-id> <workflow> [workflow ...]"
RELEASE_ID="$1"
shift
[[ "$RELEASE_ID" =~ ^[A-Za-z0-9._-]+$ ]] || die "invalid release ID"
[[ -f "$ROOT/plugin.json" ]] || die "missing plugin.json"
jq -e '
    .name == "serpvibe-search-stack"
    and (.version | type == "string" and length > 0)
    and (.description | type == "string" and length > 0)
    and (.author.name | type == "string" and length > 0)
' "$ROOT/plugin.json" >/dev/null || die "invalid plugin manifest"

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
cp "$ROOT/plugin.json" "$PACKAGE/plugin.json"
if [[ -f "$ROOT/mcp.json" ]]; then
    cp "$ROOT/mcp.json" "$PACKAGE/mcp.json"
fi

for workflow in "$@"; do
    case "$workflow" in
        account_management) skill="account-management"; dependency="search-stack-mcp" ;;
        website_management) skill="website-management"; dependency="search-stack-mcp" ;;
        task_management) skill="task-management"; dependency="search-stack-mcp" ;;
        memory_management) skill="memory-management"; dependency="kibana" ;;
        *) die "no skill mapping for enabled workflow: $workflow" ;;
    esac
    source_dir="$ROOT/skills/$skill"
    [[ -f "$source_dir/SKILL.md" ]] || die "missing skill manifest: $source_dir/SKILL.md"
    manifest_name="$(sed -n 's/^name:[[:space:]]*//p' "$source_dir/SKILL.md" | head -n 1)"
    [[ "$manifest_name" == "$skill" ]] || die "skill name mismatch for $skill"
    [[ -f "$source_dir/agents/openai.yaml" ]] || die "missing OpenAI metadata for $skill"
    rg -q "value:[[:space:]]*\"$dependency\"" "$source_dir/agents/openai.yaml" \
        || die "$skill does not depend on $dependency"
    cp -a "$source_dir" "$PACKAGE/skills/$skill"
done

CONTENT_SHA256="$(
    cd "$PACKAGE"
    find . -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum | awk '{print $1}'
)"
WORKFLOWS_JSON="$(jq -cn --args '$ARGS.positional' "$@")"
jq -n \
    --arg release_id "$RELEASE_ID" \
    --arg content_sha256 "$CONTENT_SHA256" \
    --argjson workflows "$WORKFLOWS_JSON" \
    '{release_id: $release_id, content_sha256: $content_sha256, workflows: $workflows}' \
    >"$PACKAGE/build.json"

mv "$PACKAGE" "$DESTINATION"
echo "$DESTINATION"
