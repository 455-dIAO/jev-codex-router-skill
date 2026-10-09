"""Discover executable Codex model/effort routes through app-server."""
from __future__ import annotations

import json
import hashlib
import os
import platform
from pathlib import Path
import shutil
import subprocess
import queue
import threading
import time


class CatalogError(Exception):
    pass


_MAX_OUTPUT = 4 * 1024 * 1024
_MAX_RESPONSE = 1024 * 1024
_EFFORTS = {"none", "minimal", "low", "medium", "high", "xhigh", "max", "ultra"}


def _timeout(config):
    value = config.get("discovery_timeout_seconds", 20)
    if type(value) not in (int, float) or not 1 <= value <= 60:
        raise CatalogError("discovery_timeout_seconds must be in [1, 60]")
    return float(value)


def _command(config):
    override = config.get("codex_command")
    if override is not None:
        if not isinstance(override, list) or not override or not all(isinstance(x, str) and x for x in override):
            raise CatalogError("codex_command must be a non-empty argument list")
        command = list(override)
    else:
        executable = (shutil.which("codex.exe") if os.name == "nt" else None) or shutil.which("codex")
        if not executable:
            raise CatalogError("Codex CLI executable not found")
        command = [executable]
    if Path(command[0]).suffix.lower() in (".cmd", ".bat", ".ps1"):
        command[0] = str(_npm_executable(Path(command[0])))
    return command


def _npm_executable(wrapper):
    # Resolve the published npm package's native binary, never invoke a shell.
    arch = {"amd64": "x64", "x86_64": "x64", "arm64": "arm64", "aarch64": "arm64"}.get(platform.machine().lower())
    if arch:
        triple = ("x86_64" if arch == "x64" else "aarch64") + "-pc-windows-msvc"
        scope = wrapper.resolve().parent / "node_modules" / "@openai"
        package = scope / "codex"
        roots = [package / "node_modules" / "@openai" / ("codex-win32-" + arch),
                 scope / ("codex-win32-" + arch), package]
        for root in roots:
            for folder in ("bin", "codex"):
                executable = root / "vendor" / triple / folder / "codex.exe"
                if executable.is_file():
                    return executable
    raise CatalogError("Cannot resolve Codex wrapper; set codex_command to the native codex executable")


class _Session:
    def __init__(self, command, deadline):
        safe_env = {k: v for k, v in os.environ.items() if k not in {"JEV_API_KEY", "TYPESAFE_API_KEY", "OPENROUTER_API_KEY"}}
        self.deadline, self.next_id, self.lines = deadline, 1, queue.Queue(maxsize=128)
        self.stopped = threading.Event()
        self.process = None
        self.total = 0
        try:
            self.process = subprocess.Popen(command + ["app-server"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                            stderr=subprocess.DEVNULL, env=safe_env, shell=False)
        except (OSError, ValueError) as error:
            raise CatalogError("Unable to start Codex app-server") from error
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()

    def _offer(self, item):
        while not self.stopped.is_set():
            try:
                self.lines.put(item, timeout=0.1)
                return
            except queue.Full:
                continue

    def _read(self):
        try:
            while not self.stopped.is_set():
                raw = self.process.stdout.readline(_MAX_RESPONSE + 1)
                if not raw:
                    break
                self.total += len(raw)
                if self.total > _MAX_OUTPUT:
                    self._offer(CatalogError("Codex discovery response exceeds limit"))
                    return
                if len(raw) > _MAX_RESPONSE:
                    self._offer(CatalogError("Oversized app-server response"))
                    return
                try:
                    self._offer(json.loads(raw))
                except ValueError:
                    continue
        except (OSError, ValueError):
            self._offer(CatalogError("Unable to read Codex app-server response"))
        finally:
            self._offer(None)

    def request(self, method, params):
        if time.monotonic() >= self.deadline:
            raise CatalogError("Codex model discovery timed out")
        ident = self.next_id
        self.next_id += 1
        self.process.stdin.write((json.dumps({"jsonrpc": "2.0", "id": ident, "method": method, "params": params}) + "\n").encode())
        self.process.stdin.flush()
        while True:
            remaining = self.deadline - time.monotonic()
            if remaining <= 0:
                raise CatalogError("Codex model discovery timed out")
            try:
                item = self.lines.get(timeout=remaining)
            except queue.Empty:
                raise CatalogError("Codex model discovery timed out") from None
            if isinstance(item, Exception):
                raise item
            if item is None:
                raise CatalogError("Codex app-server exited unexpectedly")
            if isinstance(item, dict) and item.get("id") == ident:
                if "error" in item:
                    raise CatalogError("Codex app-server request failed")
                result = item.get("result")
                if not isinstance(result, dict):
                    raise CatalogError("Malformed Codex app-server response")
                return result

    def close(self):
        if not self.process:
            return
        self.stopped.set()
        try:
            self.process.stdin.close()
        except OSError:
            pass
        try:
            self.process.wait(timeout=max(0.1, min(1, self.deadline - time.monotonic())))
        except subprocess.TimeoutExpired:
            self.process.terminate()
            try:
                self.process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=1)
        try:
            self.reader.join(timeout=1)
            self.process.stdout.close()
        except OSError:
            pass


