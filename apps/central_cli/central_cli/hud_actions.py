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

    def _active_panel(self):
        """Det synlige panel (#hud-panel) hvis en panel-fane (overview/mind/
        diagnostics/…) er aktiv — ellers None. Bruges så pil/side-taster scroller
        panelet i stedet for at være døde på ikke-tabel-faner (Mind kunne ikke
        køres ned)."""
        try:
            p = self.query_one("#hud-panelbox")
            if getattr(p, "display", False):
                return p
        except Exception:
            pass
        return None

    def action_nav_up(self) -> None:
        p = self._active_panel()
        if p is not None:
            p.scroll_up(animate=False)
            return
        t = self._table()
        if t is not None:
            t.action_cursor_up()
            self._after_cursor_move(t)

    def action_nav_down(self) -> None:
        p = self._active_panel()
        if p is not None:
            p.scroll_down(animate=False)
            return
        t = self._table()
        if t is not None:
            t.action_cursor_down()
            self._after_cursor_move(t)

    def action_nav_pageup(self) -> None:
        p = self._active_panel()
        if p is not None:
            p.scroll_page_up(animate=False)
            return
        t = self._table()
        if t is not None:
            t.action_page_up()
            self._after_cursor_move(t)

    def action_nav_pagedown(self) -> None:
        p = self._active_panel()
        if p is not None:
            p.scroll_page_down(animate=False)
            return
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
        if self._pending_approval is not None:
            self._pending_approval = None
            self._flash(f"[{DIM}]— annulleret —[/]")
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
        # A pending approval (approvals-fanen): ↵/ja = godkend, nej = afvis.
        if self._pending_approval is not None:
            low = val.lower()
            if val == "" or low in ("y", "yes", "j", "ja", "godkend"):
                self._resolve_approval(True)
            elif low in ("n", "no", "nej", "afvis"):
                self._resolve_approval(False)
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
            self.query_one("#hud-panelbox").display = False
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
            self.query_one("#hud-panelbox").display = False
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
        """Enter/select on a row: governance toggles, approvals arms godkend/afvis,
        others (re)show detail."""
        if self.active_tab == "governance":
            self._toggle_governance_row(index)
        elif self.active_tab == "approvals":
            self._begin_approval(index)
        else:
            self._render_row_detail(index)

    # -- Approvals: godkend/afvis direkte i Centralen ----------------------
    def _begin_approval(self, index: int) -> None:
        """Enter på et forslag: armér en godkend/afvis-bekræftelse. Bekræftes via
        kommando-linjen (ja/nej) som de øvrige writes — ingen tast-konflikt."""
        proposals = (getattr(self, "_autonomy", None) or {}).get("proposals") or []
        if index < 0 or index >= len(proposals):
            return
        p = proposals[index]
        pid = p.get("proposal_id") or p.get("id")
        if pid is None:
            self._flash(f"[{DIM}]— forslag mangler id —[/]")
            return
        title = str(p.get("title") or p.get("summary") or p.get("kind") or pid)
        self._pending_approval = (str(pid), title)
        self._flash(
            f"[{AMBER} b]⚠ forslag '{_esc(title[:60])}': "
            f"[j]a/↵ = godkend · n = afvis · esc = annullér[/]"
        )

    def _resolve_approval(self, approve: bool) -> None:
        if self._pending_approval is None:
            return
        pid, title = self._pending_approval
        self._pending_approval = None
        path = (f"/mc/autonomy/proposals/{pid}/approve" if approve
                else f"/mc/autonomy/proposals/{pid}/reject")
        try:
            resp = self._client.post_json(path, {})
        except Exception as exc:
            self._flash(f"[{RED}]✖ {_esc(str(exc))}[/]")
            return
        ok = isinstance(resp, dict) and (resp.get("ok") or resp.get("status") == "ok"
                                         or resp.get("resolved"))
        verb = "godkendt" if approve else "afvist"
        if ok:
            self._flash(f"[{GREEN}]✓ forslag {verb}: {_esc(title[:50])}[/]")
        else:
            err = (resp or {}).get("error") if isinstance(resp, dict) else resp
            self._flash(f"[{RED}]✖ {verb} fejlede: {_esc(str(err))[:80]}[/]")
        self.refresh_data()

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
        if kind == "agent_abort":
            return f"afbryd agent {payload.get('label')}"
        if kind == "slot_disable":
            return f"deaktivér slot {payload.get('label')}"
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
        # Generic "POST to a path" confirms (agent abort / slot disable): these
        # don't ride the governance/healer key+value contract — they carry the
        # full path + body and just fire once confirmed.
        if kind in ("agent_abort", "slot_disable"):
            self._pending_write = None
            label = str(payload.get("label", "") or "")
            ok_msg = (f"agent afbrudt: {label}" if kind == "agent_abort"
                      else f"slot deaktiveret: {label}")
            fail = ("afbryd fejlede" if kind == "agent_abort"
                    else "deaktivér fejlede")
            self._post_action(payload["path"], payload.get("body") or {},
                              ok_msg, fail)
            return
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

    # -- Agent / balancer row actions --------------------------------------
    def _selected_row(self, rows: list) -> dict | None:
        """The row dict under the cursor for the active table-tab, or None."""
        if not rows:
            return None
        idx = 0
        t = self._table()
        if t is not None:
            try:
                idx = int(t.cursor_row or 0)
            except Exception:
                idx = 0
        if 0 <= idx < len(rows):
            return rows[idx]
        return None

    def _post_action(self, path: str, body: dict, ok_msg: str,
                     fail: str) -> None:
        """POST + surface feedback in the feed, then refresh. Self-safe."""
        try:
            resp = self._client.post_json(path, body or {})
        except Exception as exc:
            self._flash(f"[{RED}]✖ {fail}: {_esc(str(exc))[:80]}[/]")
            return
        ok = isinstance(resp, dict) and (resp.get("ok")
                                         or resp.get("status") == "ok")
        if ok:
            self._flash(f"[{GREEN}]✓ {_esc(ok_msg)}[/]")
        else:
            err = (resp or {}).get("error") if isinstance(resp, dict) else resp
            self._flash(f"[{RED}]✖ {fail}: {_esc(str(err))[:80]}[/]")
        self.refresh_data()

    def action_agent_pause(self) -> None:
        """`p` on the Agents tab: pause the selected agent (only if active)."""
        if self.active_tab != "agents":
            return
        row = self._selected_row(self._agent_rows or [])
        if row is None:
            self._flash(f"[{DIM}]— ingen agent valgt —[/]")
            return
        if str(row.get("status", "") or "").lower() != "active":
            self._flash(f"[{AMBER}]— kun aktive agenter kan pauses —[/]")
            return
        aid = str(row.get("agent_id", "") or "")
        if not aid:
            self._flash(f"[{DIM}]— agent mangler id —[/]")
            return
        self._post_action(f"/central/agents/{aid}/pause", {},
                          f"agent pauset: {aid}", "pause fejlede")

    def action_agent_abort(self) -> None:
        """`x` on the Agents tab: DANGEROUS — arm y/n confirm, then cancel."""
        if self.active_tab != "agents":
            return
        row = self._selected_row(self._agent_rows or [])
        if row is None:
            self._flash(f"[{DIM}]— ingen agent valgt —[/]")
            return
        aid = str(row.get("agent_id", "") or "")
        if not aid:
            self._flash(f"[{DIM}]— agent mangler id —[/]")
            return
        payload = {"path": f"/central/agents/{aid}/cancel", "body": {},
                   "label": aid}
        self._pending_write = ("agent_abort", payload)
        self._flash(
            f"[{AMBER} b]⚠ bekræft {self._write_desc('agent_abort', payload)}? "
            f"y/n[/]"
        )

    def action_slot_reset(self) -> None:
        """`r` on the Balancer tab: reset the selected slot."""
        if self.active_tab != "balancer":
            return
        sid = self._selected_slot_id()
        if sid is None:
            return
        self._post_action(f"/mc/cheap-balancer/slot/{sid}/reset", {},
                          f"slot reset: {sid}", "reset fejlede")

    def action_slot_enable(self) -> None:
        """`e` on the Balancer tab: enable the selected slot."""
        if self.active_tab != "balancer":
            return
        sid = self._selected_slot_id()
        if sid is None:
            return
        self._post_action(f"/mc/cheap-balancer/slot/{sid}/enable", {},
                          f"slot aktiveret: {sid}", "aktivér fejlede")

    def action_slot_disable(self) -> None:
        """`d` on the Balancer tab: DANGEROUS — arm y/n confirm, then disable."""
        if self.active_tab != "balancer":
            return
        sid = self._selected_slot_id()
        if sid is None:
            return
        payload = {"path": f"/mc/cheap-balancer/slot/{sid}/disable", "body": {},
                   "label": sid}
        self._pending_write = ("slot_disable", payload)
        self._flash(
            f"[{AMBER} b]⚠ bekræft {self._write_desc('slot_disable', payload)}? "
            f"y/n[/]"
        )

    def _selected_slot_id(self) -> str | None:
        row = self._selected_row(self._balancer_rows or [])
        if row is None:
            self._flash(f"[{DIM}]— ingen slot valgt —[/]")
            return None
        sid = str(row.get("slot_id", "") or "")
        if not sid:
            self._flash(f"[{DIM}]— slot mangler id —[/]")
            return None
        return sid

    def check_action(self, action: str, parameters: tuple) -> bool | None:
        """Gate the single-letter row actions so they never steal a keystroke:
        disabled while the command line has text (letter types normally) and
        outside the tab they belong to. Everything else stays enabled."""
        agent_acts = ("agent_pause", "agent_abort")
        slot_acts = ("slot_reset", "slot_disable", "slot_enable")
        if action in agent_acts or action in slot_acts:
            try:
                if self.query_one("#hud-cmd-input", Input).value:
                    return False
            except Exception:
                pass
            if action in agent_acts and self.active_tab != "agents":
                return False
            if action in slot_acts and self.active_tab != "balancer":
                return False
        return True

    def _flash(self, markup: str) -> None:
        from central_cli.hud import _TABLE_TABS
        try:
            if self.active_tab in _TABLE_TABS:
                self.query_one("#hud-feed", RichLog).write(markup)
            elif self.active_tab == "healing":
                self._render_healing_panel()
        except Exception:
            return
