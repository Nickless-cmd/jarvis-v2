# Central Cockpit Redesign — Fase 1 (Motoren & Rammen) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Byg en async, aldrig-frysende, markør-stabil, fokus-drevet ramme for Central-CLI'en bag flaget `CENTRAL_COCKPIT_V2`, bevist på tre views (Overview, Incidents, Nerves) med fuld-skærms drill-down.

**Architecture:** Baggrunds-workers henter hver surface til en central `HudState` last-good-cache; UI-tråden rører aldrig netværk. Views tegner kun fra cachen; tabeller bevarer markør ved at fange den valgte row-KEY, genopbygge, og flytte markøren tilbage til samme key. Drill-down er en Textual `Screen`-stak. Gammel HUD bevares bag flag.

**Tech Stack:** Python 3.11, Textual ≥0.60, httpx (via eksisterende `CentralClient`), pytest. Tests køres i conda-env `ai`: `/opt/conda/envs/ai/bin/python -m pytest ... -o addopts=""` (repoets addopts kræver pytest-timeout; override med `-o addopts=""`).

**Spec:** `docs/superpowers/specs/2026-07-11-central-cockpit-redesign-design.md`

---

## File Structure

```
apps/central_cli/central_cli/
  engine/
    __init__.py
    state.py         # HudState + SurfaceEntry (last-good cache)
    rowdiff.py       # PURE cursor-restore helper (ingen Textual-afhængighed)
    workers.py       # async fetch-workers + kadence-tabel
  frame/
    __init__.py
    table_view.py    # CursorStableTable (DataTable-subklasse)
    detail_screen.py # DetailScreen base (breadcrumb + VerticalScroll + esc)
    palette.py       # CommandPalette (':' modal)
    app.py           # CockpitApp (skal, tabs, refresh-tick, drill-stak)
  views/
    __init__.py
    overview.py      # render(entry) -> Renderable
    incidents.py     # build_rows + IncidentDetailScreen
    nerves.py        # build_rows + NerveDetailScreen
tests/central_cli/
  test_hudstate.py
  test_rowdiff.py
  test_workers.py
  test_cockpit_pilot.py   # app.run_test() integration + screenshot
```

Genbruger uændret: `central_cli/client.py` (`CentralClient`), `central_cli/config.py` (`resolve_base_url`, `resolve_token`), `central_cli/hud_theme.py` (farver: `BG, PANEL, CYAN, AMBER, RED, GREEN, FG, FGDIM, DIM, LINE`), `central_cli/commands.py` (`resolve_command`). De gamle `hud*.py` og `datasource.py` røres ikke.

---

### Task 1: HudState — last-good cache

**Files:**
- Create: `apps/central_cli/central_cli/engine/__init__.py` (tom)
- Create: `apps/central_cli/central_cli/engine/state.py`
- Test: `tests/central_cli/test_hudstate.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/central_cli/test_hudstate.py
from central_cli.engine.state import HudState


def test_set_ok_stores_data_and_clears_error():
    s = HudState()
    s.set_error("realtime", "boom")
    s.set_ok("realtime", {"status": "green"})
    e = s.get("realtime")
    assert e.data == {"status": "green"}
    assert e.error is None
    assert e.fetched_at > 0
    assert e.loading is False


def test_set_error_preserves_last_good_data():
    s = HudState()
    s.set_ok("realtime", {"status": "green"})
    s.set_error("realtime", "HTTP 500")
    e = s.get("realtime")
    assert e.data == {"status": "green"}   # BEVARET — vises stadig i UI
    assert e.error == "HTTP 500"


def test_get_unknown_surface_returns_empty_entry():
    s = HudState()
    e = s.get("nope")
    assert e.data is None and e.error is None and e.fetched_at == 0.0


def test_is_stale_uses_monotonic_age(monkeypatch):
    import central_cli.engine.state as st
    now = [1000.0]
    monkeypatch.setattr(st, "_now", lambda: now[0])
    s = HudState()
    s.set_ok("x", 1)
    now[0] = 1002.0
    assert s.is_stale("x", max_age_s=1.0) is True
    assert s.is_stale("x", max_age_s=5.0) is False
    assert s.is_stale("never_fetched", max_age_s=5.0) is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/central_cli/test_hudstate.py -o addopts="" -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'central_cli.engine'`

- [ ] **Step 3: Write minimal implementation**

```python
# apps/central_cli/central_cli/engine/state.py
from __future__ import annotations

import time
from dataclasses import dataclass, field


def _now() -> float:
    return time.monotonic()


@dataclass
class SurfaceEntry:
    data: object | None = None
    fetched_at: float = 0.0
    error: str | None = None
    loading: bool = False


class HudState:
    """In-memory last-good cache pr. surface. set_error overskriver ALDRIG data,
    så UI altid kan vise sidste gode værdi + en stale/fejl-markør."""

    def __init__(self) -> None:
        self._surfaces: dict[str, SurfaceEntry] = {}

    def get(self, surface: str) -> SurfaceEntry:
        return self._surfaces.get(surface) or SurfaceEntry()

    def _entry(self, surface: str) -> SurfaceEntry:
        e = self._surfaces.get(surface)
        if e is None:
            e = SurfaceEntry()
            self._surfaces[surface] = e
        return e

    def set_loading(self, surface: str, loading: bool = True) -> None:
        self._entry(surface).loading = loading

    def set_ok(self, surface: str, data: object) -> None:
        e = self._entry(surface)
        e.data = data
        e.error = None
        e.loading = False
        e.fetched_at = _now()

    def set_error(self, surface: str, error: str) -> None:
        e = self._entry(surface)
        e.error = error
        e.loading = False

    def is_stale(self, surface: str, max_age_s: float) -> bool:
        e = self._surfaces.get(surface)
        if e is None or e.fetched_at == 0.0:
            return True
        return (_now() - e.fetched_at) > max_age_s
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/central_cli/test_hudstate.py -o addopts="" -q`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add apps/central_cli/central_cli/engine/__init__.py apps/central_cli/central_cli/engine/state.py tests/central_cli/test_hudstate.py
git commit -m "feat(cockpit): HudState last-good cache (engine)"
```

---

### Task 2: rowdiff — pure cursor-restore helper

**Files:**
- Create: `apps/central_cli/central_cli/engine/rowdiff.py`
- Test: `tests/central_cli/test_rowdiff.py`

**Rationale:** Kerne-regressionen (markør-hop) løses ved: fang den valgte row-KEY → genopbyg rækker → flyt markør tilbage til samme key. Den rene index-beregning testes uden Textual.

- [ ] **Step 1: Write the failing test**

```python
# tests/central_cli/test_rowdiff.py
from central_cli.engine.rowdiff import restore_cursor_index


