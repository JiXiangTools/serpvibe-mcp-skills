from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


SPEC = importlib.util.spec_from_file_location(
    "codex_plugin_preflight", Path(__file__).resolve().parents[1] / "codex_plugin_preflight.py"
)
assert SPEC is not None and SPEC.loader is not None
preflight = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preflight)


class PluginPreflightTests(unittest.TestCase):
    def response(self, servers=None, path="/tmp/candidate/plugin"):
        return {"result": {"plugin": {
            "mcpServers": ["search-stack-mcp"] if servers is None else servers,
            "summary": {"source": {"type": "local", "path": path}},
        }}}

    def validate(self, response):
        preflight.validate_plugin(
            response, ["search-stack-mcp"], Path("/tmp/candidate/plugin")
        )

    def test_accepts_candidate_with_expected_server(self):
        self.validate(self.response())

    def test_rejects_silently_dropped_server(self):
        with self.assertRaisesRegex(preflight.PreflightError, "unsupported mcp.json fields"):
            self.validate(self.response(servers=[]))

    def test_rejects_renamed_server(self):
        with self.assertRaises(preflight.PreflightError):
            self.validate(self.response(servers=["renamed-server"]))

    def test_rejects_extra_server(self):
        with self.assertRaises(preflight.PreflightError):
            self.validate(self.response(servers=["search-stack-mcp", "unexpected"]))

    def test_rejects_cached_package_instead_of_candidate(self):
        with self.assertRaisesRegex(preflight.PreflightError, "different package"):
            self.validate(self.response(path="/tmp/installed-cache/plugin"))

    def test_rejects_rpc_error(self):
        with self.assertRaisesRegex(preflight.PreflightError, "plugin/read failed"):
            self.validate({"error": {"code": -32602}})

    def test_rejects_missing_result(self):
        with self.assertRaises(preflight.PreflightError):
            self.validate({})

    def test_rejects_missing_or_extra_skill(self):
        with self.assertRaisesRegex(preflight.PreflightError, "packaged Skills"):
            preflight.validate_plugin(self.response(), ["search-stack-mcp"],
                                      Path("/tmp/candidate/plugin"), ["example:website-management"])

    def test_accepts_exact_skills(self):
        response = self.response()
        response["result"]["plugin"]["skills"] = [{"name": "example:website-management"}]
        preflight.validate_plugin(response, ["search-stack-mcp"], Path("/tmp/candidate/plugin"),
                                  ["example:website-management"])


if __name__ == "__main__":
    unittest.main()
