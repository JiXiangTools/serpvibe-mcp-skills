from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("native_plugin", ROOT / "scripts/native_plugin.py")
assert SPEC is not None and SPEC.loader is not None
native = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(native)


class NativePluginTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((ROOT / "plugin/plugin.json").read_text())
        self.mcp = json.loads((ROOT / "plugin/mcp.json").read_text())
        self.marketplace = json.loads((ROOT / ".agents/plugins/marketplace.json").read_text())

    def documents(self):
        return native.native_documents(self.manifest, self.mcp, self.marketplace)

    def test_identity_server_and_scopes_come_from_source(self):
        documents = self.documents()
        manifest = documents[".codex-plugin/plugin.json"]
        for field in ("name", "version", "description", "author", "homepage"):
            self.assertEqual(manifest[field], self.manifest[field])
        self.assertEqual(manifest["skills"], "./skills/")
        self.assertEqual(manifest["mcpServers"], "./.mcp.json")
        servers = documents[".mcp.json"]["mcpServers"]
        self.assertEqual(set(servers), set(self.mcp["mcpServers"]))
        for name, source in self.mcp["mcpServers"].items():
            self.assertEqual(servers[name]["url"], source["url"])
            self.assertEqual(servers[name]["scopes"], source["extensions"]["com.openai"]["auth"]["baseScopes"])
            self.assertNotIn("oauth_resource", servers[name])

    def test_does_not_mutate_source(self):
        before = copy.deepcopy((self.manifest, self.mcp, self.marketplace))
        self.documents()
        self.assertEqual((self.manifest, self.mcp, self.marketplace), before)

    def test_marketplace_identity_and_policy_are_preserved(self):
        catalog = self.documents()[".agents/plugins/marketplace.json"]
        self.assertEqual(catalog["name"], self.marketplace["name"])
        self.assertEqual(catalog["plugins"][0]["policy"], self.marketplace["plugins"][0]["policy"])
        self.assertEqual(catalog["plugins"][0]["source"]["path"], "./")

    def test_refuses_unrepresentable_auth_changes(self):
        original = copy.deepcopy(self.mcp)
        changes = [{"oidcEnabled": True}, {"defaultScopes": ["openid"]},
                   {"resource": "https://another.example/mcp"}, {"client": {"mode": "dcr"}},
                   {"baseScopes": ["openid"]}, {"unknown": True}]
        for change in changes:
            with self.subTest(change=change):
                self.mcp = copy.deepcopy(original)
                self.mcp["mcpServers"]["search-stack-mcp"]["extensions"]["com.openai"]["auth"].update(change)
                with self.assertRaises(ValueError):
                    self.documents()

    def test_refuses_unmapped_transport_options(self):
        self.mcp["mcpServers"]["search-stack-mcp"]["headers"] = {"example": "value"}
        with self.assertRaises(ValueError):
            self.documents()

    def test_refuses_unmapped_manifest_extensions(self):
        self.manifest["extensions"] = {"com.openai": {"hooks": "./hooks.json"}}
        with self.assertRaisesRegex(ValueError, "manifest mapping"):
            self.documents()

    def test_generation_is_deterministic(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            native.generate(ROOT, output)
            first = {str(p.relative_to(output)): p.read_bytes() for p in output.rglob("*") if p.is_file()}
            native.generate(ROOT, output)
            second = {str(p.relative_to(output)): p.read_bytes() for p in output.rglob("*") if p.is_file()}
            self.assertEqual(first, second)
            self.assertEqual(set(first), set(self.documents()))

    def test_refuses_mixed_formats_that_silently_drop_servers(self):
        for name in ("plugin.json", "mcp.json"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                output = Path(directory)
                (output / name).write_text("{}")
                with self.assertRaisesRegex(ValueError, "portable manifests"):
                    native.generate(ROOT, output)


if __name__ == "__main__":
    unittest.main()
