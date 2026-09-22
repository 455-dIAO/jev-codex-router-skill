import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


router = module("router", ROOT / "jev-codex-router/scripts/route.py")
installer = module("installer", ROOT / "install.py")


def config():
    # Fixture IDs are not a real host catalog and never go to a provider.
    return {"provider": "typesafe", "routes": {
        "fast": {"model": "fixture-fast", "reasoning_effort": "low", "description": "Simple bounded work"},
        "deep": {"model": "fixture-deep", "reasoning_effort": "high", "description": "Complex reasoning"}}}


TASK = {"task_name": "read_only", "agent_type": "default", "fork_turns": "none",
        "message": "Synthetic fixture text. Explain an addition function. Do not edit files or create agents."}


def answer(choice="fast", confidence=0.9):
    return {"answers": {"route": {"type": "choice", "choice": choice, "confidence": confidence,
            "probabilities": {"fast": 1.0 if choice == "fast" else 0.0,
                              "deep": 1.0 if choice == "deep" else 0.0,
                              "defer": 1.0 if choice == "defer" else 0.0}}}}


class RoutingTests(unittest.TestCase):
    def test_selected_keeps_original_task(self):
        task = copy.deepcopy(TASK)
        result = router.interpret(answer(), config(), task)
        self.assertEqual(result["spawn_arguments"], {**TASK, "model": "fixture-fast", "reasoning_effort": "low"})
        self.assertEqual(task, TASK)

    def test_defer_and_low_confidence_have_no_spawn(self):
        for response in (answer("defer"), answer(confidence=0.2)):
            result = router.interpret(response, config(), TASK)
            self.assertEqual(result["status"], "deferred")
            self.assertNotIn("spawn_arguments", result)

    def test_malformed_provider_data_rejected(self):
        responses = [None, {}, {"answers": []}]
        for field, value in [("confidence", float("nan")), ("confidence", True), ("type", "score"),
                             ("choice", "outside"), ("choice", []), ("probabilities", {"fast": 1})]:
            data = answer()
            data["answers"]["route"][field] = value
            responses.append(data)
        data = answer()
        data["answers"]["route"]["probabilities"] = {"fast": 0, "deep": 1, "defer": 0}
        responses.append(data)
        for response in responses:
            with self.subTest(response=response), self.assertRaises(router.RouteError):
                router.interpret(response, config(), TASK)

    def test_bad_config_and_full_history_fail(self):
        for change in ({"routes": {}}, {"min_confidence": float("inf")}, {"timeout_seconds": True}, {"provider": "other"}):
            with self.subTest(change=change), self.assertRaises(router.RouteError):
                router.validate({**config(), **change}, TASK)
        for task in ({**TASK, "fork_turns": "all"}, {**TASK, "model": "forced"}, {**TASK, "agent_type": "fixed_role"}):
            with self.assertRaises(router.RouteError):
                router.validate(config(), task)

    def test_positive_fork_and_utf8_bom(self):
        router.validate(config(), {**TASK, "fork_turns": "2"})
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "任务.json"
            path.write_text(json.dumps(TASK), encoding="utf-8-sig")
            self.assertEqual(router.load_json(path), TASK)

    def test_payload_has_defer_and_minimal_context(self):
        body = router.payload_for(config(), TASK)
        self.assertEqual(set(body["state"]), {"task", "agent_type"})
        self.assertIn("defer", body["questions"]["route"]["criteria"])

    def test_audit_has_no_task_and_mock_not_live(self):
        with tempfile.TemporaryDirectory() as root:
            result = router.execute(config(), TASK, root, provider=lambda c, t: answer())
            self.assertEqual(result["status"], "selected")
            self.assertFalse(result["provider_live"])
            self.assertFalse(result["actual_model_verified"])
            receipt = Path(result["audit_path"]).read_text(encoding="utf-8")
            self.assertNotIn(TASK["message"], receipt)
            self.assertNotIn("spawn_arguments", receipt)
            self.assertIn("task_sha256", receipt)

    def test_audit_failure_prevents_dispatch(self):
        with tempfile.TemporaryDirectory() as root, patch.object(router, "save_audit", side_effect=OSError()):
            result = router.execute(config(), TASK, root, provider=lambda c, t: answer())
            self.assertEqual(result["status"], "error")
            self.assertNotIn("spawn_arguments", result)

    def test_unwritable_audit_prevents_provider(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "file"
            path.write_text("occupied")
            with patch.object(router, "call_provider") as provider:
                result = router.execute(config(), TASK, path, provider=provider)
                provider.assert_not_called()
                self.assertEqual(result["status"], "error")

    def test_missing_key_safe_error(self):
        with patch.dict(os.environ, {}, clear=True), self.assertRaisesRegex(router.RouteError, "Missing provider credential"):
            router.call_provider(config(), TASK)

    def test_redirect_not_followed(self):
        with self.assertRaises(router.RouteError):
            router.NoRedirect().redirect_request(None)

    def test_cli_check_and_missing_key(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            cfg, task = root / "config.json", root / "task.json"
            cfg.write_text(json.dumps(config()), encoding="utf-8")
            task.write_text(json.dumps(TASK), encoding="utf-8")
            cmd = [sys.executable, str(ROOT / "jev-codex-router/scripts/route.py"), "--config", str(cfg), "--input", str(task)]
            checked = subprocess.run(cmd + ["--check"], capture_output=True, text=True)
            self.assertEqual(checked.returncode, 0)
            self.assertFalse(json.loads(checked.stdout)["provider_live"])
            env = {k: v for k, v in os.environ.items() if k not in {"JEV_API_KEY", "TYPESAFE_API_KEY", "OPENROUTER_API_KEY"}}
            failed = subprocess.run(cmd + ["--audit-dir", str(root / "audit")], env=env, capture_output=True, text=True)
            self.assertEqual(failed.returncode, 2)
            self.assertNotIn("spawn_arguments", json.loads(failed.stdout))


class InstallTests(unittest.TestCase):
    def test_install_repeat_and_preserve_unrelated(self):
        with tempfile.TemporaryDirectory(prefix="skill test 中文 ") as root:
            parent = Path(root).resolve()
            unrelated = parent / "other-skill.txt"
            unrelated.write_text("keep")
            self.assertEqual(installer.install(parent)["status"], "installed")
            self.assertEqual(installer.install(parent)["status"], "already_installed")
            self.assertEqual(unrelated.read_text(), "keep")
            target = parent / installer.NAME
            self.assertEqual({p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file()}, set(installer.FILES))

    def test_modified_install_not_overwritten(self):
        with tempfile.TemporaryDirectory() as root:
            parent = Path(root).resolve()
            installer.install(parent)
            target = parent / installer.NAME / "SKILL.md"
            target.write_text("personal changes")
            with self.assertRaises(ValueError):
                installer.install(parent)
            self.assertEqual(target.read_text(), "personal changes")

    def test_source_overlap_rejected(self):
        with self.assertRaises(ValueError):
            installer.install(ROOT)

    def test_symlink_rejected_when_supported(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root).resolve()
            original, link = path / "original", path / "link"
            original.mkdir()
            try:
                link.symlink_to(original, target_is_directory=True)
            except OSError:
                self.skipTest("OS does not allow creating test symlinks")
            with self.assertRaises(ValueError):
                installer.install(link)

    def test_cli_default_code_home_install_and_repeat(self):
        with tempfile.TemporaryDirectory() as root:
            parent = Path(root).resolve()
            unrelated = parent / "unrelated.txt"
            unrelated.write_text("keep", encoding="utf-8")
            cmd = [sys.executable, str(ROOT / "install.py")]
            env = {**os.environ, "CODEX_HOME": str(parent)}

            first = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(json.loads(first.stdout)["status"], "installed")

            second = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(json.loads(second.stdout)["status"], "already_installed")

            target = parent / "skills" / installer.NAME
            self.assertEqual(
                {p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file()},
                set(installer.FILES),
            )
            self.assertEqual(unrelated.read_text(encoding="utf-8"), "keep")


if __name__ == "__main__":
    unittest.main()
