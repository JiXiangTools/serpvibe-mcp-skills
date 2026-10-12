#!/usr/bin/env python3
"""Install the public Serpvibe Skills from this checkout."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile


REPOSITORY = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPOSITORY / "skills"
DEFAULT_SKILLS = (
    "account-management",
    "proxy-manager",
    "task-management",
    "website-management",
)
PUBLISHED_SKILLS = (*DEFAULT_SKILLS, "browser-env-manager")
SKILL_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class InstallError(RuntimeError):
    pass


def default_destination() -> Path:
    codex_root = os.environ.get("CODEX_HOME")
    return (Path(codex_root) if codex_root else Path.home() / ".codex") / "skills"


def manifest_name(skill_root: Path) -> str:
    manifest = skill_root / "SKILL.md"
    if not manifest.is_file():
        raise InstallError(f"missing Skill manifest: {manifest}")
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if line.startswith("name:"):
            return line.partition(":")[2].strip()
    raise InstallError(f"missing Skill name: {manifest}")


def file_snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def install(skills: list[str], destination: Path) -> tuple[list[str], list[str]]:
    if len(skills) != len(set(skills)):
        raise InstallError("duplicate Skill name")
    sources: dict[str, Path] = {}
    for name in skills:
        if not SKILL_NAME.fullmatch(name) or name not in PUBLISHED_SKILLS:
            raise InstallError(f"unknown published Skill: {name}")
        source = SKILL_ROOT / name
        if manifest_name(source) != name:
            raise InstallError(f"Skill manifest name does not match directory: {name}")
        sources[name] = source

    destination = destination.expanduser()
    destination.mkdir(parents=True, exist_ok=True)
    pending: list[str] = []
    unchanged: list[str] = []
    for name, source in sources.items():
        target = destination / name
        if target.is_symlink():
            raise InstallError(f"refusing to replace symlinked Skill: {target}")
        if target.exists():
            if not target.is_dir() or file_snapshot(target) != file_snapshot(source):
                raise InstallError(f"refusing to overwrite changed Skill: {target}")
            unchanged.append(name)
        else:
            pending.append(name)

    staging = Path(tempfile.mkdtemp(prefix=".serpvibe-skills-", dir=destination))
    installed: list[str] = []
    try:
        for name in pending:
            shutil.copytree(sources[name], staging / name, copy_function=shutil.copy2)
        for name in pending:
            (staging / name).replace(destination / name)
            installed.append(name)
    except Exception:
        for name in reversed(installed):
            shutil.rmtree(destination / name)
        raise
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return installed, unchanged


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skill",
        action="append",
        choices=PUBLISHED_SKILLS,
        dest="skills",
        help="install one published Skill; repeat for multiple (default: Search Stack set)",
    )
    parser.add_argument("--destination", type=Path, default=default_destination())
    args = parser.parse_args(argv)
    try:
        installed, unchanged = install(args.skills or list(DEFAULT_SKILLS), args.destination)
    except (InstallError, OSError) as error:
        print(f"Skill installation failed: {error}", file=sys.stderr)
        return 1
    for name in installed:
        print(f"Installed {name} to {args.destination.expanduser() / name}")
    for name in unchanged:
        print(f"Already current: {args.destination.expanduser() / name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
