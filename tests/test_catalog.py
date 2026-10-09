import json
import os
from pathlib import Path
import sys
import tempfile
import textwrap
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "jev-codex-router/scripts"))
import catalog


SERVER = textwrap.dedent(r'''
    import json, sys, time
    initialized = False
    for line in sys.stdin:
        call = json.loads(line)
        if call.get("method") == "initialize":
            if "init-error" in sys.argv:
                print(json.dumps({"id":call["id"],"error":{"message":"private server text"}}), flush=True)
                continue
            print(json.dumps({"jsonrpc":"2.0","id":call["id"],"result":{}}), flush=True)
        elif call.get("method") == "initialized":
            initialized = True
        elif call.get("method") == "model/list":
            assert initialized and call["params"]["includeHidden"] is False
            if "sleep" in sys.argv: time.sleep(5)
            if "exit" in sys.argv: raise SystemExit(3)
            if "oversized" in sys.argv:
                sys.stdout.write("x" * 1048578)
                sys.stdout.flush()
                time.sleep(5)
            if "flood" in sys.argv:
                for _ in range(500):
                    print(json.dumps({"method":"notification","params":{}}), flush=True)
            cursor = call.get("params", {}).get("cursor")
            page = [{"model": "base", "supportedReasoningEfforts": [{"reasoningEffort":"low","description":"fast"},{"reasoningEffort":"unknown","description":"skip"}]}, {"model":"hidden","hidden":True,"supportedReasoningEfforts":[{"reasoningEffort":"high","description":"skip"}]}]
            if cursor: page = [{"model":"future-model","displayName":"Future","supportedReasoningEfforts":[{"reasoningEffort":"high","description":"deep"}]}]
            if cursor and "new" in sys.argv:
                page.append({"model":"next-release","description":"New capability","supportedReasoningEfforts":[{"reasoningEffort":"medium","description":"Balanced"}]})
            result = {"data": page} if cursor else {"data": page, "nextCursor":"next"}
            if "cycle" in sys.argv: result["nextCursor"] = "next"
            if "malformed" in sys.argv: result = {"data": {}}
            print(json.dumps({"jsonrpc":"2.0","id":call["id"],"result":result}), flush=True)
''')


class CatalogTests(unittest.TestCase):
    def run_server(self, *args, **config):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            script = Path(directory) / "server.py"
            script.write_text(SERVER, encoding="utf-8")
            return catalog.discover_routes({"codex_command": [sys.executable, str(script), *args], **config})

    def test_discovery_pagination_hidden_filters_and_future_model(self):
        first = self.run_server()
        self.assertEqual({(x["model"], x["reasoning_effort"]) for x in first.values()},
                         {("base", "low"), ("future-model", "high")})
        second = self.run_server(allowed_models=["base", "future-model"], allowed_efforts=["low", "high"])
        self.assertEqual({(x["model"], x["reasoning_effort"]) for x in second.values()},
                         {("base", "low"), ("future-model", "high")})

    def test_malformed_catalog_and_process_exit_fail(self):
        with self.assertRaises(catalog.CatalogError):
            self.run_server("exit")

    def test_timeout_is_bounded(self):
        with self.assertRaises(catalog.CatalogError):
            self.run_server("sleep", discovery_timeout_seconds=1)

    def test_refresh_adds_new_model_and_retains_stable_ids(self):
        first, second = self.run_server(), self.run_server("new")
        self.assertEqual(len(first), 2)
        self.assertEqual(len(second), 3)
        self.assertTrue(set(first) < set(second))
        self.assertIn("next-release", {r["model"] for r in second.values()})

    def test_invalid_rpc_catalog_and_cycles_fail_without_raw_error(self):
        for mode in ("init-error", "malformed", "cycle", "oversized"):
            with self.subTest(mode=mode), self.assertRaises(catalog.CatalogError) as error:
                self.run_server(mode, discovery_timeout_seconds=2)
            self.assertNotIn("private server text", str(error.exception))

    def test_filter_removes_candidates_and_flood_is_drained(self):
        routes = self.run_server("new", "flood", allowed_models=["base", "next-release"])
        self.assertEqual({r["model"] for r in routes.values()}, {"base", "next-release"})
        with self.assertRaises(catalog.CatalogError):
            self.run_server(allowed_efforts=["low"])

    def test_windows_npm_wrapper_resolves_native_without_shell(self):
        with tempfile.TemporaryDirectory() as root, patch.object(catalog.platform, "machine", return_value="AMD64"):
            wrapper = Path(root) / "codex.cmd"
            wrapper.write_text("must never execute shell")
            binary = Path(root) / "node_modules/@openai/codex/node_modules/@openai/codex-win32-x64/vendor/x86_64-pc-windows-msvc/bin/codex.exe"
            binary.parent.mkdir(parents=True)
            binary.write_bytes(b"fixture")
            self.assertEqual(catalog._command({"codex_command": [str(wrapper)]}), [str(binary)])
            binary.unlink()
            with self.assertRaises(catalog.CatalogError):
                catalog._command({"codex_command": [str(wrapper)]})


if __name__ == "__main__":
    unittest.main()