def _discover(command, deadline):
    session = _Session(command, deadline)
    try:
        session.request("initialize", {"clientInfo": {"name": "jev-codex-router", "title": "Jev Codex Router", "version": "1.1.0"}})
        session.process.stdin.write((json.dumps({"jsonrpc": "2.0", "method": "initialized", "params": {}}) + "\n").encode())
        session.process.stdin.flush()
        pages, cursor, seen = [], None, set()
        for _ in range(256):
            params = {"includeHidden": False, "limit": 100}
            if cursor is not None:
                params["cursor"] = cursor
            page = session.request("model/list", params)
            pages.append(page)
            cursor = page.get("nextCursor")
            if cursor is None:
                return pages
            if not isinstance(cursor, str) or not cursor or len(cursor) > 4096 or cursor in seen:
                raise CatalogError("Malformed model catalog pagination")
            seen.add(cursor)
        raise CatalogError("Codex model catalog has too many pages")
    finally:
        session.close()


def discover_routes(config):
    """Return stable route IDs for currently reported visible model capabilities."""
    timeout = _timeout(config)
    command = _command(config)
    results = _discover(command, time.monotonic() + timeout)
    allowed_models = config.get("allowed_models")
    allowed_efforts = config.get("allowed_efforts")
    if allowed_models is not None and (not isinstance(allowed_models, list) or not all(isinstance(x, str) for x in allowed_models)):
        raise CatalogError("allowed_models must be a list")
    if allowed_efforts is not None and (not isinstance(allowed_efforts, list) or not all(isinstance(x, str) for x in allowed_efforts)):
        raise CatalogError("allowed_efforts must be a list")
    routes = {}
    for page in results:
        models = page.get("models", page.get("data"))
        if not isinstance(models, list):
            raise CatalogError("Malformed model catalog")
        for model in models:
            if not isinstance(model, dict) or model.get("hidden") is True:
                continue
            model_id = model.get("model")
            efforts = model.get("supportedReasoningEfforts")
            if not isinstance(model_id, str) or not model_id or not isinstance(efforts, list):
                continue
            if allowed_models is not None and model_id not in allowed_models:
                continue
            for effort in efforts:
                if not isinstance(effort, dict):
                    continue
                name = effort.get("reasoningEffort")
                if not isinstance(name, str) or name not in _EFFORTS or (allowed_efforts is not None and name not in allowed_efforts):
                    continue
                description = " | ".join(str(x).strip() for x in (model.get("description") or model.get("displayName") or "", effort.get("description") or "", model_id + " / " + name) if str(x).strip())
                if not isinstance(description, str) or not description.strip():
                    continue
                route_id = "route-" + hashlib.sha256((model_id + "\0" + name).encode("utf-8")).hexdigest()[:24]
                routes[route_id] = {"model": model_id, "reasoning_effort": name, "description": description.strip()}
    if not 2 <= len(routes) <= 254:
        raise CatalogError("Codex catalog produced an unsupported route count")
    return dict(sorted(routes.items()))
