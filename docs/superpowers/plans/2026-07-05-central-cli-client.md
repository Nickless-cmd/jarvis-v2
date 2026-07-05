# Central CLI Client — Implementation Plan (Leverance 1: usable live view)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Et brugbart, let standalone `central`-CLI der forbinder remote til Centralen, viser live-feed af alt der allerede kan streames/polles, og udfører de writes der findes nu (nerve-toggle, resolve, approvals) med øjeblikkelig effekt — så Bjørn har et vindue ind i Centralen NU.

**Architecture:** Let Python-pakke `apps/central_cli/` (httpx + Textual + Rich), pip-installerbar som `central`. REMOTE-først: genbruger `jc`'s token (`~/.config/jarvis-owner-token`) + base (`api.srvlab.dk`). Rene testbare lag (config/client/commands/renderer/feed) + en tynd Textual TUI ovenpå. Kommando-vokabular genbruger `central_terminal.py` via `POST /central/command`; direkte endpoints til realtime/writes.

**Tech Stack:** Python 3.11, httpx, Textual, Rich, pytest + respx (httpx-mock). `conda activate ai`.

**Spec:** `docs/superpowers/specs/2026-07-05-central-cli-client-design.md` (+ self-review Reviews 3-5).

---

## Filstruktur (Leverance 1)

- `apps/central_cli/pyproject.toml` — pakke + `central` entry point.
- `apps/central_cli/central_cli/__init__.py`
- `apps/central_cli/central_cli/config.py` — resolve base-url + token (env → jc-fil → config-fil), gem config 0600. Ét ansvar: konfiguration/auth-kilder.
- `apps/central_cli/central_cli/client.py` — httpx-klient: `get_json`/`post_json` (bearer) + `iter_sse`. Ét ansvar: HTTP/SSE-transport + fejl-mapping.
- `apps/central_cli/central_cli/commands.py` — verb → (endpoint | central-command) dispatch-tabel. Ét ansvar: kommando-routing.
- `apps/central_cli/central_cli/renderer.py` — Rich-formattering af svar (status-panel, incidents-tabel, feed-linje). Ét ansvar: præsentation.
- `apps/central_cli/central_cli/feed.py` — live-feed-model: normalisér SSE-event + polled snapshot → bounded feed-linjer. Ét ansvar: feed-tilstand.
- `apps/central_cli/central_cli/tui.py` — Textual 3-panel app (tynd wiring over lagene).
- `apps/central_cli/central_cli/main.py` — arg-parse, boot, `--script`-mode.
- `apps/central_cli/tests/` — test_config, test_client, test_commands, test_renderer, test_feed, test_main_script.

---

## Task 1: Pakke-skelet + `central` entry point

**Files:**
- Create: `apps/central_cli/pyproject.toml`, `apps/central_cli/central_cli/__init__.py`, `apps/central_cli/central_cli/main.py`
- Test: `apps/central_cli/tests/test_main_script.py`

- [ ] **Step 1: Write the failing test**

```python
# apps/central_cli/tests/test_main_script.py
from __future__ import annotations
from central_cli import __version__
from central_cli.main import build_arg_parser


def test_version_present():
    assert isinstance(__version__, str) and __version__


def test_arg_parser_has_core_flags():
    p = build_arg_parser()
    ns = p.parse_args(["--script", "status", "--json"])
    assert ns.script is True
    assert ns.command == "status"
    assert ns.json is True
    ns2 = p.parse_args([])
    assert ns2.command is None  # ingen kommando → TUI-mode
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda activate ai && cd apps/central_cli && python -m pytest tests/test_main_script.py -v`
Expected: FAIL (ModuleNotFoundError: central_cli)

- [ ] **Step 3: Write minimal implementation**

```toml
# apps/central_cli/pyproject.toml
[project]
name = "central-cli"
version = "0.1.0"
description = "Central CLI — live realtids-adgang til Den Intelligente Central"
requires-python = ">=3.11"
dependencies = ["httpx>=0.27", "textual>=0.60", "rich>=13.0"]

[project.scripts]
central = "central_cli.main:main"

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["."]
include = ["central_cli*"]
```

```python
# apps/central_cli/central_cli/__init__.py
__version__ = "0.1.0"
```