def test_cursor_follows_selected_key_after_reorder():
    # valgt "b"; ny rækkefølge sætter b sidst → markør skal følge b til index 2
    assert restore_cursor_index("b", ["a", "c", "b"], old_index=1) == 2


def test_cursor_clamps_when_selected_key_removed():
    # valgt "b" forsvinder; gammel index 1 bevares, clampet til nyt antal
    assert restore_cursor_index("b", ["a", "c"], old_index=1) == 1
    assert restore_cursor_index("b", ["a"], old_index=1) == 0


def test_cursor_zero_when_empty():
    assert restore_cursor_index("b", [], old_index=3) == 0


def test_cursor_stable_when_nothing_changes():
    assert restore_cursor_index("a", ["a", "b", "c"], old_index=0) == 0


def test_none_selected_key_clamps_old_index():
    assert restore_cursor_index(None, ["a", "b"], old_index=5) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/central_cli/test_rowdiff.py -o addopts="" -q`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# apps/central_cli/central_cli/engine/rowdiff.py
from __future__ import annotations


def restore_cursor_index(
    selected_key: str | None, new_keys: list[str], old_index: int
) -> int:
    """Hvor markøren skal stå efter en tabel-genopbygning.
    Markøren FØLGER den valgte key hvis den stadig findes; ellers bevares det
    gamle index, clampet til det nye række-antal. Tom tabel → 0."""
    if not new_keys:
        return 0
    if selected_key is not None and selected_key in new_keys:
        return new_keys.index(selected_key)
    return min(max(old_index, 0), len(new_keys) - 1)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/central_cli/test_rowdiff.py -o addopts="" -q`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add apps/central_cli/central_cli/engine/rowdiff.py tests/central_cli/test_rowdiff.py
git commit -m "feat(cockpit): pure cursor-restore helper (rowdiff)"
```

---

### Task 3: workers — async fetch til HudState

**Files:**
- Create: `apps/central_cli/central_cli/engine/workers.py`
- Test: `tests/central_cli/test_workers.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/central_cli/test_workers.py
import asyncio
from central_cli.engine.state import HudState
from central_cli.engine.workers import fetch_surface, SURFACE_PATHS


class _FakeClient:
    def __init__(self, mapping, fail=None):
        self._mapping = mapping
        self._fail = fail or set()
    def get_json(self, path, params=None):
        if path in self._fail:
            from central_cli.client import CentralError
            raise CentralError("server", "boom")
        return self._mapping[path]


def test_fetch_surface_writes_ok():
    state = HudState()
    client = _FakeClient({"/central/realtime": {"status": "green"}})
    asyncio.run(fetch_surface(client, state, "realtime"))
    e = state.get("realtime")
    assert e.data == {"status": "green"} and e.error is None


def test_fetch_surface_records_error_but_keeps_data():
    state = HudState()
    state.set_ok("realtime", {"status": "green"})
    client = _FakeClient({}, fail={"/central/realtime"})
    asyncio.run(fetch_surface(client, state, "realtime"))
    e = state.get("realtime")
    assert e.error is not None
    assert e.data == {"status": "green"}   # last-good bevaret


def test_surface_paths_cover_phase1_surfaces():
    for s in ("realtime", "costs_daily", "diagnostics"):
        assert s in SURFACE_PATHS
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/central_cli/test_workers.py -o addopts="" -q`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# apps/central_cli/central_cli/engine/workers.py
from __future__ import annotations

import asyncio

from central_cli.client import CentralClient, CentralError
from central_cli.engine.state import HudState

# Surface-navn → (path, params). Kun Fase 1-surfaces her; udvides pr. fase.
SURFACE_PATHS: dict[str, tuple[str, dict | None]] = {
    "realtime": ("/central/realtime", None),
    "costs_daily": ("/central/costs-daily", None),
    "diagnostics": ("/central/diagnostics", None),
}

# Surface-navn → kadence i sekunder (hvor ofte worker gen-henter).
SURFACE_CADENCE: dict[str, float] = {
    "realtime": 2.0,
    "costs_daily": 30.0,
    "diagnostics": 5.0,
}


async def fetch_surface(client: CentralClient, state: HudState, surface: str) -> None:
    """Hent én surface og skriv til state. Blokerende httpx-kald køres i en tråd
    så UI-loopet aldrig blokeres. Fejl bevarer sidste gode data."""
    path, params = SURFACE_PATHS[surface]
    state.set_loading(surface, True)
    try:
        data = await asyncio.to_thread(client.get_json, path, params)
        state.set_ok(surface, data)
    except CentralError as exc:
        state.set_error(surface, f"{exc.category}: {exc}")
    except Exception as exc:  # defensiv — en worker må aldrig vælte appen
        state.set_error(surface, str(exc))


async def fetch_detail(
    client: CentralClient, state: HudState, surface_key: str, path: str
) -> None:
    """On-demand detalje-fetch (fx 'nerve_detail:<navn>')."""
    state.set_loading(surface_key, True)
    try:
        data = await asyncio.to_thread(client.get_json, path, None)
        state.set_ok(surface_key, data)
    except CentralError as exc:
        state.set_error(surface_key, f"{exc.category}: {exc}")
    except Exception as exc:
        state.set_error(surface_key, str(exc))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/central_cli/test_workers.py -o addopts="" -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add apps/central_cli/central_cli/engine/workers.py tests/central_cli/test_workers.py
git commit -m "feat(cockpit): async fetch-workers (never-freeze, last-good on error)"
```

