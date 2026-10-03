# Unpublished Skill Sources

This directory is outside the installable `plugin/` tree and is never copied by
`scripts/package_plugin.sh` or the marketplace installer.

Staged Skill entrypoints use the `.staged` suffix so repository-wide Skill
scanners cannot load them accidentally. Publish one only after its MCP tools,
generated contract, installation documentation, and validation are ready; then
move it into `plugin/skills/<name>/` and restore the exact `SKILL.md` filename.
