"""Portable packaging must not depend on any installed MCP host."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class PackagePluginTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='serpvibe-portable-package-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.output = self.root / 'output'
        self.bin = self.root / 'build-tools'
        self.bin.mkdir()
        # A real restricted PATH, not a mocked preflight or an installed-host skip.
        for name in ('bash', 'dirname', 'jq', 'rg', 'find', 'sort', 'mkdir', 'mktemp',
                     'cp', 'sed', 'head', 'sha256sum', 'xargs', 'awk', 'mv', 'rm', 'python3'):
            path = shutil.which(name)
            self.assertIsNotNone(path, f'missing build test dependency: {name}')
            (self.bin / name).symlink_to(path)
        self.env = {**os.environ, 'PATH': str(self.bin), 'PLUGIN_OUTPUT_ROOT': str(self.output)}
        self.assertIsNone(shutil.which('codex', path=self.env['PATH']))

    def build(self, *args, repository=ROOT, native_runtime=False):
        env = dict(self.env)
        if native_runtime:
            env['PATH'] = os.environ['PATH']
        return subprocess.run([str(self.bin / 'bash'), str(repository / 'scripts/package_plugin.sh'), *args],
                              cwd=self.root, env=env, capture_output=True, text=True, timeout=60)

    def assert_success(self, result):
        self.assertEqual(result.returncode, 0, result.stderr)
        package = Path(result.stdout.strip())
        self.assertTrue(package.is_dir())
        self.assertEqual(package.parent, self.output)
        return package

    def assert_skills_equal(self, package):
        source = ROOT / 'plugin/skills'
        expected = {str(path.relative_to(source)): path.read_bytes()
                    for path in source.rglob('*') if path.is_file()}
        actual = {str(path.relative_to(package / 'skills')): path.read_bytes()
                  for path in (package / 'skills').rglob('*') if path.is_file()}
        self.assertEqual(actual, expected)
        self.assertEqual(sorted(path.name for path in (package / 'skills').iterdir()),
                         ['account-management', 'proxy-manager', 'task-management', 'website-management'])

    def repository_fixture(self):
        repository = self.root / 'repository'
        repository.mkdir()
        for name in ('scripts', 'plugin', '.agents'):
            shutil.copytree(ROOT / name, repository / name)
        shutil.copy2(ROOT / 'README.md', repository / 'README.md')
        return repository

    def assert_not_published(self, result):
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(self.output.iterdir()) if self.output.exists() else [], [])

    def test_default_build_without_codex_preserves_portable_source_and_skills(self):
        package = self.assert_success(self.build())
        manifest = json.loads((ROOT / 'plugin/plugin.json').read_text())
        self.assertEqual(package.name, f"serpvibe-search-stack-{manifest['version']}")
        for name in ('plugin.json', 'mcp.json'):
            self.assertEqual((package / name).read_bytes(), (ROOT / 'plugin' / name).read_bytes())
        self.assertFalse((package / '.codex-plugin').exists())
        self.assertFalse((package / '.mcp.json').exists())
        self.assert_skills_equal(package)
        metadata = json.loads((package / 'build.json').read_text())
        source_mcp = json.loads((ROOT / 'plugin/mcp.json').read_text())['mcpServers']['search-stack-mcp']
        self.assertEqual(metadata['oauth']['resource'], source_mcp['url'])
        self.assertEqual(metadata['oauth']['base_scopes'], source_mcp['extensions']['com.openai']['auth']['baseScopes'])
        catalog = json.loads((ROOT / '.agents/plugins/marketplace.json').read_text())
        self.assertEqual(catalog['plugins'][0]['source']['path'], './plugin')

    def test_explicit_portable_and_default_have_identical_content_hash(self):
        default = self.assert_success(self.build('default-fixture'))
        explicit = self.assert_success(self.build('--format', 'portable', 'explicit-fixture'))
        first = json.loads((default / 'build.json').read_text())
        second = json.loads((explicit / 'build.json').read_text())
        self.assertEqual(first['content_sha256'], second['content_sha256'])
        self.assertEqual(first['oauth'], second['oauth'])

    def test_optional_codex_adapter_cannot_publish_without_codex(self):
        result = self.build('--format', 'codex', 'unavailable-host')
        self.assert_not_published(result)
        self.assertIn('cannot load the Codex adapter', result.stderr)

    def test_invalid_format_is_rejected_before_creating_output(self):
        self.assert_not_published(self.build('--format', 'unsupported'))

    def test_portable_schema_is_required(self):
        repository = self.repository_fixture()
        path = repository / 'plugin/plugin.json'
        manifest = json.loads(path.read_text())
        manifest.pop('$schema')
        path.write_text(json.dumps(manifest))
        result = self.build(repository=repository)
        self.assert_not_published(result)
        self.assertIn('invalid plugin manifest', result.stderr)

    def test_undeclared_mcp_server_is_not_published(self):
        repository = self.repository_fixture()
        path = repository / 'plugin/mcp.json'
        mcp = json.loads(path.read_text())
        mcp['mcpServers']['unexpected'] = {'type': 'streamable-http', 'url': 'https://example.invalid/mcp'}
        path.write_text(json.dumps(mcp))
        self.assert_not_published(self.build(repository=repository))

    def test_extra_unpublished_skill_is_not_packaged(self):
        repository = self.repository_fixture()
        (repository / 'plugin/skills/memory-management').mkdir()
        result = self.build(repository=repository)
        self.assert_not_published(result)
        self.assertIn('production install surface', result.stderr)

    @unittest.skipUnless(os.environ.get('SERPVIBE_CODEX_INTEGRATION') == '1', 'opt-in real Codex adapter test')
    def test_optional_codex_adapter_remains_separate_with_identical_skills(self):
        portable = self.assert_success(self.build('same-release'))
        native = self.assert_success(self.build('--format', 'codex', 'same-release', native_runtime=True))
        self.assertEqual(native.name, portable.name + '-codex')
        self.assertFalse((native / 'plugin.json').exists())
        self.assertFalse((native / 'mcp.json').exists())
        self.assertTrue((native / '.codex-plugin/plugin.json').is_file())
        self.assertTrue((native / '.mcp.json').is_file())
        self.assert_skills_equal(native)
        self.assertEqual(json.loads((native / 'build.json').read_text())['oauth'],
                         json.loads((portable / 'build.json').read_text())['oauth'])


if __name__ == '__main__':
    unittest.main()
