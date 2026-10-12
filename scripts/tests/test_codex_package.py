import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import install_codex_package as installer


class CodexPackageTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='serpvibe-package-test-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.current = self.root / 'current'
        self.candidate = self.root / 'candidate'
        self.catalog = {'name': 'serpvibe-plugins', 'plugins': [{'name': 'serpvibe-search-stack'}]}
        for directory in (self.current, self.candidate):
            (directory / '.agents/plugins').mkdir(parents=True)
            (directory / '.agents/plugins/marketplace.json').write_text(json.dumps(self.catalog))
            (directory / '.codex-plugin').mkdir()
            (directory / '.codex-plugin/plugin.json').write_text(json.dumps({'name': 'serpvibe-search-stack'}))
        self.config = {'result': {'config': {'marketplaces': {
            'serpvibe-plugins': {'source_type': 'local', 'source': str(self.current)},
        }}}}
        self.rpc = patch.object(installer, 'app_server_request', return_value=self.config).start()
        self.run = patch.object(installer.subprocess, 'run').start()
        self.addCleanup(patch.stopall)

    def commands(self):
        return [call.args[0][2:-1] for call in self.run.call_args_list]

    def test_new_directory_updates_only_its_source_and_installs_through_host(self):
        installer.install(self.candidate, 'codex')
        self.assertEqual(self.commands(), [
            ['marketplace', 'remove', 'serpvibe-plugins'],
            ['marketplace', 'add', str(self.candidate)],
            ['add', 'serpvibe-search-stack@serpvibe-plugins'],
        ])

    def test_repeat_install_does_not_remove_marketplace(self):
        installer.install(self.current, 'codex')
        self.assertEqual(self.commands(), [
            ['marketplace', 'add', str(self.current)],
            ['add', 'serpvibe-search-stack@serpvibe-plugins'],
        ])

    def test_new_install_uses_native_add_without_removal(self):
        self.config['result']['config']['marketplaces'] = None
        installer.install(self.candidate, 'codex')
        self.assertEqual(self.commands(), [
            ['marketplace', 'add', str(self.candidate)],
            ['add', 'serpvibe-search-stack@serpvibe-plugins'],
        ])

    def test_failed_add_restores_source_even_when_new_source_is_absent(self):
        failure = subprocess.CalledProcessError(1, ['codex'], stderr='fixture failure')
        self.run.side_effect = [None, failure, subprocess.CompletedProcess([], 1), None, None]
        with self.assertRaises(subprocess.CalledProcessError):
            installer.install(self.candidate, 'codex')
        self.assertEqual(self.commands()[-3:], [
            ['marketplace', 'remove', 'serpvibe-plugins'],
            ['marketplace', 'add', str(self.current)],
            ['add', 'serpvibe-search-stack@serpvibe-plugins'],
        ])
        self.assertFalse(self.run.call_args_list[2].kwargs['check'])

    def test_failed_plugin_install_restores_previous_package(self):
        self.run.side_effect = [None, None, subprocess.TimeoutExpired(['codex'], 60), None, None, None]
        with self.assertRaises(subprocess.TimeoutExpired):
            installer.install(self.candidate, 'codex')
        self.assertEqual(self.commands()[-2:], [
            ['marketplace', 'add', str(self.current)],
            ['add', 'serpvibe-search-stack@serpvibe-plugins'],
        ])

    def test_failed_restore_is_reported_instead_of_claiming_success(self):
        failure = subprocess.CalledProcessError(1, ['codex'], stderr='fixture failure')
        self.run.side_effect = [None, failure, None, failure]
        with self.assertRaisesRegex(RuntimeError, 'could not be restored'):
            installer.install(self.candidate, 'codex')

    def test_refuses_to_replace_git_source(self):
        self.config['result']['config']['marketplaces']['serpvibe-plugins']['source_type'] = 'git'
        with self.assertRaisesRegex(ValueError, 'non-local marketplace'):
            installer.install(self.candidate, 'codex')
        self.run.assert_not_called()

    def test_refuses_to_replace_shared_marketplace(self):
        self.catalog['plugins'].append({'name': 'another-plugin'})
        (self.current / '.agents/plugins/marketplace.json').write_text(json.dumps(self.catalog))
        with self.assertRaisesRegex(ValueError, 'other plugins'):
            installer.install(self.candidate, 'codex')
        self.run.assert_not_called()

    def test_missing_previous_catalog_does_not_delete_config(self):
        (self.current / '.agents/plugins/marketplace.json').unlink()
        with self.assertRaises(FileNotFoundError):
            installer.install(self.candidate, 'codex')
        self.run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