---

### Task 4: CursorStableTable

**Files:**
- Create: `apps/central_cli/central_cli/frame/__init__.py` (tom)
- Create: `apps/central_cli/central_cli/frame/table_view.py`
- Test: (dækkes af pilot-test i Task 9; her kun statisk import-smoke)

- [ ] **Step 1: Write the failing test**

```python
# tests/central_cli/test_table_view_import.py
def test_cursor_stable_table_importable():
    from central_cli.frame.table_view import CursorStableTable
    assert hasattr(CursorStableTable, "update_rows")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/central_cli/test_table_view_import.py -o addopts="" -q`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# apps/central_cli/central_cli/frame/table_view.py
from __future__ import annotations

from textual.widgets import DataTable

from central_cli.engine.rowdiff import restore_cursor_index


class CursorStableTable(DataTable):
    """DataTable hvor markør + valgt element BEVARES på tværs af data-opdateringer.
    Vi fanger den valgte row-KEY, genopbygger rækkerne, og flytter markøren tilbage
    til samme key (rowdiff.restore_cursor_index). Løser markør-hop ved refresh."""

    def __init__(self, *columns: tuple[str, int], **kwargs) -> None:
        super().__init__(zebra_stripes=True, cursor_type="row", **kwargs)
        self._columns_spec = columns
        self._columns_added = False

    def _ensure_columns(self) -> None:
        if not self._columns_added:
            for label, width in self._columns_spec:
                self.add_column(label, width=width, key=label)
            self._columns_added = True

    def _selected_key(self) -> str | None:
        try:
            if self.row_count == 0:
                return None
            row_key = self.coordinate_to_cell_key(self.cursor_coordinate).row_key
            return str(row_key.value) if row_key is not None else None
        except Exception:
            return None

    def update_rows(self, rows: list[dict], *, key_field: str) -> None:
        """rows: liste af dicts. Hver skal have key_field + én værdi pr. kolonne-label
        (nøgle = kolonne-label). Bevarer markør på valgt key."""
        self._ensure_columns()
        selected = self._selected_key()
        old_index = self.cursor_coordinate.row if self.row_count else 0
        new_keys = [str(r[key_field]) for r in rows]

        self.clear()  # ryd kun RÆKKER (ikke kolonner)
        for r in rows:
            cells = [r.get(label, "") for (label, _w) in self._columns_spec]
            self.add_row(*cells, key=str(r[key_field]))

        if self.row_count:
            target = restore_cursor_index(selected, new_keys, old_index)
            self.move_cursor(row=target)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/central_cli/test_table_view_import.py -o addopts="" -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/central_cli/central_cli/frame/__init__.py apps/central_cli/central_cli/frame/table_view.py tests/central_cli/test_table_view_import.py
git commit -m "feat(cockpit): CursorStableTable — cursor follows key across refresh"
```

---

### Task 5: DetailScreen base

**Files:**
- Create: `apps/central_cli/central_cli/frame/detail_screen.py`
- Test: `tests/central_cli/test_detail_screen_import.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/central_cli/test_detail_screen_import.py
def test_detail_screen_has_escape_binding():
    from central_cli.frame.detail_screen import DetailScreen
    keys = {b.key for b in DetailScreen.BINDINGS}
    assert "escape" in keys
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/central_cli/test_detail_screen_import.py -o addopts="" -q`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# apps/central_cli/central_cli/frame/detail_screen.py
from __future__ import annotations

from rich.console import RenderableType
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Static

from central_cli.hud_theme import CYAN, DIM, FGDIM


class DetailScreen(Screen):
    """Base for drill-down. Fuld bredde, scrollbar body, brødkrumme, Esc popper.
    Subklasser overrider `title_crumb()` og `body_renderable()`."""

    BINDINGS = [Binding("escape", "app.pop_screen", "tilbage", show=True)]

    def title_crumb(self) -> str:
        return "Central ▸ detalje"

    def body_renderable(self) -> RenderableType:
        return "(tom)"

    def compose(self) -> ComposeResult:
        yield Static(
            f"[{CYAN}]{self.title_crumb()}[/]  [{DIM}]— esc: tilbage[/]",
            id="crumb",
        )
        with VerticalScroll(id="detail-body"):
            yield Static(self.body_renderable(), id="detail-content")

    def refresh_body(self) -> None:
        try:
            self.query_one("#detail-content", Static).update(self.body_renderable())
            self.query_one("#crumb", Static).update(
                f"[{CYAN}]{self.title_crumb()}[/]  [{DIM}]— esc: tilbage[/]"
            )
        except Exception:  # skærmen kan være poppet imens
            pass
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/central_cli/test_detail_screen_import.py -o addopts="" -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/central_cli/central_cli/frame/detail_screen.py tests/central_cli/test_detail_screen_import.py
git commit -m "feat(cockpit): DetailScreen base (scrollable drill-down + breadcrumb)"
```

