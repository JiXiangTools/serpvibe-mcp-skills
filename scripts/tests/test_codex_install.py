"""Opt-in real CLI test; no user credentials, token exchange or business writes.

Run SERPVIBE_CODEX_INTEGRATION=1 python3 -m unittest discover -s scripts/tests.
Uses temporary profiles and stops OAuth before login. It is not a fresh-user or
refresh-token acceptance test.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import selectors
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import tomllib
import unittest
from urllib.parse import parse_qs, urlsplit


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("native_plugin", ROOT / "scripts/native_plugin.py")
assert SPEC is not None and SPEC.loader is not None
native = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(native)


@unittest.skipUnless(os.environ.get("SERPVIBE_CODEX_INTEGRATION") == "1", "opt-in real Codex installation test")
class CodexInstallTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="serpvibe-codex-install-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.profile = self.root / "profile"
        self.profile.mkdir()
        self.config = self.profile / "config.toml"
        self.config.write_text('[mcp_servers.unrelated]\nurl = "https://example.invalid/mcp"\nenabled = false\n')
        self.env = {**os.environ, "CODEX_HOME": str(self.profile)}
        self.package = self.root / "package"
        native.generate(ROOT, self.package)
        shutil.copytree(ROOT / "plugin/skills", self.package / "skills")
        self.expected = json.loads((self.package / ".mcp.json").read_text())["mcpServers"]["search-stack-mcp"]

    def run_cli(self, *args):
        result = subprocess.run(["codex", *args], cwd=self.root, env=self.env, capture_output=True,
                                text=True, timeout=40, check=True)
        return json.loads(result.stdout)

    def install(self, package=None):
        subprocess.run(["bash", str(ROOT / "scripts/install_codex_plugin.sh"), str(package or self.package), "--no-login"],
                       cwd=self.root, env=self.env, capture_output=True, text=True, timeout=60, check=True)

    def update_package(self, package, version='0.4.12-test'):
        manifest = package / '.codex-plugin/plugin.json'
        document = json.loads(manifest.read_text())
        if version is not None:
            document['version'] = version
        manifest.write_text(json.dumps(document))
        skill = package / 'skills/website-management/SKILL.md'
        skill.write_text(skill.read_text() + '\nNew version test marker.\n')

    def assert_current_package(self, package):
        listing = self.run_cli('plugin', 'list', '--marketplace', 'serpvibe-plugins', '--json')
        self.assertEqual(len(listing['installed']), 1)
        installed = listing['installed'][0]
        self.assertTrue(installed['enabled'])
        expected = json.loads((package / '.codex-plugin/plugin.json').read_text())
        self.assertEqual(installed['version'], expected['version'])
        cache = self.profile / 'plugins/cache/serpvibe-plugins/serpvibe-search-stack'
        current = [path for path in cache.iterdir()
                   if json.loads((path / '.codex-plugin/plugin.json').read_text())['version'] == expected['version']]
        self.assertEqual(len(current), 1)
        for path in package.rglob('*'):
            if path.is_file():
                self.assertEqual(path.read_bytes(), (current[0] / path.relative_to(package)).read_bytes())

    def test_new_package_directory_updates_only_its_marketplace_and_cached_files(self):
        other = self.root / 'unrelated-marketplace'
        (other / '.agents/plugins').mkdir(parents=True)
        (other / '.agents/plugins/marketplace.json').write_text(json.dumps({'name': 'unrelated', 'plugins': []}))
        self.run_cli('plugin', 'marketplace', 'add', str(other), '--json')
        self.install()
        original = tomllib.loads(self.config.read_text())
        updated = self.root / 'new-package'
        shutil.copytree(self.package, updated)
        self.update_package(updated)
        self.install(updated)
        self.install(updated)
        actual = tomllib.loads(self.config.read_text())
        self.assertEqual(actual['mcp_servers'], original['mcp_servers'])
        self.assertEqual(actual['marketplaces']['unrelated'], original['marketplaces']['unrelated'])
        self.assertEqual(actual['marketplaces']['serpvibe-plugins']['source'], str(updated))
        self.assert_current_package(updated)

    def test_same_directory_same_version_rebuild_refreshes_cached_skill_files(self):
        self.install()
        self.update_package(self.package, version=None)
        self.install()
        self.assert_current_package(self.package)

    def test_invalid_upgrade_does_not_mutate_existing_install(self):
        self.install()
        original = self.config.read_bytes()
        updated = self.root / 'invalid-package'
        shutil.copytree(self.package, updated)
        (updated / '.mcp.json').write_text('{"mcpServers": {"search-stack-mcp": {"unsupported": true}}}')
        with self.assertRaises(subprocess.CalledProcessError):
            self.install(updated)
        self.assertEqual(self.config.read_bytes(), original)
        self.assert_current_package(self.package)

    def test_portable_package_is_rejected_without_implicit_conversion(self):
        portable = self.root / 'portable-package'
        shutil.copytree(ROOT / 'plugin', portable)
        original = self.config.read_bytes()
        self.env['CODEX_BIN'] = str(self.root / 'codex-must-not-be-called')
        with self.assertRaises(subprocess.CalledProcessError) as raised:
            self.install(portable)
        self.assertIn('optional Codex adapter', raised.exception.stderr)
        self.assertEqual(self.config.read_bytes(), original)
        self.assertFalse((self.profile / 'plugins/cache').exists())
        self.assertFalse((portable / '.codex-plugin').exists())

    def test_failed_upgrade_restores_previous_source_and_package(self):
        self.install()
        original = tomllib.loads(self.config.read_text())
        updated = self.root / 'new-package'
        shutil.copytree(self.package, updated)
        self.update_package(updated)
        fail_once = self.root / 'fail-one-plugin-install'
        fail_once.touch()
        wrapper = self.root / 'codex-fail-once'
        wrapper.write_text(
            f'#!{sys.executable}\n'
            'import os, sys\n'
            'from pathlib import Path\n'
            f'marker = Path({str(fail_once)!r})\n'
            "if sys.argv[1:3] == ['plugin', 'add'] and marker.exists():\n"
            '    marker.unlink()\n'
            "    print('injected install failure', file=sys.stderr)\n"
            '    sys.exit(42)\n'
            f'os.execv({shutil.which("codex")!r}, [{shutil.which("codex")!r}, *sys.argv[1:]])\n'
        )
        wrapper.chmod(0o700)
        self.env['CODEX_BIN'] = str(wrapper)
        with self.assertRaises(subprocess.CalledProcessError) as raised:
            self.install(updated)
        self.assertIn('injected install failure', raised.exception.stderr)
        self.assertNotIn('Plugin installed', raised.exception.stdout)
        self.assertFalse(fail_once.exists(), 'failure must occur after the new source is registered')
        self.assertEqual(tomllib.loads(self.config.read_text()), original)
        self.assert_current_package(self.package)

    def test_repeat_install_preserves_other_config_and_skill_contents(self):
        original = tomllib.loads(self.config.read_text())["mcp_servers"]
        self.install()
        first = self.config.read_bytes()
        self.install()
        self.assertEqual(self.config.read_bytes(), first)
        self.assertEqual(tomllib.loads(self.config.read_text())["mcp_servers"], original)
        connections = self.run_cli("mcp", "list", "--json")
        self.assertEqual(sorted(item["name"] for item in connections), ["search-stack-mcp", "unrelated"])
        connection = next(item for item in connections if item["name"] == "search-stack-mcp")
        self.assertEqual(connection["transport"]["url"], self.expected["url"])
        self.assertEqual(connection["auth_status"], "not_logged_in")
        cache = self.profile / "plugins/cache/serpvibe-plugins/serpvibe-search-stack"
        versions = list(cache.iterdir())
        self.assertEqual(len(versions), 1)
        for path in (self.package / "skills").rglob("*"):
            if path.is_file():
                self.assertEqual(path.read_bytes(), (versions[0] / path.relative_to(self.package)).read_bytes())
        self.assertFalse((versions[0] / "skills/memory-management").exists())

    def test_install_rejects_preexisting_manual_connection_without_mutation(self):
        with self.config.open("a") as config:
            config.write('\n[mcp_servers.search-stack-mcp]\nurl = "https://existing.example/mcp"\nenabled = false\n')
        original = tomllib.loads(self.config.read_text())["mcp_servers"]
        result = subprocess.run(["bash", str(ROOT / "scripts/install_codex_plugin.sh"),
                                 str(self.package), "--no-login"], cwd=self.root, env=self.env,
                                capture_output=True, text=True, timeout=60)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("shadows the plugin", result.stderr)
        self.assertNotIn("Plugin installed", result.stdout)
        self.assertEqual(tomllib.loads(self.config.read_text())["mcp_servers"], original)
        self.assertFalse((self.profile / "plugins/cache/serpvibe-plugins/serpvibe-search-stack").exists())
        connections = self.run_cli("mcp", "list", "--json")
        stack = [item for item in connections if item["name"] == "search-stack-mcp"]
        self.assertEqual(len(stack), 1)
        self.assertEqual(stack[0]["transport"]["url"], "https://existing.example/mcp")
        self.assertFalse(stack[0]["enabled"])

    def test_installed_plugin_supplies_oauth_parameters_without_cli_overrides(self):
        self.install()
        with subprocess.Popen(["bash", str(ROOT / "scripts/install_codex_plugin.sh"), str(self.package), "--no-browser"],
                              cwd=self.root, env=self.env, stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              start_new_session=True) as process:
            selector = selectors.DefaultSelector()
            selector.register(process.stdout, selectors.EVENT_READ)
            buffer = b""
            query = None
            try:
                deadline = time.monotonic() + 30
                while time.monotonic() < deadline and query is None:
                    if not selector.select(timeout=1):
                        continue
                    chunk = os.read(process.stdout.fileno(), 65536)
                    if not chunk:
                        self.fail("Codex exited before producing an authorization URL")
                    buffer += chunk
                    while b"\n" in buffer:
                        line, buffer = buffer.split(b"\n", 1)
                        line = line.decode(errors="replace").strip()
                        if line.startswith("https://"):
                            parsed = urlsplit(line)
                            parameters = parse_qs(parsed.query)
                            if "client_id" in parameters:
                                query = parameters
                                self.assertEqual(parsed.netloc, "dev-6ylzesmz8sfrtb4j.us.auth0.com")
                                break
                self.assertIsNotNone(query, "no OAuth URL within 30 seconds")
                self.assertEqual(query.get("client_id"), [native.CODEX_CIMD])
                self.assertEqual(query.get("resource"), [self.expected["url"]])
                self.assertEqual(set(query.get("scope", [""])[0].split()), set(self.expected["scopes"]))
                self.assertEqual(query.get("code_challenge_method"), ["S256"])
                self.assertEqual(query.get("response_type"), ["code"])
                self.assertTrue(query.get("state"))
                self.assertEqual(urlsplit(query["redirect_uri"][0]).hostname, "127.0.0.1")
            finally:
                selector.close()
                # Stop the wrapper and its pending Codex login together.
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()


if __name__ == "__main__":
    unittest.main()