```python
# apps/central_cli/central_cli/main.py
from __future__ import annotations

import argparse

from central_cli import __version__


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="central", description="Central CLI")
    p.add_argument("--version", action="version", version=__version__)
    p.add_argument("--remote", metavar="URL", default=None, help="API base-url (override)")
    p.add_argument("--script", action="store_true", help="Ingen TUI — kør én kommando + exit")
    p.add_argument("--json", action="store_true", help="Rå JSON-output")
    p.add_argument("--no-boot", action="store_true", help="Skip boot-animation")
    p.add_argument("command", nargs="?", default=None, help="Kommando (kun i --script)")
    p.add_argument("args", nargs="*", help="Kommando-argumenter")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    ns = parser.parse_args(argv)
    if ns.script or ns.command:
        from central_cli.script_runner import run_script
        return run_script(ns)
    from central_cli.tui import run_tui
    return run_tui(ns)


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `conda activate ai && cd apps/central_cli && pip install -e . -q && python -m pytest tests/test_main_script.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add apps/central_cli/pyproject.toml apps/central_cli/central_cli/__init__.py apps/central_cli/central_cli/main.py apps/central_cli/tests/test_main_script.py
git commit -m "feat(central-cli): pakke-skelet + central entry point (L1)"
```

---

## Task 2: Config — remote-først, genbrug jc's token

**Files:**
- Create: `apps/central_cli/central_cli/config.py`
- Test: `apps/central_cli/tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
# apps/central_cli/tests/test_config.py
from __future__ import annotations
from central_cli import config


def test_base_url_precedence(monkeypatch, tmp_path):
    monkeypatch.delenv("CENTRAL_CLI_API_URL", raising=False)
    # default
    assert config.resolve_base_url(remote=None) == "https://api.srvlab.dk"
    # --remote override
    assert config.resolve_base_url(remote="http://10.0.0.39:8080") == "http://10.0.0.39:8080"
    # env override
    monkeypatch.setenv("CENTRAL_CLI_API_URL", "http://env:9000")
    assert config.resolve_base_url(remote=None) == "http://env:9000"


def test_token_reads_jc_file(monkeypatch, tmp_path):
    monkeypatch.delenv("CENTRAL_CLI_TOKEN", raising=False)
    jc = tmp_path / "jarvis-owner-token"
    jc.write_text("TOK-123\n")
    monkeypatch.setattr(config, "_JC_TOKEN_PATH", jc)
    assert config.resolve_token() == "TOK-123"
    # env vinder over fil
    monkeypatch.setenv("CENTRAL_CLI_TOKEN", "ENVTOK")
    assert config.resolve_token() == "ENVTOK"


def test_token_missing_returns_none(monkeypatch, tmp_path):
    monkeypatch.delenv("CENTRAL_CLI_TOKEN", raising=False)
    monkeypatch.setattr(config, "_JC_TOKEN_PATH", tmp_path / "nope")
    assert config.resolve_token() is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda activate ai && cd apps/central_cli && python -m pytest tests/test_config.py -v`
Expected: FAIL (ModuleNotFoundError: central_cli.config)

- [ ] **Step 3: Write minimal implementation**

```python
# apps/central_cli/central_cli/config.py
from __future__ import annotations

import os
from pathlib import Path

_DEFAULT_BASE = "https://api.srvlab.dk"          # jc's tunnel-base (Cloudflare → container)
_JC_TOKEN_PATH = Path.home() / ".config" / "jarvis-owner-token"   # genbrug jc's token-fil


def resolve_base_url(*, remote: str | None) -> str:
    """--remote > env CENTRAL_CLI_API_URL > default (jc-tunnel). Remote-først."""
    if remote:
        return remote.rstrip("/")
    env = os.environ.get("CENTRAL_CLI_API_URL", "").strip()
    if env:
        return env.rstrip("/")
    return _DEFAULT_BASE


def resolve_token() -> str | None:
    """env CENTRAL_CLI_TOKEN > jc's ~/.config/jarvis-owner-token. None hvis ingen."""
    env = os.environ.get("CENTRAL_CLI_TOKEN", "").strip()
    if env:
        return env
    try:
        tok = _JC_TOKEN_PATH.read_text(encoding="utf-8").strip()
        return tok or None
    except OSError:
        return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `conda activate ai && cd apps/central_cli && python -m pytest tests/test_config.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add apps/central_cli/central_cli/config.py apps/central_cli/tests/test_config.py
git commit -m "feat(central-cli): config — remote-først + genbrug jc-token (L1)"
```

---

## Task 3: HTTP-klient — get_json / post_json (bearer) + fejl-mapping

**Files:**
- Create: `apps/central_cli/central_cli/client.py`
- Test: `apps/central_cli/tests/test_client.py`

- [ ] **Step 1: Write the failing test**