---

### Task 6: CommandPalette (':' modal)

**Files:**
- Create: `apps/central_cli/central_cli/frame/palette.py`
- Test: `tests/central_cli/test_palette_import.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/central_cli/test_palette_import.py
def test_palette_resolves_known_verb():
    from central_cli.frame.palette import resolve_palette_command
    spec = resolve_palette_command("status")
    assert spec is not None and spec.path.startswith("/central")


def test_palette_unknown_verb_returns_none():
    from central_cli.frame.palette import resolve_palette_command
    assert resolve_palette_command("definitelynotacommand") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/central_cli/test_palette_import.py -o addopts="" -q`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# apps/central_cli/central_cli/frame/palette.py
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input

from central_cli.commands import resolve_command


def resolve_palette_command(line: str):
    """Slå en kommando-linje op i den eksisterende dispatch. None hvis ukendt."""
    line = (line or "").strip()
    if not line:
        return None
    parts = line.split()
    try:
        return resolve_command(parts[0], parts[1:])
    except Exception:
        return None


class CommandPalette(ModalScreen[str | None]):
    """':' åbner denne. Enter → returnér kommando-linjen; Esc → None."""

    BINDINGS = [Binding("escape", "dismiss_none", "annullér")]

    def compose(self) -> ComposeResult:
        with Vertical(id="palette-box"):
            yield Input(placeholder=": kommando (fx status, resolve, nerve <navn>)",
                        id="palette-input")

    def on_mount(self) -> None:
        self.query_one("#palette-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value.strip() or None)

    def action_dismiss_none(self) -> None:
        self.dismiss(None)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/central_cli/test_palette_import.py -o addopts="" -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add apps/central_cli/central_cli/frame/palette.py tests/central_cli/test_palette_import.py
git commit -m "feat(cockpit): ':' command palette (reuses resolve_command)"
```

---

### Task 7: views/overview.py

**Files:**
- Create: `apps/central_cli/central_cli/views/__init__.py` (tom)
- Create: `apps/central_cli/central_cli/views/overview.py`
- Test: `tests/central_cli/test_views_overview.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/central_cli/test_views_overview.py
from central_cli.engine.state import HudState
from central_cli.views.overview import render_overview


def test_render_overview_from_state_returns_text():
    s = HudState()
    s.set_ok("realtime", {"status": "green", "incidents": [], "degrading": []})
    out = render_overview(s)
    assert "green" in str(out).lower() or "GREEN" in str(out)


def test_render_overview_handles_empty_state():
    s = HudState()
    out = render_overview(s)   # ingen data endnu — må ikke kaste
    assert out is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/central_cli/test_views_overview.py -o addopts="" -q`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# apps/central_cli/central_cli/views/overview.py
from __future__ import annotations

from rich.console import Group
from rich.text import Text

from central_cli.engine.state import HudState
from central_cli.hud_theme import AMBER, CYAN, DIM, FGDIM, GREEN, RED

_STATUS_COLOR = {"green": GREEN, "yellow": AMBER, "red": RED}


def render_overview(state: HudState):
    """Renderable til Overview-panelet. Læser KUN fra state (ingen fetch)."""
    e = state.get("realtime")
    data = e.data if isinstance(e.data, dict) else {}
    status = str(data.get("status", "?"))
    color = _STATUS_COLOR.get(status, DIM)

    lines: list = []
    header = Text.from_markup(f"[{color}]● {status.upper()}[/]")
    if e.error:
        header.append_text(Text.from_markup(f"  [{AMBER}]⚠ {e.error} (viser sidste gode)[/]"))
    elif e.loading and e.fetched_at == 0.0:
        header.append_text(Text.from_markup(f"  [{DIM}]henter…[/]"))
    lines.append(header)

    incidents = data.get("incidents") or []
    degrading = data.get("degrading") or []
    breakers = data.get("open_breakers") or []
    counts = Text.from_markup(
        f"[{FGDIM}]incidents[/] [{CYAN}]{len(incidents)}[/]   "
        f"[{FGDIM}]degrading[/] [{AMBER}]{len(degrading)}[/]   "
        f"[{FGDIM}]breakers[/] [{RED}]{len(breakers)}[/]"
    )
    lines.append(counts)

    cost = state.get("costs_daily").data
    if isinstance(cost, dict) and cost.get("today_usd") is not None:
        lines.append(Text.from_markup(f"[{FGDIM}]pris i dag[/] [{CYAN}]${cost['today_usd']}[/]"))

    for inc in incidents[:8]:
        msg = str(inc.get("message", ""))
        lines.append(Text.from_markup(f"  [{DIM}]•[/] {msg}"))  # u-trunkeret; panel scroller

    return Group(*lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/central_cli/test_views_overview.py -o addopts="" -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add apps/central_cli/central_cli/views/__init__.py apps/central_cli/central_cli/views/overview.py tests/central_cli/test_views_overview.py
git commit -m "feat(cockpit): overview view (renders from HudState, stale-aware)"
```

---

### Task 8: views/incidents.py + IncidentDetailScreen

**Files:**
- Create: `apps/central_cli/central_cli/views/incidents.py`
- Test: `tests/central_cli/test_views_incidents.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/central_cli/test_views_incidents.py
from central_cli.engine.state import HudState
from central_cli.views.incidents import build_incident_rows, incident_detail_text


def test_build_incident_rows_maps_fields_and_key():
    s = HudState()
    s.set_ok("realtime", {"incidents": [
        {"id": 42, "cluster": "tools", "nerve": "outcome",
         "severity": "error", "message": "Tool-fejlrate 60%"},
    ]})
    rows = build_incident_rows(s)
    assert rows[0]["id"] == "42"          # key_field
    assert rows[0]["cluster"] == "tools"
    assert "60%" in rows[0]["besked"]


def test_incident_detail_text_is_untruncated():
    long_msg = "x" * 600
    d = {"id": 1, "cluster": "c", "nerve": "n", "severity": "error", "message": long_msg}
    out = str(incident_detail_text(d))
    assert long_msg in out                # ingen [:N]-klip i detaljen
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/central_cli/test_views_incidents.py -o addopts="" -q`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# apps/central_cli/central_cli/views/incidents.py
from __future__ import annotations

from rich.console import Group
from rich.text import Text

from central_cli.engine.state import HudState
from central_cli.frame.detail_screen import DetailScreen
from central_cli.hud_theme import AMBER, CYAN, DIM, FGDIM, RED

INCIDENT_COLUMNS = (("cluster", 14), ("nerve", 18), ("sev", 7), ("besked", 44))

_SEV_COLOR = {"error": RED, "warning": AMBER, "info": DIM}


def build_incident_rows(state: HudState) -> list[dict]:
    """Rækker til CursorStableTable. Hver dict har 'id' (key) + kolonne-labels.
    'besked' vises trunkeret i tabellen (drill for fuld tekst)."""
    data = state.get("realtime").data
    incidents = (data or {}).get("incidents", []) if isinstance(data, dict) else []
    rows: list[dict] = []
    for i, inc in enumerate(incidents):
        msg = str(inc.get("message", ""))
        rows.append({
            "id": str(inc.get("id", f"idx{i}")),
            "cluster": str(inc.get("cluster", "")),
            "nerve": str(inc.get("nerve", "")),
            "sev": str(inc.get("severity", "")),
            "besked": msg if len(msg) <= 42 else msg[:41] + "…",
            "_raw": inc,
        })
    return rows


def incident_detail_text(inc: dict):
    """Fuld, u-trunkeret detalje-renderable til IncidentDetailScreen."""
    sev = str(inc.get("severity", ""))
    color = _SEV_COLOR.get(sev, FGDIM)
    parts = [
        Text.from_markup(
            f"[{CYAN}]{inc.get('cluster','')}[/] ▸ [{CYAN}]{inc.get('nerve','')}[/]  "
            f"[{color}]{sev}[/]  [{DIM}]{inc.get('ts','')}[/]"
        ),
        Text(""),
        Text.from_markup(f"[{FGDIM}]besked[/]"),
        Text(str(inc.get("message", ""))),
    ]
    rc = inc.get("root_cause") or inc.get("signature")
    if rc:
        parts += [Text(""), Text.from_markup(f"[{FGDIM}]root-cause[/]"), Text(str(rc))]
    corr = inc.get("correlation")
    if isinstance(corr, dict):
        parts += [Text(""), Text.from_markup(
            f"[{FGDIM}]korrelation[/] count={corr.get('count','?')} "
            f"first={corr.get('first','?')} last={corr.get('last','?')}")]
    return Group(*parts)


class IncidentDetailScreen(DetailScreen):
    def __init__(self, inc: dict) -> None:
        super().__init__()
        self._inc = inc

    def title_crumb(self) -> str:
        return f"Central ▸ Incidents ▸ {self._inc.get('cluster','')}:{self._inc.get('nerve','')}"

    def body_renderable(self):
        return incident_detail_text(self._inc)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/central_cli/test_views_incidents.py -o addopts="" -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add apps/central_cli/central_cli/views/incidents.py tests/central_cli/test_views_incidents.py
git commit -m "feat(cockpit): incidents view + untruncated IncidentDetailScreen"
```

---

### Task 9: views/nerves.py + NerveDetailScreen

**Files:**
- Create: `apps/central_cli/central_cli/views/nerves.py`
- Test: `tests/central_cli/test_views_nerves.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/central_cli/test_views_nerves.py
from central_cli.engine.state import HudState
from central_cli.views.nerves import build_nerve_rows, nerve_detail_text, nerve_detail_surface_key


def test_build_nerve_rows_uses_name_as_key():
    s = HudState()
    s.set_ok("realtime", {"nerves": [
        {"nerve": "council", "cluster": "agents", "state": "aktiv"},
    ]})
    rows = build_nerve_rows(s)
    assert rows[0]["nerve"] == "council"
    assert rows[0]["cluster"] == "agents"


def test_nerve_detail_surface_key_is_namespaced():
    assert nerve_detail_surface_key("council") == "nerve_detail:council"


def test_nerve_detail_text_shows_recent_observations_with_reason():
    detail = {"recent": [
        {"decision": "escalate", "reason": "pattern repeated 3x", "payload": {"x": 1}},
    ]}
    out = str(nerve_detail_text("council", detail))
    assert "escalate" in out and "pattern repeated 3x" in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/central_cli/test_views_nerves.py -o addopts="" -q`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# apps/central_cli/central_cli/views/nerves.py
from __future__ import annotations

from rich.console import Group
from rich.text import Text

from central_cli.engine.state import HudState
from central_cli.frame.detail_screen import DetailScreen
from central_cli.hud_theme import CYAN, DIM, FGDIM, GREEN

NERVE_COLUMNS = (("cluster", 16), ("nerve", 24), ("state", 14))


def build_nerve_rows(state: HudState) -> list[dict]:
    data = state.get("realtime").data
    nerves = (data or {}).get("nerves", []) if isinstance(data, dict) else []
    rows: list[dict] = []
    for n in nerves:
        rows.append({
            "nerve": str(n.get("nerve", "")),          # key_field
            "cluster": str(n.get("cluster", "")),
            "state": str(n.get("state", "")),
            "_raw": n,
        })
    return rows


def nerve_detail_surface_key(nerve: str) -> str:
    return f"nerve_detail:{nerve}"


def nerve_detail_path(nerve: str) -> str:
    return f"/central/nerve/{nerve}"


def nerve_detail_text(nerve: str, detail: dict | None):
    parts = [Text.from_markup(f"[{CYAN}]{nerve}[/]  [{DIM}]seneste beslutninger[/]"), Text("")]
    if not isinstance(detail, dict):
        parts.append(Text.from_markup(f"[{DIM}]henter…[/]"))
        return Group(*parts)
    recent = detail.get("recent") or []
    if not recent:
        parts.append(Text.from_markup(f"[{DIM}]ingen observationer[/]"))
    for obs in recent[:30]:
        parts.append(Text.from_markup(
            f"[{GREEN}]{obs.get('decision','?')}[/]  [{FGDIM}]{obs.get('reason','')}[/]"))
        payload = obs.get("payload")
        if payload:
            parts.append(Text.from_markup(f"    [{DIM}]{payload}[/]"))
    return Group(*parts)


class NerveDetailScreen(DetailScreen):
    """Drill-detalje for én nerve. Læser sin egen surface (nerve_detail:<navn>)
    fra HudState; appen starter en on-demand worker når skærmen pushes."""

    def __init__(self, nerve: str, state: HudState) -> None:
        super().__init__()
        self._nerve = nerve
        self._state = state

    def title_crumb(self) -> str:
        return f"Central ▸ Nerves ▸ {self._nerve}"

    def body_renderable(self):
        entry = self._state.get(nerve_detail_surface_key(self._nerve))
        return nerve_detail_text(self._nerve, entry.data if isinstance(entry.data, dict) else None)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/central_cli/test_views_nerves.py -o addopts="" -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add apps/central_cli/central_cli/views/nerves.py tests/central_cli/test_views_nerves.py
git commit -m "feat(cockpit): nerves view + NerveDetailScreen (per-nerve decision trace)"
```

---

### Task 10: CockpitApp shell + flag-wiring

**Files:**
- Create: `apps/central_cli/central_cli/frame/app.py`
- Modify: `apps/central_cli/central_cli/main.py` (tilføj `--v2`)
- Modify: `apps/central_cli/central_cli/hud.py` (run_hud vælger v2 via flag/env)
- Test: `tests/central_cli/test_cockpit_pilot.py` (Step 1 nedenfor)

- [ ] **Step 1: Write the failing test (pilot — cursor-stabilitet + drill)**

```python
# tests/central_cli/test_cockpit_pilot.py
import asyncio
import pytest
from central_cli.engine.state import HudState
from central_cli.frame.app import CockpitApp


class _FakeClient:
    def get_json(self, path, params=None):
        if path == "/central/realtime":
            return {"status": "green",
                    "incidents": [{"id": str(i), "cluster": "c", "nerve": "n",
                                   "severity": "error", "message": f"m{i}"} for i in range(5)],
                    "nerves": [{"nerve": f"nv{i}", "cluster": "c", "state": "aktiv"}
                               for i in range(5)], "degrading": [], "open_breakers": []}
        if path == "/central/costs-daily":
            return {"today_usd": 0.03}
        if path == "/central/diagnostics":
            return {"incidents": [], "root_causes": []}
        if path.startswith("/central/nerve/"):
            return {"recent": [{"decision": "d", "reason": "r", "payload": {}}]}
        return {}


@pytest.mark.asyncio
async def test_cursor_survives_refresh_and_enter_drills():
    app = CockpitApp(client=_FakeClient(), state=HudState())
    async with app.run_test() as pilot:
        await app.seed_now()                 # synkron seed så tabellen har rækker
        await app.switch_tab("incidents")
        await pilot.pause()
        table = app.active_table()
        table.move_cursor(row=2)
        key_before = table._selected_key()
        app.rerender_active()                # simulér refresh-tick
        await pilot.pause()
        assert table._selected_key() == key_before   # markør IKKE hoppet
        await pilot.press("enter")           # drill ind
        await pilot.pause()
        assert app.screen_stack[-1].__class__.__name__ == "IncidentDetailScreen"
        await pilot.press("escape")
        await pilot.pause()
        assert app.screen_stack[-1].__class__.__name__ != "IncidentDetailScreen"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/central_cli/test_cockpit_pilot.py -o addopts="" -q`
Expected: FAIL — `ModuleNotFoundError: central_cli.frame.app`

- [ ] **Step 3: Write minimal implementation**

```python
# apps/central_cli/central_cli/frame/app.py
from __future__ import annotations

import asyncio

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Static

from central_cli.engine.state import HudState
from central_cli.engine.workers import SURFACE_CADENCE, fetch_detail, fetch_surface
from central_cli.frame.palette import CommandPalette
from central_cli.frame.table_view import CursorStableTable
from central_cli.hud_theme import BG, CYAN, FGDIM
from central_cli.views import incidents as v_inc
from central_cli.views import nerves as v_nrv
from central_cli.views.overview import render_overview

_TABS = ["overview", "incidents", "nerves"]


class CockpitApp(App):
    CSS = f"""
    Screen {{ background: {BG}; }}
    #tabs {{ height: 1; background: {BG}; color: {FGDIM}; }}
    #body {{ height: 1fr; }}
    CursorStableTable {{ height: 1fr; }}
    #ovpanel {{ height: 1fr; padding: 1 2; }}
    #footer {{ height: 1; color: {FGDIM}; }}
    """
    BINDINGS = [
        Binding("tab", "next_tab", "fane→", show=False),
        Binding("shift+tab", "prev_tab", "←fane", show=False),
        Binding("enter", "drill", "åbn", show=True),
        Binding("colon", "palette", "kommando", show=True),
        Binding("ctrl+q", "quit", "afslut", show=False),
    ]

    def __init__(self, *, client, state: HudState | None = None) -> None:
        super().__init__()
        self._client = client
        self._state = state or HudState()
        self._tab = "overview"

    def compose(self) -> ComposeResult:
        yield Static(self._tab_bar(), id="tabs")
        with VerticalScroll(id="body"):
            yield Static(render_overview(self._state), id="ovpanel")
            yield CursorStableTable(*v_inc.INCIDENT_COLUMNS, id="incidents-table")
            yield CursorStableTable(*v_nrv.NERVE_COLUMNS, id="nerves-table")
        yield Static("", id="footer")

    def _tab_bar(self) -> str:
        cells = []
        for t in _TABS:
            mark = f"[{CYAN}]{t}[/]" if t == self._tab else f"[{FGDIM}]{t}[/]"
            cells.append(mark)
        return "  ".join(cells)

    # ── lifecycle ──
    def on_mount(self) -> None:
        self._show_tab(self._tab)
        for surface in SURFACE_CADENCE:
            self.run_worker(self._poll(surface), exclusive=False, group=f"poll:{surface}")
        self.set_interval(1.0, self.rerender_active)

    async def _poll(self, surface: str) -> None:
        cadence = SURFACE_CADENCE[surface]
        while True:
            await fetch_surface(self._client, self._state, surface)
            self.rerender_active()
            await asyncio.sleep(cadence)

    # ── test-hjælpere (synkron seed så pilot ikke skal vente på polling) ──
    async def seed_now(self) -> None:
        for surface in SURFACE_CADENCE:
            await fetch_surface(self._client, self._state, surface)
        self.rerender_active()

    async def switch_tab(self, tab: str) -> None:
        self._tab = tab
        self._show_tab(tab)

    def active_table(self) -> CursorStableTable | None:
        if self._tab == "incidents":
            return self.query_one("#incidents-table", CursorStableTable)
        if self._tab == "nerves":
            return self.query_one("#nerves-table", CursorStableTable)
        return None

    # ── rendering ──
    def _show_tab(self, tab: str) -> None:
        self.query_one("#ovpanel", Static).display = tab == "overview"
        self.query_one("#incidents-table", CursorStableTable).display = tab == "incidents"
        self.query_one("#nerves-table", CursorStableTable).display = tab == "nerves"
        self.query_one("#tabs", Static).update(self._tab_bar())
        self.rerender_active()

    def rerender_active(self) -> None:
        try:
            if self._tab == "overview":
                self.query_one("#ovpanel", Static).update(render_overview(self._state))
            elif self._tab == "incidents":
                self.query_one("#incidents-table", CursorStableTable).update_rows(
                    v_inc.build_incident_rows(self._state), key_field="id")
            elif self._tab == "nerves":
                self.query_one("#nerves-table", CursorStableTable).update_rows(
                    v_nrv.build_nerve_rows(self._state), key_field="nerve")
        except Exception as exc:  # en enkelt render-fejl må aldrig vælte skallen
            try:
                self.query_one("#footer", Static).update(f"[red]render: {exc}[/red]")
            except Exception:
                pass

    # ── actions ──
    def action_next_tab(self) -> None:
        self._tab = _TABS[(_TABS.index(self._tab) + 1) % len(_TABS)]
        self._show_tab(self._tab)

    def action_prev_tab(self) -> None:
        self._tab = _TABS[(_TABS.index(self._tab) - 1) % len(_TABS)]
        self._show_tab(self._tab)

    def action_drill(self) -> None:
        table = self.active_table()
        if table is None or table.row_count == 0:
            return
        key = table._selected_key()
        if self._tab == "incidents":
            for r in v_inc.build_incident_rows(self._state):
                if r["id"] == key:
                    self.push_screen(v_inc.IncidentDetailScreen(r["_raw"]))
                    return
        elif self._tab == "nerves":
            self.run_worker(
                fetch_detail(self._client, self._state,
                             v_nrv.nerve_detail_surface_key(key), v_nrv.nerve_detail_path(key)),
                exclusive=True, group="nerve-detail")
            screen = v_nrv.NerveDetailScreen(key, self._state)
            self.push_screen(screen)
            self.set_interval(0.5, screen.refresh_body)  # opdatér når detaljen lander

    def action_palette(self) -> None:
        def _run(line: str | None) -> None:
            if not line:
                return
            spec = None
            try:
                from central_cli.frame.palette import resolve_palette_command
                spec = resolve_palette_command(line)
            except Exception:
                spec = None
            if spec is None:
                self.query_one("#footer", Static).update(f"[red]ukendt: {line}[/red]")
                return
            self.query_one("#footer", Static).update(f"[dim]{line} → {spec.path}[/dim]")
        self.push_screen(CommandPalette(), _run)
```

- [ ] **Step 4: Run pilot test to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/central_cli/test_cockpit_pilot.py -o addopts="" -q`
Expected: PASS (1 passed). If `pytest.mark.asyncio` is unknown, ensure `pytest-asyncio` is installed in the ai env (`/opt/conda/envs/ai/bin/pip install pytest-asyncio`) or add `asyncio_mode = auto` — verify with the run.

- [ ] **Step 5: Wire the flag in main.py + hud.run_hud**

Modify `apps/central_cli/central_cli/main.py` — add after the `--no-boot` line (around line 14):

```python
    p.add_argument("--v2", action="store_true", help="Nyt cockpit (async ramme)")
```

Modify `apps/central_cli/central_cli/hud.py` `run_hud` (around line 497) — replace the body:

```python
def run_hud(ns) -> int:
    import os
    from central_cli.client import CentralClient
    from central_cli.config import resolve_base_url, resolve_token

    client = CentralClient(base_url=resolve_base_url(remote=ns.remote), token=resolve_token())
    use_v2 = getattr(ns, "v2", False) or os.environ.get("CENTRAL_COCKPIT_V2") == "1"
    if use_v2:
        from central_cli.frame.app import CockpitApp
        CockpitApp(client=client).run()
        return 0
    CentralHud(client=client, live=True).run()
    return 0
```

- [ ] **Step 6: Verify flag path imports cleanly**

Run: `/opt/conda/envs/ai/bin/python -c "from central_cli.frame.app import CockpitApp; from central_cli.main import build_arg_parser; ns=build_arg_parser().parse_args(['--v2']); assert ns.v2"`
Expected: no output, exit 0

- [ ] **Step 7: Commit**

```bash
git add apps/central_cli/central_cli/frame/app.py apps/central_cli/central_cli/main.py apps/central_cli/central_cli/hud.py tests/central_cli/test_cockpit_pilot.py
git commit -m "feat(cockpit): CockpitApp shell + CENTRAL_COCKPIT_V2 flag wiring"
```

---

### Task 11: Visual verification (render → screenshot → read)

**Files:**
- Create: `tests/central_cli/test_cockpit_screenshot.py`

**Rationale:** feedback_verify_visual_before_done — erklær aldrig UI virkende uden at have SET det rendere.

- [ ] **Step 1: Write the screenshot-producing test**

```python
# tests/central_cli/test_cockpit_screenshot.py
import pytest
from central_cli.engine.state import HudState
from central_cli.frame.app import CockpitApp
from tests.central_cli.test_cockpit_pilot import _FakeClient


@pytest.mark.asyncio
async def test_screenshot_incidents_tab(tmp_path):
    app = CockpitApp(client=_FakeClient(), state=HudState())
    async with app.run_test(size=(120, 40)) as pilot:
        await app.seed_now()
        await app.switch_tab("incidents")
        await pilot.pause()
        svg = tmp_path / "cockpit-incidents.svg"
        app.save_screenshot(str(svg))
        assert svg.exists() and svg.stat().st_size > 1000
        print(f"SCREENSHOT: {svg}")
```

- [ ] **Step 2: Run it and produce the SVG**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/central_cli/test_cockpit_screenshot.py -o addopts="" -q -s`
Expected: PASS, prints `SCREENSHOT: /tmp/.../cockpit-incidents.svg`

- [ ] **Step 3: Convert to PNG and LOOK at it**

```bash
SVG=$(/opt/conda/envs/ai/bin/python -m pytest tests/central_cli/test_cockpit_screenshot.py -o addopts="" -q -s 2>/dev/null | grep -o '/[^ ]*cockpit-incidents.svg' | head -1)
rsvg-convert "$SVG" -o /tmp/cockpit-incidents.png
```
Then Read `/tmp/cockpit-incidents.png` and confirm: tab-bar shows overview/incidents/nerves, an incidents table with rows renders, footer present. Only declare Phase 1 visually done after seeing this.

- [ ] **Step 4: Commit**

```bash
git add tests/central_cli/test_cockpit_screenshot.py
git commit -m "test(cockpit): headless screenshot verification of incidents tab"
```

---

## Self-Review

**Spec coverage:**
- Async never-freeze data engine → Task 1 (HudState) + Task 3 (workers, to_thread). ✓
- Cursor-stable diff-refresh → Task 2 (rowdiff) + Task 4 (CursorStableTable) + Task 10 pilot asserts cursor survives. ✓
- Scroll containers everywhere → `VerticalScroll` in DetailScreen (Task 5) + `#body` in app (Task 10). ✓
- Drill-down Screen stack → Task 5 (base) + Task 8/9 (incident/nerve screens) + Task 10 (push/pop). ✓
- Focus-driven key dispatch + ':' palette → Task 6 + Task 10 BINDINGS. ✓
- 3 proof views → Task 7/8/9. ✓
- Un-truncated detail → Task 8 test asserts 600-char message survives. ✓
- Per-nerve decision trace → Task 9 (nerve_detail via /central/nerve/{name}). ✓
- Flag + old HUD preserved → Task 10 Step 5. ✓
- Module split (<300 lines) → file structure; each file single-responsibility. ✓
- Render→screenshot verification → Task 11. ✓
- Resolve-key reserved (wired in Phase 3) → not implemented here by design (non-goal). ✓

**Placeholder scan:** No TBD/TODO; every code step has complete code. One environmental caveat flagged honestly in Task 10 Step 4 (pytest-asyncio availability) with a concrete resolution.

**Type consistency:** `HudState.get/set_ok/set_error/is_stale/set_loading` used consistently across Tasks 1,3,7,8,9,10. `CursorStableTable.update_rows(rows, key_field=...)` + `_selected_key()` consistent (Tasks 4,10). `build_incident_rows`/`build_nerve_rows` return dicts with `id`/`nerve` key-fields matching `key_field` args in Task 10. `SURFACE_CADENCE`/`SURFACE_PATHS`/`fetch_surface`/`fetch_detail` consistent (Tasks 3,10). Detail screens subclass `DetailScreen` with `title_crumb`/`body_renderable` (Tasks 5,8,9). ✓
