"""Central HUD — action handlers + command/write layer (``_ActionMixin``).

All ``action_*`` key handlers, the always-on command line (``_run_command`` and
its read-render helpers), navigation helpers, drill/toggle, and the shared
write/confirm machinery for governance + healer flags. Extracted verbatim from
``hud.py`` (behaviour-preserving split); every method resolves on the combined
``CentralHud`` instance, so calls into the populate mixin / shell work unchanged.
"""

from __future__ import annotations

from typing import Any

from rich.text import Text

from textual.widgets import DataTable, Input, RichLog, Static

from central_cli.hud_theme import (
    _esc,
    CYAN, AMBER, RED, GREEN, DIM, FG, FGDIM,
)


class _ActionMixin:
    """Action-side of the Central HUD: key handlers, command line, writes."""

    # -- actions -----------------------------------------------------------
    def action_show(self, name: str) -> None:
        self.show_tab(name)

    def action_help(self) -> None:
        return

    # -- navigation (works while the input stays focused) ------------------
    def _table(self) -> DataTable | None:
        from central_cli.hud import _TABLE_TABS
        if self.active_tab not in _TABLE_TABS:
            return None
        try:
            return self.query_one("#nerve-table", DataTable)
        except Exception:
            return None

    def _refresh_detail_for_current(self) -> None:
        """Render the detail panel for whichever row the cursor is on (used after
        a populate/refresh so the side panel reflects the selection, not incidents)."""
        t = self._table()
        row = 0
        if t is not None:
            try:
                row = int(t.cursor_row or 0)
            except Exception:
                row = 0
        self._render_row_detail(row)

    def _after_cursor_move(self, t: DataTable) -> None:
        """Refresh the detail panel for the newly-selected row (robust — does not
        rely on the RowHighlighted event firing from a programmatic cursor move)."""
        try:
            self._render_row_detail(int(t.cursor_row or 0))
        except Exception:
            pass

    def action_nav_up(self) -> None:
        t = self._table()
        if t is not None:
            t.action_cursor_up()
            self._after_cursor_move(t)

    def action_nav_down(self) -> None:
        t = self._table()
        if t is not None:
            t.action_cursor_down()
            self._after_cursor_move(t)

    def action_nav_pageup(self) -> None:
        t = self._table()
        if t is not None:
            t.action_page_up()
            self._after_cursor_move(t)

    def action_nav_pagedown(self) -> None:
        t = self._table()
        if t is not None:
            t.action_page_down()
            self._after_cursor_move(t)

    def _cycle_tab(self, step: int) -> None:
        from central_cli.hud import _TABS
        keys = [k for k, _, _ in _TABS]
        try:
            i = keys.index(self.active_tab)
        except ValueError:
            i = 0
        self.show_tab(keys[(i + step) % len(keys)])

    def action_next_tab(self) -> None:
        self._cycle_tab(1)

    def action_prev_tab(self) -> None:
        self._cycle_tab(-1)

    def action_cancel(self) -> None:
        """Esc: clear a half-typed command, else cancel a pending confirm."""
        try:
            inp = self.query_one("#hud-cmd-input", Input)
        except Exception:
            inp = None
        if inp is not None and inp.value:
            inp.value = ""
            return
        if self._pending_write is not None:
            self.action_confirm_no()

    # -- command line (always-on terminal prompt) --------------------------
    def on_input_submitted(self, event: Input.Submitted) -> None:  # noqa: ANN001
        val = (event.value or "").strip()
        try:
            self.query_one("#hud-cmd-input", Input).value = ""
        except Exception:
            pass
        # A pending dangerous confirm: y/yes/enter = confirm, n/no = cancel.
        if self._pending_write is not None:
            low = val.lower()
            if val == "" or low in ("y", "yes", "j", "ja"):
                self.action_confirm_yes()
            elif low in ("n", "no", "nej"):
                self.action_confirm_no()
            self._keep_focus()
            return
        if val == "":
            # Empty Enter = drill/select the current row.
            t = self._table()
            if t is not None:
                self._drill_row(int(t.cursor_row or 0))
            self._keep_focus()
            return
        self._run_command(val)
        self._keep_focus()

    def _run_command(self, line: str) -> None:
        """Parse + execute a command via the shared resolve_command layer.
        Read results render FULLY into the detail panel; writes flash in the feed."""
        parts = line.split()
        verb, args = parts[0].lower(), parts[1:]
        try:
            from central_cli.commands import resolve_command
            spec = resolve_command(verb, args)
        except Exception as exc:
            self._flash(f"[{RED}]✖ {verb}: {_esc(str(exc))}[/]")
            return
        try:
            if spec.method == "GET":
                data = self._client.get_json(spec.path, spec.body)
            else:
                data = self._client.post_json(spec.path, spec.body or {})
        except Exception as exc:
            self._flash(f"[{RED}]✖ {_esc(line)}: {_esc(str(exc))}[/]")
            return
        if spec.method == "GET":
            # read: render the full result and DON'T refresh (would clobber it)
            if verb == "feel":
                self._show_feel(data)
            else:
                self._show_command_output(line, data)
        else:
            ok = isinstance(data, dict) and data.get("ok")
            tail = f"[{GREEN}]ok[/]" if ok else f"[{RED}]{_esc(str((data or {}).get('error', data)))[:80]}[/]"
            self._flash(f"[{CYAN}]▸ {_esc(line)}[/] [{DIM}]—[/] {tail}")
            self.refresh_data()

    def _show_feel(self, data: Any) -> None:
        """Render Jarvis' somatic snapshot as his own voice in the detail panel."""
        try:
            panel = self.query_one("#hud-detail", Static)
        except Exception:
            return
        lines = (data or {}).get("lines") or [] if isinstance(data, dict) else []
        self._set_side_paneh(f"[{CYAN}]JARVIS FØLER[/] [{DIM}]— somatisk snapshot[/]")
        if not lines:
            panel.update(Text.from_markup(f"[{FGDIM}]— stille indeni lige nu —[/]"))
        else:
            out = [f"[{GREEN} b]◈ INDRE LIV[/]", ""]
            for ln in lines:
                out.append(f"[{DIM}]·[/] [{FG}]{_esc(ln)}[/]")
                out.append("")
            panel.update(Text.from_markup("\n".join(out)))
        try:
            self.query_one("#hud-panel", Static).display = False
            self.query_one("#hud-side").display = True
        except Exception:
            pass

    def _show_command_output(self, line: str, data: Any) -> None:
        """Render a read command's FULL result into the detail panel (scrollable)."""
        import json
        try:
            panel = self.query_one("#hud-detail", Static)
        except Exception:
            return
        self._set_side_paneh(f"[{CYAN}]KOMMANDO[/] [{DIM}]— {_esc(line)}[/]")
        try:
            pretty = json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True)
        except Exception:
            pretty = str(data)
        body = "\n".join(_esc(ln) for ln in pretty.splitlines()[:400])
        panel.update(Text.from_markup(f"[{FG}]{body}[/]"))
        # ensure the detail panel is the visible one
        try:
            self.query_one("#hud-panel", Static).display = False
            self.query_one("#hud-side").display = True
        except Exception:
            pass

    def _drill_incident(self, index: int) -> None:
        self._sel_incident = index
        self._render_detail_panel()

    def on_data_table_row_highlighted(self, event) -> None:  # noqa: ANN001
        try:
            row = int(getattr(event, "cursor_row", 0) or 0)
        except Exception:
            row = 0
        self._render_row_detail(row)

    def on_data_table_row_selected(self, event) -> None:  # noqa: ANN001
        try:
            index = int(getattr(event, "cursor_row", 0) or 0)
        except Exception:
            index = 0
        self._drill_row(index)

    def _drill_row(self, index: int) -> None:
        """Enter/select on a row: governance toggles, others (re)show detail."""
        if self.active_tab == "governance":
            self._toggle_governance_row(index)
        else:
            self._render_row_detail(index)

    # -- Governance writes -------------------------------------------------
    def _next_value(self, flag: dict) -> Any:
        kind = str(flag.get("kind") or "")
        value = flag.get("value")
        if kind == "enum":
            options = list(flag.get("options") or [])
            if not options:
                return value
            try:
                idx = options.index(value)
            except ValueError:
                idx = -1
            return options[(idx + 1) % len(options)]
        return not bool(value)

    def _toggle_governance_row(self, index: int) -> None:
        flags = self._gov_flags or []
        if index < 0 or index >= len(flags):
            return
        flag = flags[index]
        key = flag.get("key")
        if key is None:
            return
        self._set_governance(key, self._next_value(flag))

    def _set_governance(self, key: Any, value: Any) -> None:
        payload = {"key": key, "value": value, "confirm": False}
        try:
            resp = self._client.post_json("/central/governance/set", payload)
        except Exception as exc:
            self._flash(f"[{RED}]✖ skrivefejl: {exc}[/]")
            return
        self._handle_write_response("governance", payload, resp)

    # -- Healer writes -----------------------------------------------------
    def _toggle_healer_row(self, index: int) -> None:
        healers = (self._healers.get("healers") or []) if self._healers else []
        if index < 0 or index >= len(healers):
            return
        healer = healers[index]
        flag = self._healer_flag_name(healer)
        if flag is None:
            self._flash(f"[{DIM}]— healer er ikke flag-styret —[/]")
            return
        self._set_healer(flag, not bool(healer.get("live_flag_on")))

    def _set_healer(self, name: Any, enabled: bool) -> None:
        payload = {"name": name, "enabled": enabled, "confirm": False}
        try:
            resp = self._client.post_json("/central/healers/flag", payload)
        except Exception as exc:
            self._flash(f"[{RED}]✖ skrivefejl: {exc}[/]")
            return
        self._handle_write_response("healer", payload, resp)

    # -- shared write / confirm --------------------------------------------
    def _write_path(self, kind: str) -> str:
        return ("/central/governance/set" if kind == "governance"
                else "/central/healers/flag")

    def _write_desc(self, kind: str, payload: dict) -> str:
        if kind == "governance":
            return f"{payload.get('key')}={self._fmt_value(payload.get('value'))}"
        return f"{payload.get('name')}={'on' if payload.get('enabled') else 'off'}"

    def _handle_write_response(self, kind: str, payload: dict, resp: Any) -> None:
        resp = resp if isinstance(resp, dict) else {}
        if resp.get("needs_confirm"):
            self._pending_write = (kind, payload)
            self._flash(f"[{AMBER} b]⚠ bekræft {self._write_desc(kind, payload)}? y/n[/]")
            return
        if resp.get("ok"):
            self._pending_write = None
            self._flash(f"[{GREEN}]✓ sat: {self._write_desc(kind, payload)}[/]")
            self.refresh_data()
            return
        err = resp.get("error") or "ukendt fejl"
        self._flash(f"[{RED}]✖ {err}[/]")

    def _confirm_line(self) -> str:
        if self._pending_write is None:
            return ""
        kind, payload = self._pending_write
        return f"[{AMBER} b]⚠ bekræft {self._write_desc(kind, payload)}? y/n[/]"

    def action_toggle(self) -> None:
        if self.active_tab == "governance":
            try:
                table = self.query_one("#nerve-table", DataTable)
                index = int(table.cursor_row or 0)
            except Exception:
                index = 0
            self._toggle_governance_row(index)

    def action_confirm_yes(self) -> None:
        if self._pending_write is None:
            return
        kind, payload = self._pending_write
        confirmed = dict(payload)
        confirmed["confirm"] = True
        try:
            resp = self._client.post_json(self._write_path(kind), confirmed)
        except Exception as exc:
            self._pending_write = None
            self._flash(f"[{RED}]✖ skrivefejl: {exc}[/]")
            return
        resp = resp if isinstance(resp, dict) else {}
        self._pending_write = None
        if resp.get("ok"):
            self._flash(f"[{GREEN}]✓ sat: {self._write_desc(kind, confirmed)}[/]")
        else:
            self._flash(f"[{RED}]✖ {resp.get('error') or 'afvist'}[/]")
        self.refresh_data()

    def action_confirm_no(self) -> None:
        if self._pending_write is None:
            return
        self._pending_write = None
        self._flash(f"[{DIM}]— afbrudt —[/]")

    def _flash(self, markup: str) -> None:
        from central_cli.hud import _TABLE_TABS
        try:
            if self.active_tab in _TABLE_TABS:
                self.query_one("#hud-feed", RichLog).write(markup)
            elif self.active_tab == "healing":
                self._render_healing_panel()
        except Exception:
            return