```python
# apps/central_cli/tests/test_client.py
from __future__ import annotations
import httpx
import pytest
from central_cli.client import CentralClient, CentralError


def _client(handler) -> CentralClient:
    transport = httpx.MockTransport(handler)
    return CentralClient(base_url="http://x", token="T", _transport=transport)


def test_get_json_sends_bearer_and_returns_body():
    seen = {}
    def handler(req: httpx.Request) -> httpx.Response:
        seen["auth"] = req.headers.get("authorization")
        seen["url"] = str(req.url)
        return httpx.Response(200, json={"ok": True})
    c = _client(handler)
    assert c.get_json("/central/realtime") == {"ok": True}
    assert seen["auth"] == "Bearer T"
    assert seen["url"].endswith("/central/realtime")


def test_post_json_sends_body():
    seen = {}
    def handler(req: httpx.Request) -> httpx.Response:
        seen["body"] = req.content
        return httpx.Response(200, json={"done": True})
    c = _client(handler)
    assert c.post_json("/central/command", {"line": "status"}) == {"done": True}
    assert b"status" in seen["body"]


def test_403_raises_permission_error():
    c = _client(lambda req: httpx.Response(403, json={"detail": "owner-only"}))
    with pytest.raises(CentralError) as e:
        c.get_json("/central/realtime")
    assert e.value.category == "permission"


def test_500_raises_server_error():
    c = _client(lambda req: httpx.Response(500, text="boom"))
    with pytest.raises(CentralError) as e:
        c.get_json("/central/realtime")
    assert e.value.category == "server"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda activate ai && cd apps/central_cli && python -m pytest tests/test_client.py -v`
Expected: FAIL (ModuleNotFoundError: central_cli.client)

- [ ] **Step 3: Write minimal implementation**

```python
# apps/central_cli/central_cli/client.py
from __future__ import annotations

from typing import Any, Iterator

import httpx


class CentralError(Exception):
    """CLI-vendt fejl med kategori (connection/permission/auth/server/client)."""
    def __init__(self, category: str, message: str, status: int | None = None):
        super().__init__(message)
        self.category = category
        self.status = status


def _categorize(status: int) -> str:
    if status in (401,):
        return "auth"
    if status in (403,):
        return "permission"
    if status >= 500:
        return "server"
    return "client"


class CentralClient:
    def __init__(self, *, base_url: str, token: str | None, timeout: float = 20.0, _transport=None):
        self.base_url = base_url.rstrip("/")
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        self._client = httpx.Client(base_url=self.base_url, headers=headers,
                                    timeout=timeout, transport=_transport)

    def _check(self, resp: httpx.Response) -> httpx.Response:
        if resp.status_code >= 400:
            raise CentralError(_categorize(resp.status_code),
                               f"HTTP {resp.status_code}: {resp.text[:200]}", resp.status_code)
        return resp

    def get_json(self, path: str, params: dict | None = None) -> Any:
        try:
            r = self._check(self._client.get(path, params=params))
        except httpx.RequestError as exc:
            raise CentralError("connection", str(exc)) from exc
        return r.json()

    def post_json(self, path: str, body: dict) -> Any:
        try:
            r = self._check(self._client.post(path, json=body))
        except httpx.RequestError as exc:
            raise CentralError("connection", str(exc)) from exc
        return r.json()

    def iter_sse(self, path: str) -> Iterator[dict]:
        """Yield parsed `data:` JSON-linjer fra en SSE-stream. Self-safe pr. linje."""
        import json
        try:
            with self._client.stream("GET", path, timeout=None) as resp:
                self._check(resp)
                for line in resp.iter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    payload = line[len("data:"):].strip()
                    try:
                        yield json.loads(payload)
                    except ValueError:
                        continue
        except httpx.RequestError as exc:
            raise CentralError("connection", str(exc)) from exc

    def close(self) -> None:
        self._client.close()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `conda activate ai && cd apps/central_cli && python -m pytest tests/test_client.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add apps/central_cli/central_cli/client.py apps/central_cli/tests/test_client.py
git commit -m "feat(central-cli): httpx-klient get/post/sse + fejl-kategorier (L1)"
```

---

## Task 4: Kommando-dispatch — verb → endpoint/central-command (inkl. writes)

**Files:**
- Create: `apps/central_cli/central_cli/commands.py`
- Test: `apps/central_cli/tests/test_commands.py`

- [ ] **Step 1: Write the failing test**

```python
# apps/central_cli/tests/test_commands.py
from __future__ import annotations
from central_cli.commands import resolve_command, CommandSpec


