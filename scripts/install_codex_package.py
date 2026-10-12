#!/usr/bin/env python3
"""Install a validated local package with Codex's own marketplace/cache commands."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

from codex_plugin_preflight import app_server_request


def install(package, codex):
    package = package.resolve()
    manifest = json.loads((package / '.codex-plugin/plugin.json').read_text())
    catalog = json.loads((package / '.agents/plugins/marketplace.json').read_text())
    name = catalog['name']
    plugin = manifest['name']
    if [entry['name'] for entry in catalog['plugins']] != [plugin]:
        raise ValueError('expected only the packaged plugin in its marketplace')
    response = app_server_request(codex, 'config/read', {
        'includeLayers': False, 'cwd': str(Path.cwd()),
    }, 30)
    if 'error' in response:
        raise ValueError('cannot inspect configured marketplace source')
    configured = (response['result']['config'].get('marketplaces') or {}).get(name)

    def run(*args, check=True):
        return subprocess.run([codex, 'plugin', *args, '--json'], check=check,
                              text=True, capture_output=True, timeout=60)

    previous = None
    if configured:
        if configured.get('source_type') != 'local':
            raise ValueError('refusing to replace a non-local marketplace with a local package')
        source = Path(configured['source']).resolve()
        if source != package:
            old_catalog = json.loads((source / '.agents/plugins/marketplace.json').read_text())
            if old_catalog['name'] != name or [entry['name'] for entry in old_catalog['plugins']] != [plugin]:
                raise ValueError('refusing to replace a marketplace that contains other plugins')
            previous = source

    if previous:
        run('marketplace', 'remove', name)
    try:
        run('marketplace', 'add', str(package))
        run('add', f'{plugin}@{name}')
    except (OSError, subprocess.SubprocessError):
        if previous:
            # Restore through the host, including the installed files. Never
            # edit TOML/cache internals or remove an MCP connection/OAuth token.
            try:
                # An unsuccessful add may not have registered the new source.
                run('marketplace', 'remove', name, check=False)
                run('marketplace', 'add', str(previous))
                run('add', f'{plugin}@{name}')
            except (OSError, subprocess.SubprocessError) as rollback_error:
                raise RuntimeError(f'package update failed and previous package could not be restored: {previous}') from rollback_error
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--codex', default='codex')
    args = parser.parse_args()
    try:
        install(args.package, args.codex)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.SubprocessError) as error:
        print(f'Package installation failed: {error}', file=sys.stderr)
        if isinstance(error, subprocess.CalledProcessError):
            print(error.stderr, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
