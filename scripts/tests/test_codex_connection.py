import copy
from pathlib import Path
import sys
import unittest


SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
from check_codex_connection import check


class ConnectionTests(unittest.TestCase):
    def setUp(self):
        self.servers = {'search-stack-mcp': {'url': 'https://fixture.example/mcp',
                        'scopes': ['website:read'], 'oauth': {'client_id': 'fixture'}}}
        self.connection = {'name': 'search-stack-mcp', 'enabled': True,
                           'auth_status': 'not_logged_in',
                           'transport': {'type': 'streamable_http', 'url': 'https://fixture.example/mcp'}}

    def test_empty_profile_before_install(self):
        self.assertEqual(check([], self.servers, {}, True), 'absent')
        with self.assertRaises(ValueError):
            check([], self.servers, {})

    def test_manual_entry_is_rejected_even_with_same_url(self):
        with self.assertRaisesRegex(ValueError, 'shadows'):
            check([self.connection], self.servers, self.servers)

    def test_unrelated_manual_entry_is_untouched(self):
        manual = {'unrelated': {'url': 'https://unrelated.example/mcp'}}
        before = copy.deepcopy(manual)
        self.assertEqual(check([self.connection], self.servers, manual), 'not_logged_in')
        self.assertEqual(manual, before)

    def test_authenticated_matching_plugin_is_reused(self):
        self.connection['auth_status'] = 'o_auth'
        self.assertEqual(check([self.connection], self.servers, {}), 'o_auth')

    def test_disabled_wrong_url_or_non_oauth_fail(self):
        for changes in ({'enabled': False}, {'auth_status': 'bearer_token'},
                        {'transport': {'type': 'streamable_http', 'url': 'https://wrong.example/mcp'}}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                check([{**self.connection, **changes}], self.servers, {})

    def test_static_auth_or_header_helpers_fail(self):
        for name in ('bearer_token_env_var', 'http_headers', 'env_http_headers', 'http_headers_helper'):
            candidate = copy.deepcopy(self.connection)
            candidate['transport'][name] = 'fixture'
            with self.subTest(field=name), self.assertRaises(ValueError):
                check([candidate], self.servers, {})