def test_read_verb_maps_to_get_endpoint():
    spec = resolve_command("status", [])
    assert spec == CommandSpec(method="GET", path="/central/realtime", body=None, write=False)


def test_timeseries_and_diag():
    assert resolve_command("series", []).path == "/central/timeseries"
    assert resolve_command("diag", []).path == "/central/diagnostics"


def test_nerve_toggle_is_write_post():
    spec = resolve_command("toggle", ["network/health", "off"])
    assert spec.method == "POST"
    assert spec.path == "/central/nerve/network/health/toggle"
    assert spec.write is True
    assert spec.body == {"enabled": False}


def test_central_command_backed_verb():
    # ukendte central_terminal-verber routes via /central/command
    spec = resolve_command("incidents", ["--filter", "network"])
    assert spec.method == "POST"
    assert spec.path == "/central/command"
    assert spec.body == {"line": "incidents --filter network"}


def test_approval_write():
    spec = resolve_command("approve", ["tool", "abc123"])
    assert spec.method == "POST"
    assert spec.path == "/mc/tool-intent/approve"
    assert spec.write is True
    assert spec.body == {"id": "abc123"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda activate ai && cd apps/central_cli && python -m pytest tests/test_commands.py -v`
Expected: FAIL (ModuleNotFoundError: central_cli.commands)

- [ ] **Step 3: Write minimal implementation**

```python
# apps/central_cli/central_cli/commands.py
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CommandSpec:
    method: str
    path: str
    body: dict | None
    write: bool


# Direkte GET-endpoints (realtime/observabilitet).
_GET_ENDPOINTS = {
    "status": "/central/realtime",
    "realtime": "/central/realtime",
    "series": "/central/timeseries",
    "diag": "/central/diagnostics",
    "providers": "/central/providers",
    "mind": "/central/mind",
    "overview": "/mc/overview",
    "costs": "/mc/costs",
    "runs": "/mc/runs",
    "approvals": "/mc/approvals",
}

# Verber der routes til central_terminal-parseren via POST /central/command
# (genbrug af eksisterende vokabular — ingen duplikeret logik).
_TERMINAL_VERBS = {
    "incidents", "trace", "scan", "instrument", "daemons", "model",
    "learning", "drift", "breakers", "autonomy", "clusters", "resolve",
}


def resolve_command(verb: str, args: list[str]) -> CommandSpec:
    """Map (verb, args) → CommandSpec. Writes markeres write=True (til confirm-guard)."""
    if verb in _GET_ENDPOINTS:
        return CommandSpec("GET", _GET_ENDPOINTS[verb], None, False)

    if verb == "nerve" and args:
        return CommandSpec("GET", f"/central/nerve/{args[0]}", None, False)

    if verb == "toggle" and len(args) >= 1:
        nerve = args[0]
        enabled = not (len(args) >= 2 and args[1].lower() in ("off", "false", "0"))
        return CommandSpec("POST", f"/central/nerve/{nerve}/toggle", {"enabled": enabled}, True)

    if verb == "approve" and len(args) >= 2:
        kind, ident = args[0], args[1]
        path = {
            "tool": "/mc/tool-intent/approve",
            "autonomy": f"/mc/autonomy/proposals/{ident}/approve",
            "initiative": f"/mc/initiatives/{ident}/approve",
        }.get(kind, "/mc/tool-intent/approve")
        body = {"id": ident} if kind == "tool" else {}
        return CommandSpec("POST", path, body, True)

    if verb == "deny" and len(args) >= 2:
        kind, ident = args[0], args[1]
        path = {
            "tool": "/mc/tool-intent/deny",
            "autonomy": f"/mc/autonomy/proposals/{ident}/reject",
            "initiative": f"/mc/initiatives/{ident}/reject",
        }.get(kind, "/mc/tool-intent/deny")
        body = {"id": ident} if kind == "tool" else {}
        return CommandSpec("POST", path, body, True)

    # Alt andet → central_terminal-parser via /central/command.
    line = " ".join([verb, *args]).strip()
    is_write = verb in ("resolve",)
    return CommandSpec("POST", "/central/command", {"line": line}, is_write)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `conda activate ai && cd apps/central_cli && python -m pytest tests/test_commands.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add apps/central_cli/central_cli/commands.py apps/central_cli/tests/test_commands.py
git commit -m "feat(central-cli): kommando-dispatch (read/write/terminal-vokabular) (L1)"
```

---

## Task 5: Feed-model — normalisér SSE-event + snapshot → bounded feed-linjer

**Files:**
- Create: `apps/central_cli/central_cli/feed.py`
- Test: `apps/central_cli/tests/test_feed.py`

- [ ] **Step 1: Write the failing test**

```python
# apps/central_cli/tests/test_feed.py
from __future__ import annotations
from central_cli.feed import FeedLine, feed_line_from_event, FeedBuffer


def test_feed_line_from_trace_event():
    ev = {"cluster": "network", "nerve": "health", "decision": "degraded", "reason": "latency"}
    ln = feed_line_from_event(ev)
    assert isinstance(ln, FeedLine)
    assert ln.cluster == "network" and ln.nerve == "health"
    assert ln.decision == "degraded"
    assert "network/health" in ln.text


def test_buffer_is_bounded_and_newest_first():
    buf = FeedBuffer(cap=3)
    for i in range(5):
        buf.add(feed_line_from_event({"cluster": "c", "nerve": str(i), "decision": "observe"}))
    lines = buf.recent()
    assert len(lines) == 3
    assert lines[0].nerve == "4"   # nyeste først
    assert lines[-1].nerve == "2"


def test_severity_color_maps():
    assert feed_line_from_event({"cluster": "c", "nerve": "n", "decision": "error"}).color == "red"
    assert feed_line_from_event({"cluster": "c", "nerve": "n", "decision": "degraded"}).color == "yellow"
    assert feed_line_from_event({"cluster": "c", "nerve": "n", "decision": "observe"}).color == "green"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda activate ai && cd apps/central_cli && python -m pytest tests/test_feed.py -v`
Expected: FAIL (ModuleNotFoundError: central_cli.feed)

- [ ] **Step 3: Write minimal implementation**

```python
# apps/central_cli/central_cli/feed.py
from __future__ import annotations

from collections import deque
from dataclasses import dataclass

_COLOR = {"error": "red", "critical": "red", "degraded": "yellow",
          "warning": "yellow", "observe": "green", "info": "blue"}


@dataclass(frozen=True)
class FeedLine:
    cluster: str
    nerve: str
    decision: str
    text: str
    color: str


def feed_line_from_event(ev: dict) -> FeedLine:
    cluster = str(ev.get("cluster") or "?")
    nerve = str(ev.get("nerve") or "?")
    decision = str(ev.get("decision") or "observe")
    reason = str(ev.get("reason") or "")
    color = _COLOR.get(decision, "white")
    text = f"● {cluster}/{nerve} · {decision}" + (f" — {reason}" if reason else "")
    return FeedLine(cluster, nerve, decision, text, color)


class FeedBuffer:
    """Bounded, nyeste-først feed-buffer (live nerve-firings)."""
    def __init__(self, cap: int = 200):
        self._dq: deque[FeedLine] = deque(maxlen=cap)

    def add(self, line: FeedLine) -> None:
        self._dq.append(line)

    def recent(self) -> list[FeedLine]:
        return list(reversed(self._dq))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `conda activate ai && cd apps/central_cli && python -m pytest tests/test_feed.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add apps/central_cli/central_cli/feed.py apps/central_cli/tests/test_feed.py
git commit -m "feat(central-cli): feed-model (normalisér event → bounded feed) (L1)"
```

---

## Task 6: Renderer — Rich-formattering af status + incidents + generisk JSON

**Files:**
- Create: `apps/central_cli/central_cli/renderer.py`
- Test: `apps/central_cli/tests/test_renderer.py`

- [ ] **Step 1: Write the failing test**

```python
# apps/central_cli/tests/test_renderer.py
from __future__ import annotations
from rich.console import Console
from central_cli.renderer import render_status, render_generic


def _to_text(renderable) -> str:
    con = Console(width=100, no_color=True, record=True)
    con.print(renderable)
    return con.export_text()


def test_render_status_shows_status_and_incidents():
    data = {"status": "yellow", "open_breakers": [],
            "incidents": [{"severity": "error", "cluster": "network", "nerve": "health", "message": "latens høj"}]}
    out = _to_text(render_status(data))
    assert "yellow" in out.lower()
    assert "network" in out and "health" in out
    assert "latens" in out


def test_render_generic_json_fallback():
    out = _to_text(render_generic({"a": 1, "b": ["x", "y"]}))
    assert "a" in out and "1" in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda activate ai && cd apps/central_cli && python -m pytest tests/test_renderer.py -v`
Expected: FAIL (ModuleNotFoundError: central_cli.renderer)

- [ ] **Step 3: Write minimal implementation**

```python
# apps/central_cli/central_cli/renderer.py
from __future__ import annotations

import json
from typing import Any

from rich.panel import Panel
from rich.table import Table
from rich.console import Group

_STATUS_COLOR = {"green": "green", "yellow": "yellow", "red": "red"}


def render_status(data: dict) -> Panel:
    status = str(data.get("status") or "?")
    breakers = data.get("open_breakers") or []
    incidents = data.get("incidents") or []
    tbl = Table(show_header=True, header_style="bold cyan")
    tbl.add_column("sev"); tbl.add_column("cluster/nerve"); tbl.add_column("besked")
    for i in incidents[:50]:
        tbl.add_row(str(i.get("severity") or ""),
                    f"{i.get('cluster')}/{i.get('nerve')}",
                    str(i.get("message") or "")[:80])
    head = f"[bold]STATUS:[/bold] {status}  |  breakers: {len(breakers)}  |  incidents: {len(incidents)}"
    return Panel(Group(head, tbl), title="◈ CENTRAL", border_style=_STATUS_COLOR.get(status, "cyan"))


def render_generic(data: Any) -> Panel:
    return Panel(json.dumps(data, indent=2, ensure_ascii=False, default=str), title="output", border_style="cyan")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `conda activate ai && cd apps/central_cli && python -m pytest tests/test_renderer.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add apps/central_cli/central_cli/renderer.py apps/central_cli/tests/test_renderer.py
git commit -m "feat(central-cli): Rich-renderer (status-panel + generisk JSON) (L1)"
```

---

## Task 7: Script-runner — `central --script <cmd>` (one-shot, absorberer jc)

**Files:**
- Create: `apps/central_cli/central_cli/script_runner.py`
- Test: `apps/central_cli/tests/test_script_runner.py`

- [ ] **Step 1: Write the failing test**

```python
# apps/central_cli/tests/test_script_runner.py
from __future__ import annotations
import argparse
from central_cli.script_runner import execute


class _FakeClient:
    def __init__(self): self.calls = []
    def get_json(self, path, params=None): self.calls.append(("GET", path)); return {"status": "yellow", "incidents": []}
    def post_json(self, path, body): self.calls.append(("POST", path, body)); return {"ok": True}


def test_execute_status_json_returns_raw():
    c = _FakeClient()
    out, code = execute(c, verb="status", args=[], as_json=True)
    assert code == 0
    assert '"status"' in out and "yellow" in out
    assert c.calls == [("GET", "/central/realtime")]


def test_execute_write_hits_post():
    c = _FakeClient()
    out, code = execute(c, verb="toggle", args=["network/health", "off"], as_json=True)
    assert code == 0
    assert c.calls[0][0] == "POST"
    assert c.calls[0][1] == "/central/nerve/network/health/toggle"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda activate ai && cd apps/central_cli && python -m pytest tests/test_script_runner.py -v`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Write minimal implementation**

```python
# apps/central_cli/central_cli/script_runner.py
from __future__ import annotations

import argparse
import json

from central_cli.client import CentralClient, CentralError
from central_cli.commands import resolve_command
from central_cli.config import resolve_base_url, resolve_token


def execute(client, *, verb: str, args: list[str], as_json: bool) -> tuple[str, int]:
    """Kør én kommando mod klienten. Returnerer (output_tekst, exit_code)."""
    spec = resolve_command(verb, args)
    try:
        if spec.method == "GET":
            data = client.get_json(spec.path)
        else:
            data = client.post_json(spec.path, spec.body or {})
    except CentralError as exc:
        return (f"fejl ({exc.category}): {exc}", 1)
    if as_json:
        return (json.dumps(data, indent=2, ensure_ascii=False, default=str), 0)
    # ikke-json: render kort (status → panel, ellers generic) — via renderer i TUI/print.
    from rich.console import Console
    from central_cli.renderer import render_status, render_generic
    con = Console(record=True)
    con.print(render_status(data) if verb in ("status", "realtime") and isinstance(data, dict) else render_generic(data))
    return (con.export_text(), 0)


def run_script(ns: argparse.Namespace) -> int:
    if not ns.command:
        print("central --script kræver en kommando", flush=True)
        return 2
    base = resolve_base_url(remote=ns.remote)
    token = resolve_token()
    client = CentralClient(base_url=base, token=token)
    try:
        out, code = execute(client, verb=ns.command, args=list(ns.args), as_json=ns.json)
    finally:
        client.close()
    print(out, flush=True)
    return code
```

- [ ] **Step 4: Run test to verify it passes**

Run: `conda activate ai && cd apps/central_cli && python -m pytest tests/test_script_runner.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add apps/central_cli/central_cli/script_runner.py apps/central_cli/tests/test_script_runner.py
git commit -m "feat(central-cli): script-runner (one-shot, absorberer jc) (L1)"
```

---

## Task 8: TUI — Textual 3-panel (live feed | output | command bar) + smoke test

**Files:**
- Create: `apps/central_cli/central_cli/tui.py`
- Test: `apps/central_cli/tests/test_tui_smoke.py`

- [ ] **Step 1: Write the failing test**

```python
# apps/central_cli/tests/test_tui_smoke.py
from __future__ import annotations
import pytest
from central_cli.tui import CentralApp


@pytest.mark.asyncio
async def test_app_boots_and_has_three_panes():
    app = CentralApp(base_url="http://x", token="T", live=False)  # live=False → ingen netværk
    async with app.run_test() as pilot:
        assert app.query_one("#feed") is not None
        assert app.query_one("#output") is not None
        assert app.query_one("#cmdbar") is not None
        # skriv en kommando i baren → dispatch kaldes (mocket)
        app._last_dispatched = None
        await pilot.press(*"status")
        await app._run_command("status")
        assert app._last_dispatched == "status"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda activate ai && cd apps/central_cli && pip install -e ".[test]" -q; pip install pytest-asyncio -q; python -m pytest tests/test_tui_smoke.py -v`
Expected: FAIL (ModuleNotFoundError: central_cli.tui)

- [ ] **Step 3: Write minimal implementation**

```python
# apps/central_cli/central_cli/tui.py
from __future__ import annotations

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Input, RichLog, Static

from central_cli.client import CentralClient, CentralError
from central_cli.commands import resolve_command
from central_cli.feed import FeedBuffer, feed_line_from_event
from central_cli.renderer import render_status, render_generic


class CentralApp(App):
    CSS = """
    #feed { width: 30%; border: solid cyan; }
    #output { width: 70%; border: solid cyan; }
    #cmdbar { dock: bottom; }
    """

    def __init__(self, *, base_url: str, token: str | None, live: bool = True):
        super().__init__()
        self._client = CentralClient(base_url=base_url, token=token)
        self._buf = FeedBuffer()
        self._live = live
        self._last_dispatched: str | None = None

    def compose(self) -> ComposeResult:
        with Vertical():
            with Horizontal():
                yield RichLog(id="feed", highlight=False, markup=True)
                yield RichLog(id="output", markup=True)
            yield Input(placeholder="central> ", id="cmdbar")

    def on_mount(self) -> None:
        if self._live:
            self.set_interval(3.0, self._poll_feed)

    async def _poll_feed(self) -> None:
        try:
            snap = self._client.get_json("/central/realtime")
        except CentralError:
            return
        for i in (snap.get("incidents") or [])[:20]:
            self._buf.add(feed_line_from_event({
                "cluster": i.get("cluster"), "nerve": i.get("nerve"),
                "decision": i.get("severity"), "reason": str(i.get("message") or "")[:60]}))
        log = self.query_one("#feed", RichLog)
        log.clear()
        for ln in self._buf.recent()[:60]:
            log.write(f"[{ln.color}]{ln.text}[/{ln.color}]")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        await self._run_command(event.value.strip())
        self.query_one("#cmdbar", Input).value = ""

    async def _run_command(self, line: str) -> None:
        if not line:
            return
        self._last_dispatched = line
        parts = line.split()
        spec = resolve_command(parts[0], parts[1:])
        out = self.query_one("#output", RichLog)
        try:
            data = (self._client.get_json(spec.path) if spec.method == "GET"
                    else self._client.post_json(spec.path, spec.body or {}))
        except CentralError as exc:
            out.write(f"[red]fejl ({exc.category}): {exc}[/red]")
            return
        out.clear()
        out.write(render_status(data) if parts[0] in ("status", "realtime") and isinstance(data, dict)
                  else render_generic(data))


def run_tui(ns) -> int:
    from central_cli.config import resolve_base_url, resolve_token
    app = CentralApp(base_url=resolve_base_url(remote=ns.remote), token=resolve_token())
    app.run()
    return 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `conda activate ai && cd apps/central_cli && python -m pytest tests/test_tui_smoke.py -v`
Expected: PASS (1 test)

- [ ] **Step 5: Commit**

```bash
git add apps/central_cli/central_cli/tui.py apps/central_cli/tests/test_tui_smoke.py
git commit -m "feat(central-cli): Textual 3-panel TUI + live-poll + command bar (L1)"
```

---

## Task 9: Live end-to-end verifikation (mod containeren)

**Files:** ingen kode — operationel verifikation.

- [ ] **Step 1:** `conda activate ai && cd apps/central_cli && pip install -e . -q`
- [ ] **Step 2:** `central --script status --json` → forventet: JSON med `status` + `incidents` (samme som `jc status`). Bekræfter remote-token + klient virker.
- [ ] **Step 3:** `central --script series` → tidsserie-JSON. `central --script diag` → diagnostik.
- [ ] **Step 4:** Write-røgtest (ufarlig): `central --script toggle <en-ikke-security-nerve> off` → verificér i `jc nerve <n>` at den slog fra; slå til igen. Bekræfter øjeblikkelig-effekt-write.
- [ ] **Step 5:** `central` (TUI) → 3 paneler, feed poller, skriv `status` i baren → panel opdateres. Ctrl+C afslutter rent.
- [ ] **Step 6:** Commit en kort `apps/central_cli/README.md` med install + brug (pip install -e, `central`, `central --script status --json`, `--remote`).

```bash
git add apps/central_cli/README.md
git commit -m "docs(central-cli): README install + brug; L1 live-verificeret"
```

---

## Leverance 2 (BACKEND Fase 0 — fuld skrive-magt) — task-outline (egen plan efter L1)

Nye endpoints (owner-gated + confirm-guard + security-invariant bevaret), derefter CLI-verb-grupper:
- **Healer-flade:** `GET /central/healers` (→ `build_healer_surface`, error_healers.py:523) · `POST /central/healers/flag` (`set_healer_flag` global + `daemon_restart_live`/`syslog_restart_live`, error_healers.py:93,106-107) · heal-outcome/escalation-feed (nerve `heal/*`). CLI: `heal show|enable|disable|live <h>|ledger`.
- **Governance read/write:** `GET/POST /central/governance` over injection_live (central_injection_registry.py:140), lag4 live+pause (central_adaptation.py:46,275), gut_consumer_mode (gut_engine.py:89), agenda_authoritative (central_agenda.py:22), self_prompt (central_self_state.py:23), generative_autonomy (settings.py:85). CLI: `gov show|set <flag> <value>` + confirm.
- **Breaker-reset:** `POST /central/breakers/{name}/reset` (central_switches.py:90). CLI: `breaker reset <name>`.
- **Canonical error-taksonomi:** `GET /central/error-kinds` (KIND_MAP, central_error_envelope.py:213). CLI: `errors kinds`.
- **Token:** `token mint|rotate|revoke` (issue_token jarvisx.py:1462 + secret-rotation). **Write-audit-log:** ny durable tabel/kv der logger hver central-mutation (hvem/hvad/hvornår) — findes ikke i dag.
Hver med eksekverbar test + confirm-guard-test. Udvides til fuld TDD-plan når L1 lander.

## Leverance 3 (fuld realtime + polish) — task-outline (egen plan)

- Event-familie-filtre på `/central/stream` (server-side) + cross-proces-feed i live + heal/cost/run-live streams.
- TUI-polish: J.A.R.V.I.S-tema (§5), boot-animation, keyboard shortcuts (§4), command-history, `watch`, paginering, `--no-color`/`--theme`.
- jarvis-desk-nedgradering SIDST (efter CLI verificeret): slet CentralPanel.tsx/CentralHud.tsx/centralStream.ts, tilføj let CentralBadge.tsx.

---

## Self-Review (Leverance 1)

**Spec-dækning (L1-delen):** §3 auth (remote+jc-token) → Task 2. §4 TUI 3-panel → Task 8. §6 kommandoer (read+writes) → Task 4+7+8. Realtime (poll live) → Task 8 `_poll_feed`. Install/`central` entry → Task 1. jc-absorption (`--script`) → Task 7. Live-verifikation → Task 9. Ikke i L1 (bevidst, → L2/L3): healing/governance-writes (kræver backend), SSE-stream-familie-filtre, J.A.R.V.I.S-polish, desk-nedgradering.

**Placeholder-scan:** ingen TBD/TODO i L1-tasks; alle kode-steps komplette + eksakte kommandoer.

**Type-konsistens:** `CommandSpec(method,path,body,write)` ens i Task 4/7/8. `CentralClient.get_json/post_json/iter_sse` ens i Task 3/7/8. `FeedLine`/`FeedBuffer.recent()` ens i Task 5/8. `resolve_base_url(remote=)`/`resolve_token()` ens i Task 2/7/8. `execute(client, *, verb, args, as_json)` ens i Task 7. `render_status`/`render_generic` ens i Task 6/7/8.
