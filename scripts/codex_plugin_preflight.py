#!/usr/bin/env python3
"""Reject a package when the actual Codex parser silently drops its MCP servers.

Uses plugin/read only: no installation, authentication, or MCP tool calls.
This proves server discovery, not OAuth login or authentication-field support.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import selectors
import subprocess
import sys
import time


class PreflightError(RuntimeError):
    pass


def validate_plugin(response: dict, expected: list[str], plugin_root: Path) -> None:
    if "error" in response:
        raise PreflightError("Codex plugin/read failed; the package cannot be released")
    plugin = response.get("result", {}).get("plugin", {})
    actual = plugin.get("mcpServers")
    if not isinstance(actual, list) or sorted(actual) != sorted(expected):
        raise PreflightError(
            f"Codex did not load the declared MCP servers: expected {expected!r}, "
            f"got {actual!r}. Check unsupported mcp.json fields; do not publish."
        )
    source = plugin.get("summary", {}).get("source", {})
    path = source.get("path")
    if source.get("type") != "local" or not isinstance(path, str):
        raise PreflightError("Codex did not inspect the local release candidate")
    if Path(path).resolve() != plugin_root.resolve():
        raise PreflightError("Codex inspected a different package, not the release candidate")


def read_plugin(codex: str, marketplace: Path, plugin_name: str, timeout: float) -> dict:
    with subprocess.Popen(
        [codex, "app-server", "--stdio"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    ) as process:
        assert process.stdin is not None and process.stdout is not None
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ)
        buffer = b""

        def call(identifier: int, method: str, params: dict) -> dict:
            nonlocal buffer
            request = {"id": identifier, "method": method, "params": params}
            process.stdin.write(json.dumps(request).encode() + b"\n")
            process.stdin.flush()
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    response = json.loads(line)
                    if response.get("id") == identifier:
                        return response
                if not selector.select(timeout=min(1, max(0, deadline - time.monotonic()))):
                    continue
                chunk = os.read(process.stdout.fileno(), 65536)
                if not chunk:
                    raise PreflightError(f"Codex exited during {method}")
                buffer += chunk
                if len(buffer) > 4 * 1024 * 1024:
                    raise PreflightError("Codex returned an oversized protocol message")
            raise PreflightError(f"Codex timed out during {method}")

        try:
            initialized = call(1, "initialize", {
                "clientInfo": {"name": "serpvibe-plugin-preflight", "version": "1"},
                "capabilities": {"experimentalApi": True},
            })
            if "error" in initialized:
                raise PreflightError("Codex app-server initialization failed")
            process.stdin.write(b'{"method":"initialized"}\n')
            process.stdin.flush()
            return call(2, "plugin/read", {
                "marketplacePath": str(marketplace.resolve()),
                "pluginName": plugin_name,
            })
        finally:
            selector.close()
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


def main(argv: list[str] | None = None) -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex", default="codex")
    parser.add_argument("--repository", type=Path, default=root)
    parser.add_argument("--timeout-seconds", type=float, default=30)
    args = parser.parse_args(argv)
    try:
        if args.timeout_seconds <= 0:
            raise PreflightError("timeout must be positive")
        plugin_root = args.repository.resolve() / "plugin"
        manifest = json.loads((plugin_root / "plugin.json").read_text())
        mcp = json.loads((plugin_root / "mcp.json").read_text())
        expected = list(mcp["mcpServers"])
        if not expected:
            raise PreflightError("Search Stack must declare at least one MCP server")
        version = subprocess.run(
            [args.codex, "--version"], check=True, capture_output=True, text=True,
            timeout=args.timeout_seconds,
        ).stdout.strip()
        response = read_plugin(
            args.codex, args.repository / ".agents/plugins/marketplace.json",
            manifest["name"], args.timeout_seconds,
        )
        validate_plugin(response, expected, plugin_root)
    except (PreflightError, OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(f"Codex plugin preflight failed: {error}", file=sys.stderr)
        return 1
    print(f"Codex plugin preflight passed ({version}): {', '.join(expected)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
