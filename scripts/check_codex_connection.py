#!/usr/bin/env python3
"""Check effective host configuration, without reading or printing credentials."""
import argparse
import json
from pathlib import Path
import sys
import subprocess
from codex_plugin_preflight import app_server_request, PreflightError


def check(connections, servers, manual_servers, allow_absent=False):
    if len(servers) != 1:
        raise ValueError('expected one packaged MCP connection')
    name, expected = next(iter(servers.items()))
    if name in manual_servers:
        raise ValueError('manual search-stack-mcp configuration shadows the plugin; remove that entry explicitly before installing (unrelated connections are untouched)')
    matches = [item for item in connections if item.get('name') == name]
    if not matches and allow_absent:
        return 'absent'
    if len(matches) != 1:
        raise ValueError('expected exactly one effective MCP connection')
    connection = matches[0]
    transport = connection.get('transport', {})
    if (
        connection.get('enabled') is not True
        or transport.get('type') != 'streamable_http'
        or transport.get('url') != expected['url']
        or transport.get('bearer_token_env_var')
        or transport.get('http_headers')
        or transport.get('env_http_headers')
        or transport.get('http_headers_helper')
    ):
        raise ValueError('conflicting search-stack-mcp configuration; remove its stale manual entry explicitly before installing (unrelated connections are untouched)')
    status = connection.get('auth_status')
    if status not in ('not_logged_in', 'o_auth'):
        raise ValueError('MCP connection must use native OAuth authentication')
    return status


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--codex', default='codex')
    parser.add_argument('--allow-absent', action='store_true')
    args = parser.parse_args()
    try:
        servers = json.loads((args.package / '.mcp.json').read_text())['mcpServers']
        config = app_server_request(args.codex, 'config/read', {
            'includeLayers': False, 'cwd': str(Path.cwd()),
        }, 30)
        if 'error' in config:
            raise ValueError('cannot inspect effective host configuration')
        manual = config['result']['config'].get('mcp_servers') or {}
        print(check(json.load(sys.stdin), servers, manual, args.allow_absent))
    except (OSError, ValueError, KeyError, TypeError, PreflightError, subprocess.SubprocessError) as error:
        print(f'Connection check failed: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
