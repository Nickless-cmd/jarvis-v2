"""Central HUD — read-side rendering (``_PopulateMixin``).

All ``_populate_*`` table fillers and ``_render_*`` detail/panel painters, plus
the small UI helpers they lean on (``_reset_columns``, ``_set_paneh``,
``_set_side_paneh``, ``_sync_header``, ``_sync_tabs``, ``_render_feed``,
``_rel_age``, ``_fmt_value``, healer-flag lookup). Extracted verbatim from
``hud.py`` (behaviour-preserving split); every method resolves on the combined
``CentralHud`` instance, so cross-mixin calls work unchanged.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from rich.text import Text

from textual.widgets import DataTable, RichLog, Static

from central_cli import datasource
from central_cli.hud_theme import (
    _esc,
    CYAN, AMBER, RED, GREEN, BLUE, DIM, FG, FGDIM, SPARK,
    _STATE, _DECISION, _IMPORTANCE, _STATUS, _CLUSTER_STATUS, _SEVERITY,
    _AFFECT, _AGENT_STATUS, _RUN_STATUS,
)


class _PopulateMixin:
    """Read-side of the Central HUD: table population + detail/panel painting."""

    def _sync_header(self) -> None:
        try:
            self.query_one("#hud-head", Static).update(self._render_header())
        except Exception:
            pass

    def _sync_tabs(self) -> None:
        try:
            self.query_one("#hud-tabs", Static).update(self._render_tabs())
        except Exception:
            pass

    def _set_paneh(self, text: str) -> None:
        try:
            self.query_one("#main-paneh", Static).update(Text.from_markup(text))
        except Exception:
            pass

    def _set_side_paneh(self, text: str) -> None:
        try:
            self.query_one("#side-paneh", Static).update(Text.from_markup(text))
        except Exception:
            pass

    def _reset_columns(self, table: DataTable, *cols: tuple[str, int]) -> None:
        table.clear(columns=True)
        for label, width in cols:
            table.add_column(label, width=width)

    # -- Nerves ------------------------------------------------------------
    def _populate_nerves(self) -> None:
        try:
            table = self.query_one("#nerve-table", DataTable)
        except Exception:
            return
        self._reset_columns(table, ("cluster", 15), ("nerve", 22), ("state", 15),
                            ("sidste", 8), ("count", 6), ("aktivitet", 18))
        if self._client is None:
            return
        try:
            rows = datasource.nerves(self._client)
        except Exception:
            return
        self._nerve_rows = rows
        self._set_paneh(
            f"[{CYAN}]NERVES[/] [{FGDIM}]— {len(rows)} i alt · filter: [/]"
            f"[{CYAN}]/[/] [{FGDIM}]· sortér: state[/]"
        )
        for r in rows:
            state = str(r.get("state", ""))
            color, glyph = _STATE.get(state, (FG, state))
            if state == "død" and str(r.get("severity", "")) in ("error", "severe", "critical"):
                glyph = "✖ død · error"
            table.add_row(
                Text(str(r.get("cluster", "")), style=FGDIM),
                Text(str(r.get("nerve", "")), style=FG),
                Text(glyph, style=color),
                Text(self._rel_age(r.get("last", "")), style=FGDIM),
                Text(str(r.get("count", 0)), style=FGDIM, justify="right"),
                Text(str(r.get("spark", "")), style=SPARK),
            )

    def _render_feed(self) -> None:
        try:
            log = self.query_one("#hud-feed", RichLog)
        except Exception:
            return
        if self._client is None:
            return
        try:
            rows = datasource.feed(self._client)
        except Exception:
            return
        log.clear()
        for r in rows:
            decision = str(r.get("decision", ""))
            color = _DECISION.get(decision, DIM)
            count = int(r.get("count", 1) or 1)
            badge = f" [{FGDIM}]×{count} · seneste[/]" if count > 1 else ""
            cluster = _esc(r.get("cluster", ""))
            nerve = _esc(r.get("nerve", ""))
            reason = _esc(r.get("reason", ""))
            sep = f" [{DIM}]—[/] {reason}" if reason else ""
            log.write(
                f"[{color}]●[/] [{color}]{cluster}/{nerve}[/] "
                f"[{DIM}]·[/] {_esc(decision)}{badge}{sep}"
            )

    # -- detail panel (side, full height) ----------------------------------
    def _detail_incident(self) -> dict | None:
        if self.active_tab == "incidents" and self._incidents:
            i = max(0, min(self._sel_incident, len(self._incidents) - 1))
            return self._incidents[i]
        top = (self._overview or {}).get("top_incidents") or []
        return top[0] if top else None

    def _render_detail_panel(self) -> None:
        try:
            panel = self.query_one("#hud-detail", Static)
        except Exception:
            return
        inc = self._detail_incident()
        if not inc:
            self._set_side_paneh(f"[{CYAN}]INCIDENT-DETALJE[/] [{DIM}]— —[/]")
            panel.update(Text.from_markup(
                f"[{GREEN} b]◈ ALT ROLIGT[/]\n\n"
                f"[{FGDIM}]Ingen aktive incidents.[/]\n"
                f"[{FGDIM}]Detaljer vises her når noget kræver opmærksomhed.[/]"
            ))
            return
        try:
            d = datasource.incident_detail(self._client, inc)
        except Exception:
            d = dict(inc)

        sev = str(d.get("severity", "") or "—")
        color = _SEVERITY.get(sev, FG)
        cluster = d.get("cluster", "")
        nerve = d.get("nerve", "")
        self._set_side_paneh(
            f"[{CYAN}]INCIDENT-DETALJE[/] [{DIM}]— {_esc(cluster)}/{_esc(nerve)}[/]"
        )

        def _cap(text: Any, n: int) -> str:
            s = str(text or "").replace("\n", " ")
            return s if len(s) <= n else s[: n - 1] + "…"

        # bordered badge (terminal idiom: bg-tinted pill)
        badge_bg = "#1f0d0d" if color == RED else ("#241a05" if color == AMBER else "#06202e")
        lines = [
            f"[{color} b on {badge_bg}] ● {_esc(sev.upper())} · {_esc(cluster)} [/]",
            "",
            f"[{FG} b]{_esc(d.get('title') or nerve)}[/]",
            f"[{FGDIM}]{_esc(_cap(d.get('message', ''), 130))}[/]",
        ]
        rc = d.get("root_cause")
        if rc:
            lines += ["", f"[{FGDIM} b]ROOT CAUSE[/]", f"[{FG}]{_esc(_cap(rc, 130))}[/]"]
        related = d.get("related") or []
        if related:
            chips = "".join(f"[{FGDIM} on #0f1824] {_esc(r)} [/] " for r in related)
            lines += ["", f"[{FGDIM} b]RELATEREDE NERVER[/]", chips]
        heal = d.get("heal_status")
        if heal:
            lines += ["", f"[{FGDIM} b]HEAL-STATUS[/]", f"[{GREEN}]◈ {_esc(_cap(heal, 130))}[/]"]
        corr = d.get("correlation") or {}
        if corr:
            first = str(corr.get("first", ""))[:10]
            last = str(corr.get("last", ""))[:10]
            lines += [
                "",
                f"[{FGDIM} b]CORRELATION[/]",
                f"[{FGDIM}]#{corr.get('sig', '')} · {corr.get('count', 0)} "
                f"forekomster · {first}→{last}[/]",
            ]
        lines += [
            "",
            f"[{CYAN} on #06202e] ↵ fuld diagnostik [/]  [{AMBER} on #241a05] r resolve [/]",
        ]
        panel.update(Text.from_markup("\n".join(lines)))

    # -- Clusters ----------------------------------------------------------
    def _populate_clusters(self) -> None:
        try:
            table = self.query_one("#nerve-table", DataTable)
        except Exception:
            return
        self._reset_columns(table, ("cluster", 18), ("status", 12), ("nerver", 8),
                            ("aktiv", 7), ("idle", 7), ("degraded", 10), ("død", 6))
        if self._client is None:
            return
        try:
            rows = datasource.clusters(self._client)
        except Exception:
            return
        self._cluster_rows = rows
        self._set_paneh(f"[{CYAN}]CLUSTERS[/] [{FGDIM}]— {len(rows)} i alt[/]")
        for r in rows:
            status = str(r.get("status", ""))
            color = _CLUSTER_STATUS.get(status, FG)
            table.add_row(
                Text(str(r.get("cluster", "")), style=FG),
                Text(f"● {status}", style=color),
                Text(str(r.get("nerves", 0)), style=FGDIM),
                Text(str(r.get("aktiv", 0)), style=GREEN),
                Text(str(r.get("idle", 0)), style=DIM),
                Text(str(r.get("degraded", 0)), style=AMBER),
                Text(str(r.get("død", 0)), style=RED),
            )

    # -- Incidents ---------------------------------------------------------
    def _populate_incidents(self) -> None:
        try:
            table = self.query_one("#nerve-table", DataTable)
        except Exception:
            return
        self._reset_columns(table, ("sev", 9), ("cluster/nerve", 26), ("besked", 40))
        if self._client is None:
            return
        try:
            self._incidents = datasource.incidents(self._client)
        except Exception:
            self._incidents = []
        self._set_paneh(f"[{CYAN}]INCIDENTS[/] [{FGDIM}]— {len(self._incidents)} uløste[/]")
        for inc in self._incidents:
            sev = str(inc.get("severity", ""))
            color = _SEVERITY.get(sev, FG)
            cluster = inc.get("cluster", "")
            nerve = inc.get("nerve", "")
            msg = str(inc.get("message", "") or "").replace("\n", " ")
            preview = msg if len(msg) <= 80 else msg[:79] + "…"
            table.add_row(
                Text(f"● {sev}" if sev else "—", style=color),
                Text(f"{cluster}/{nerve}", style=FG),
                Text(preview, style=FGDIM),
            )

    # -- Connections tab (API-forbindelses-presence) -----------------------
    def _populate_connections(self) -> None:
        """Hvem/hvad er forbundet til API'et: ip · user · endpoint · antal · fejl · aktiv.
        Metadata-only (intet samtaleindhold). GDPR: fuld IP → /24 efter 48t."""
        try:
            table = self.query_one("#nerve-table", DataTable)
        except Exception:
            return
        self._reset_columns(table, ("", 2), ("ip", 20), ("user", 16),
                            ("endpoint", 30), ("req", 6), ("err", 5))
        if self._client is None:
            return
        try:
            data = datasource.connections(self._client)
        except Exception:
            data = {}
        conns = data.get("connections") or []
        active = int(data.get("active_count") or 0)
        errs = int(data.get("error_count") or 0)
        self._set_paneh(
            f"[{CYAN}]CONNECTIONS[/] [{FGDIM}]— {active} aktive · {len(conns)} total · "
            f"{errs} fejl[/]  [{FGDIM}](metadata-only · IP→/24 efter 48t)[/]"
        )
        for c in conns:
            is_active = bool(c.get("active"))
            dot = Text("●", style=GREEN if is_active else FGDIM)
            ip = str(c.get("ip", "") or "?")
            user = str(c.get("user_id", "") or "—")
            if len(user) > 15:
                user = user[:6] + "…" + user[-6:]
            method = str(c.get("last_method", "") or "")
            path = str(c.get("last_path", "") or "")
            endpoint = f"{method} {path}"
            if len(endpoint) > 29:
                endpoint = endpoint[:28] + "…"
            rc = int(c.get("request_count") or 0)
            ec = int(c.get("error_count") or 0)
            table.add_row(
                dot,
                Text(ip, style=FG if is_active else FGDIM),
                Text(user, style=FG),
                Text(endpoint, style=FGDIM),
                Text(str(rc), style=FG),
                Text(str(ec), style=(_SEVERITY.get("error", FG) if ec else FGDIM)),
            )

    # -- Users tab (bruger-aktivitet: sidst aktiv pr. bruger) ---------------
    def _populate_users(self) -> None:
        try:
            table = self.query_one("#nerve-table", DataTable)
        except Exception:
            return
        self._reset_columns(table, ("", 2), ("navn", 12), ("rolle", 8),
                            ("sidst aktiv", 18), ("via", 8), ("besk.", 7), ("est.tok", 9))
        if self._client is None:
            return
        try:
            data = datasource.users(self._client)
        except Exception:
            data = {}
        rows = data.get("users") or []
        self._set_paneh(f"[{CYAN}]USERS[/] [{FGDIM}]— {data.get('active_count',0)} aktive · "
                        f"{data.get('total_users',0)} brugere[/]")
        for u in rows:
            act = bool(u.get("active"))
            la = str(u.get("last_active", "") or "")[:16].replace("T", " ")
            table.add_row(
                Text("●", style=GREEN if act else FGDIM),
                Text(str(u.get("name", "?")), style=FG if act else FGDIM),
                Text(str(u.get("role", "")), style=FGDIM),
                Text(la, style=FG), Text(str(u.get("via", "")), style=FGDIM),
                Text(str(u.get("messages", 0)), style=FG),
                Text(f"{int(u.get('est_tokens',0)):,}", style=FGDIM),
            )

    # -- Excess tab (gartner-sans: Centralens egen vægt) -------------------
    def _populate_excess(self) -> None:
        try:
            table = self.query_one("#nerve-table", DataTable)
        except Exception:
            return
        self._reset_columns(table, ("linjer", 9), ("fil", 52))
        if self._client is None:
            return
        try:
            data = datasource.excess(self._client)
        except Exception:
            data = {}
        pres = int(data.get("pressure", 0))
        pcol = _SEVERITY.get("error", FG) if pres >= 70 else (GREEN if pres < 40 else FG)
        self._set_paneh(
            f"[{CYAN}]EXCESS[/] [{pcol}]pres {pres}/100[/] [{FGDIM}]— "
            f"{data.get('over_hard_count',0)} filer >2000 · {data.get('service_count',0)} services · "
            f"{int(data.get('total_lines',0)):,} linjer[/]\n[{FGDIM}]{data.get('felt','')}[/]"
        )
        for f in data.get("worst_files", []):
            over = f.get("over_hard")
            table.add_row(
                Text(f"{int(f.get('lines',0)):,}", style=_SEVERITY.get("error", FG) if over else FG),
                Text(str(f.get("file", "")), style=FG if over else FGDIM),
            )

    # -- Decentral tab (chokepoint-skat) -----------------------------------
    def _populate_decentral(self) -> None:
        try:
            table = self.query_one("#nerve-table", DataTable)
        except Exception:
            return
        self._reset_columns(table, ("", 2), ("beslutning", 22), ("total", 8), ("handling", 40))
        if self._client is None:
            return
        try:
            data = datasource.decentralization(self._client)
        except Exception:
            data = {}
        tax = data.get("chokepoint_tax_pct", 0.0)
        self._set_paneh(
            f"[{CYAN}]DECENTRAL[/] [{FGDIM}]— chokepoint-skat [/][{FG}]{tax}%[/] [{FGDIM}]"
            f"({data.get('overhead_decisions',0)}/{data.get('total_decisions',0)} overhead)[/]\n"
            f"[{FGDIM}]{data.get('felt','')}[/]"
        )
        for c in data.get("candidates", []):
            table.add_row(
                Text("✂", style=GREEN),
                Text(str(c.get("nerve", "")), style=FG),
                Text(str(c.get("total", 0)), style=FGDIM),
                Text("kandidat: resolve lokalt, eskalér ikke-grøn", style=FGDIM),
            )

    # -- Anomalies tab -----------------------------------------------------
    def _populate_anomalies(self) -> None:
        try:
            table = self.query_one("#nerve-table", DataTable)
        except Exception:
            return
        self._reset_columns(table, ("vigtighed", 11), ("kategori", 16),
                            ("count", 6), ("signatur", 42))
        if self._client is None:
            return
        try:
            self._anomalies = datasource.anomalies(self._client)
        except Exception:
            self._anomalies = []
        self._set_paneh(f"[{CYAN}]ANOMALIES[/] [{FGDIM}]— {len(self._anomalies)} fanget[/]")
        for a in self._anomalies:
            imp = str(a.get("importance", ""))
            color = _IMPORTANCE.get(imp, FG)
            sig = str(a.get("signature", "")).replace("\n", " ")
            preview = sig if len(sig) <= 42 else sig[:41] + "…"
            table.add_row(
                Text(f"● {imp}" if imp else "—", style=color),
                Text(str(a.get("category", "")), style=FGDIM),
                Text(str(a.get("count", 0)), style=FGDIM, justify="right"),
                Text(preview, style=FG),
            )

    def _render_anomaly_detail(self) -> None:
        try:
            panel = self.query_one("#hud-detail", Static)
        except Exception:
            return
        anoms = self._anomalies or []
        if not anoms:
            self._set_side_paneh(f"[{CYAN}]ANOMALI-DETALJE[/] [{DIM}]— —[/]")
            panel.update(Text.from_markup(f"[{GREEN} b]◈ INGEN ANOMALIER[/]"))
            return
        i = max(0, min(self._sel_anomaly, len(anoms) - 1))
        a = anoms[i]
        imp = str(a.get("importance", "") or "—")
        color = _IMPORTANCE.get(imp, FG)
        cat = a.get("category", "")
        badge_bg = "#1f0d0d" if color == RED else ("#241a05" if color == AMBER else "#06202e")

        def _cap(t: Any, n: int) -> str:
            s = str(t or "").replace("\n", " ")
            return s if len(s) <= n else s[: n - 1] + "…"

        first = str(a.get("first", ""))[:16].replace("T", " ")
        last = str(a.get("last", ""))[:16].replace("T", " ")
        self._set_side_paneh(f"[{CYAN}]ANOMALI-DETALJE[/] [{DIM}]— {_esc(cat)}[/]")
        lines = [
            f"[{color} b on {badge_bg}] ● {_esc(imp.upper())} · {_esc(a.get('source', ''))} [/]",
            "",
            f"[{FG} b]{_esc(cat)}[/]  [{FGDIM}]×{a.get('count', 0)}[/]",
            "",
            f"[{FGDIM} b]SIGNATUR[/]",
            f"[{FG}]{_esc(_cap(a.get('signature', ''), 160))}[/]",
            "",
            f"[{FGDIM} b]SAMPLE[/]",
            f"[{FGDIM}]{_esc(_cap(a.get('sample', ''), 200))}[/]",
        ]
        if a.get("location"):
            lines += ["", f"[{FGDIM} b]LOKATION[/]", f"[{FGDIM}]{_esc(_cap(a.get('location'), 90))}[/]"]
        lines += [
            "",
            f"[{FGDIM} b]VINDUE[/]",
            f"[{FGDIM}]{first}  →  {last}[/]",
        ]
        panel.update(Text.from_markup("\n".join(lines)))

    # -- detail dispatch (every table tab shows full detail of selected row) --
    def _render_row_detail(self, row: int) -> None:
        t = self.active_tab
        if t == "incidents":
            self._sel_incident = row
            self._render_detail_panel()
        elif t == "anomalies":
            self._sel_anomaly = row
            self._render_anomaly_detail()
        elif t == "nerves":
            self._render_nerve_detail(row)
        elif t == "clusters":
            self._render_cluster_detail(row)
        elif t == "governance":
            self._render_gov_detail(row)
        elif t == "agents":
            self._render_agent_detail(row)
        elif t == "balancer":
            self._render_balancer_detail(row)
        elif t == "runs":
            self._render_run_detail(row)

    def _render_nerve_detail(self, row: int) -> None:
        try:
            panel = self.query_one("#hud-detail", Static)
        except Exception:
            return
        rows = self._nerve_rows or []
        if not (0 <= row < len(rows)):
            return
        r = rows[row]
        state = str(r.get("state", ""))
        color, glyph = _STATE.get(state, (FG, state))
        cluster = r.get("cluster", "")
        nerve = r.get("nerve", "")
        self._set_side_paneh(f"[{CYAN}]NERVE-DETALJE[/] [{DIM}]— {_esc(cluster)}/{_esc(nerve)}[/]")
        badge_bg = {GREEN: "#06251a", AMBER: "#241a05", RED: "#1f0d0d", DIM: "#0f1824"}.get(color, "#06202e")
        lines = [
            f"[{color} b on {badge_bg}] {_esc(glyph)} [/]",
            "",
            f"[{FG} b]{_esc(nerve)}[/]",
            f"[{FGDIM}]cluster[/]  [{FG}]{_esc(cluster)}[/]",
            "",
            f"[{FGDIM}]sidste fyring[/]  [{FG}]{_esc(self._rel_age(r.get('last', '')))}[/]",
            f"[{FGDIM}]antal (count)[/]  [{FG}]{r.get('count', 0)}[/]",
            "",
            f"[{FGDIM} b]AKTIVITET[/]",
            f"[{SPARK}]{_esc(r.get('spark', '') or '—')}[/]",
        ]
        if r.get("reason"):
            lines += ["", f"[{FGDIM} b]SENESTE[/]", f"[{FGDIM}]{_esc(r.get('reason'))}[/]"]
        lines += ["", f"[{DIM}]↵ vælg · skriv 'toggle {_esc(nerve)} off' for at slå fra[/]"]
        panel.update(Text.from_markup("\n".join(lines)))

    def _render_cluster_detail(self, row: int) -> None:
        try:
            panel = self.query_one("#hud-detail", Static)
        except Exception:
            return
        rows = self._cluster_rows or []
        if not (0 <= row < len(rows)):
            return
        r = rows[row]
        status = str(r.get("status", ""))
        color = _CLUSTER_STATUS.get(status, FG)
        name = r.get("cluster", "")
        self._set_side_paneh(f"[{CYAN}]CLUSTER-DETALJE[/] [{DIM}]— {_esc(name)}[/]")
        badge_bg = {GREEN: "#06251a", AMBER: "#241a05", RED: "#1f0d0d", DIM: "#0f1824"}.get(color, "#06202e")
        lines = [
            f"[{color} b on {badge_bg}] ● {_esc(status.upper())} [/]",
            "",
            f"[{FG} b]{_esc(name)}[/]",
            f"[{FGDIM}]nerver i alt[/]  [{FG} b]{r.get('nerves', 0)}[/]",
            "",
            f"[{GREEN}]● aktiv[/]      [{FG}]{r.get('aktiv', 0)}[/]",
            f"[{DIM}]○ idle[/]       [{FG}]{r.get('idle', 0)}[/]",
            f"[{AMBER}]◆ degraded[/]   [{FG}]{r.get('degraded', 0)}[/]",
            f"[{RED}]✖ død[/]        [{FG}]{r.get('død', 0)}[/]",
            "",
            f"[{CYAN}]↵ filtrér Nerves til denne cluster[/]",
        ]
        panel.update(Text.from_markup("\n".join(lines)))

    def _render_gov_detail(self, row: int) -> None:
        try:
            panel = self.query_one("#hud-detail", Static)
        except Exception:
            return
        flags = self._gov_flags or []
        if not (0 <= row < len(flags)):
            return
        f = flags[row]
        dangerous = bool(f.get("dangerous"))
        value = f.get("value")
        on = bool(value) if isinstance(value, bool) else str(value) not in ("off", "")
        vcolor = GREEN if on else DIM
        label = f.get("label") or f.get("key") or ""
        self._set_side_paneh(f"[{CYAN}]FLAG-DETALJE[/] [{DIM}]— {_esc(f.get('key', ''))}[/]")
        lines = [
            f"[{vcolor} b on #06251a] {_esc(self._fmt_value(value))} [/]"
            if on else f"[{DIM} b on #12161d] {_esc(self._fmt_value(value))} [/]",
            "",
            f"[{FG} b]{_esc(label)}[/]",
            f"[{FGDIM}]nøgle[/]  [{FG}]{_esc(f.get('key', ''))}[/]",
            f"[{FGDIM}]type[/]   [{FG}]{_esc(f.get('kind', 'bool'))}[/]",
        ]
        opts = f.get("options")
        if opts:
            lines.append(f"[{FGDIM}]valg[/]   [{FG}]{_esc(', '.join(map(str, opts)))}[/]")
        if dangerous:
            lines += ["", f"[{AMBER}]⚠ farligt flag — kræver bekræftelse (y) ved ændring[/]"]
        else:
            lines += ["", f"[{DIM}]— ufarligt —[/]"]
        lines += ["", f"[{CYAN} on #06202e] ↵ skift værdi [/]"]
        panel.update(Text.from_markup("\n".join(lines)))

    # -- Overview ----------------------------------------------------------
    def _render_overview_panel(self) -> None:
        try:
            panel = self.query_one("#hud-panel", Static)
        except Exception:
            return
        ov = self._overview or {}
        status = str(ov.get("status", "unknown")).lower()
        s_color, s_label = _STATUS.get(status, (DIM, status.upper() or "UKENDT"))
        nerves = ov.get("nerves", 0)
        clusters = ov.get("clusters", 0)
        incidents = ov.get("incidents", 0)
        breakers = ov.get("breakers", 0)
        inc_color = RED if incidents else FG
        brk_color = RED if breakers else FG
        lines = [
            f"[{CYAN} b]◈ OVERVIEW[/]",
            "",
            f"[{FGDIM}]status[/]   [{s_color} b]● {s_label}[/]",
            "",
            f"[{FGDIM}]nerver[/] [{FG} b]{nerves}[/]    "
            f"[{FGDIM}]clusters[/] [{FG} b]{clusters}[/]    "
            f"[{FGDIM}]incidents[/] [{inc_color} b]{incidents}[/]    "
            f"[{FGDIM}]breakers[/] [{brk_color} b]{breakers}[/]",
        ]
        # -- affekt (rådets #4): hvordan nervesystemet føles lige nu ----------
        af = self._affect or {}
        dominant = str(af.get("dominant", "ro") or "ro")
        a_color, a_glyph = _AFFECT.get(dominant, (FG, "●"))
        lines.append(
            f"[{FGDIM}]affekt[/]  [{a_color} b]{a_glyph} {dominant}[/]  "
            f"[{FGDIM}]uro[/] [{FG}]{af.get('uro', 0)}[/] "
            f"[{FGDIM}]tryk[/] [{FG}]{af.get('tryk', 0)}[/] "
            f"[{FGDIM}]varme[/] [{FG}]{af.get('varme', 0)}[/] "
            f"[{FGDIM}]ro[/] [{FG}]{af.get('ro', 0)}[/]"
        )
        # -- tone (rådets #5): den sproglige STIL Centralen taler i lige nu ----
        tn = self._tone or {}
        register = str(tn.get("register", "") or "")
        if register:
            descriptors = tn.get("descriptors") or []
            desc = " · ".join(str(d) for d in descriptors[:3])
            lines.append(
                f"[{FGDIM}]tone[/]    [{CYAN} b]◈ {register}[/]"
                + (f"  [{FGDIM}]{_esc(desc)}[/]" if desc else "")
            )
        lines.append("")
        lines.append(f"[{CYAN}]top incidents[/]")
        top = ov.get("top_incidents") or []
        if not top:
            lines.append(f"[{DIM}]— ingen aktive incidents —[/]")
        for inc in top[:8]:
            sev = str(inc.get("severity", "") or "—")
            color = _SEVERITY.get(sev, FG)
            cluster = inc.get("cluster", "")
            nerve = inc.get("nerve", "")
            msg = str(inc.get("message", "") or "").replace("\n", " ")
            if len(msg) > 90:
                msg = msg[:89] + "…"
            lines.append(f"  [{color}]● {_esc(sev)}[/] [{FGDIM}]{_esc(cluster)}/{_esc(nerve)}[/] — {_esc(msg)}")

        # -- cost sidste 7 dage (self-safe; skjules ved tom data) ----------
        try:
            cd = self._costs_daily or {}
            raw_days = cd.get("days") or []
            per_day: dict[str, float] = {}
            day_order: list[str] = []
            for row in raw_days:
                if not isinstance(row, dict):
                    continue
                day = row.get("day")
                if not isinstance(day, str):
                    continue
                try:
                    c = float(row.get("total_cost") or 0.0)
                except Exception:
                    c = 0.0
                if day not in per_day:
                    per_day[day] = 0.0
                    day_order.append(day)
                per_day[day] += c
            if day_order:
                lines.append("")
                lines.append(f"[{CYAN}]cost sidste 7 dage[/]")
                for day in day_order[:7]:
                    lines.append(
                        f"  [{FGDIM}]{_esc(day)}[/]  [{FG}]${per_day[day]:.2f}[/]"
                    )
        except Exception:
            pass

        panel.update(Text.from_markup("\n".join(lines)))

    # -- Diagnostics -------------------------------------------------------
    def _render_diagnostics_panel(self) -> None:
        try:
            panel = self.query_one("#hud-panel", Static)
        except Exception:
            return
        try:
            diag = datasource.diagnostics(self._client) if self._client else {}
        except Exception:
            diag = {}

        def _count(v: Any) -> int:
            try:
                return len(v)
            except Exception:
                return int(v or 0)

        inc = _count(diag.get("incidents") or [])
        anom = _count(diag.get("anomalies") or [])
        degr = _count(diag.get("degrading") or [])
        root_causes = diag.get("root_causes") or []
        lines = [
            f"[{CYAN} b]◈ DIAGNOSTICS[/]",
            "",
            f"[{FGDIM}]incidents[/] [{(RED if inc else FG)} b]{inc}[/]    "
            f"[{FGDIM}]anomalier[/] [{(AMBER if anom else FG)} b]{anom}[/]    "
            f"[{FGDIM}]degraderer[/] [{(AMBER if degr else FG)} b]{degr}[/]",
            "",
            f"[{CYAN}]rod-årsager[/]",
        ]
        if not root_causes:
            lines.append(f"[{DIM}]— ingen identificerede rod-årsager —[/]")
        for rc in root_causes[:12]:
            if isinstance(rc, dict):
                text = rc.get("signature") or rc.get("cause") or rc.get("message") or str(rc)
                cnt = rc.get("count")
                suffix = f"  [{FGDIM}]×{cnt}[/]" if cnt else ""
            else:
                text, suffix = str(rc), ""
            if len(text) > 84:
                text = text[:83] + "…"
            lines.append(f"  [{AMBER}]▸[/] [{FG}]{_esc(text)}[/]{suffix}")

        # -- seneste hændelser (A7) — rå eventbus-feed --
        try:
            evs = datasource.events(self._client, limit=12) if self._client else []
        except Exception:
            evs = []
        self._events = evs or []
        lines += [
            "",
            f"[{CYAN} b]◈ SENESTE HÆNDELSER[/]  [{FGDIM}]— eventbus ({len(evs)})[/]",
        ]
        if not evs:
            lines.append(f"  [{DIM}]— ingen hændelser —[/]")
        for ev in evs[:12]:
            fam = str(ev.get("family") or "?")
            kind = str(ev.get("kind") or "")
            lines.append(f"  [{DIM}]▸[/] [{FGDIM}]{_esc(fam)}[/] [{FG}]{_esc(kind)}[/]")
        panel.update(Text.from_markup("\n".join(lines)))

    # -- Governance --------------------------------------------------------
    def _populate_governance(self) -> None:
        try:
            table = self.query_one("#nerve-table", DataTable)
        except Exception:
            return
        self._reset_columns(table, ("flag", 30), ("værdi", 10), ("farlig", 12))
        if self._client is None:
            return
        try:
            self._gov_flags = datasource.governance(self._client) or []
        except Exception:
            self._gov_flags = []
        self._set_paneh(f"[{CYAN}]GOVERNANCE[/] [{FGDIM}]— {len(self._gov_flags)} flag · [/]"
                        f"[{CYAN}]t[/] [{FGDIM}]toggler[/]")
        for f in self._gov_flags:
            dangerous = bool(f.get("dangerous"))
            label = str(f.get("label") or f.get("key") or "")
            value = f.get("value")
            on = bool(value) if isinstance(value, bool) else str(value) not in ("off", "")
            val_text = Text(self._fmt_value(value), style=(GREEN if on else DIM))
            danger_cell = (Text("⚠ farlig", style=AMBER) if dangerous
                           else Text("—", style=DIM))
            table.add_row(Text(label, style=FG), val_text, danger_cell)

    # -- Runs (recent visible runs, drill-in detail) -----------------------
    def _populate_runs(self) -> None:
        try:
            table = self.query_one("#nerve-table", DataTable)
        except Exception:
            return
        self._reset_columns(
            table, ("run", 20), ("lane", 12), ("status", 12), ("model", 20)
        )
        if self._client is None:
            return
        try:
            self._run_rows = datasource.runs(self._client, limit=20)
        except Exception:
            self._run_rows = []
        try:
            self._scheduled = datasource.scheduled(self._client)
        except Exception:
            self._scheduled = []
        n_sched = len(self._scheduled)
        self._set_paneh(
            f"[{CYAN}]RUNS[/] [{FGDIM}]— {len(self._run_rows)} seneste · "
            f"{n_sched} planlagte[/]"
        )
        if not self._run_rows:
            table.add_row(
                Text("— ingen runs —", style=DIM), Text(""), Text(""), Text("")
            )
            return
        for r in self._run_rows:
            status = str(r.get("status", "") or "—")
            color = _RUN_STATUS.get(status, FG)
            rid = str(r.get("run_id", "") or "")[:18]
            table.add_row(
                Text(_esc(rid), style=FG),
                Text(_esc(str(r.get("lane", "") or "")), style=FGDIM),
                Text(f"● {_esc(status)}", style=color),
                Text(_esc(str(r.get("model", "") or "")), style=FGDIM),
            )

    def _render_run_detail(self, row: int) -> None:
        try:
            panel = self.query_one("#hud-detail", Static)
        except Exception:
            return
        rows = self._run_rows or []
        if not (0 <= row < len(rows)):
            self._set_side_paneh(f"[{CYAN}]RUN-DETALJE[/] [{DIM}]— —[/]")
            panel.update(Text.from_markup(f"[{GREEN} b]◈ INGEN RUNS[/]"))
            return
        r = rows[row]
        status = str(r.get("status", "") or "—")
        color = _RUN_STATUS.get(status, FG)
        run_id = r.get("run_id", "") or ""
        badge_bg = {GREEN: "#06251a", AMBER: "#25200a", BLUE: "#06202e",
                    RED: "#1f0d0d"}.get(color, "#06202e")
        self._set_side_paneh(f"[{CYAN}]RUN-DETALJE[/] [{DIM}]— {_esc(str(run_id)[:18])}[/]")
        provider = r.get("provider", "") or ""
        model = r.get("model", "") or ""
        lane = r.get("lane", "") or ""
        started = r.get("started_at", "") or ""
        finished = r.get("finished_at", "") or ""
        lines = [
            f"[{color} b on {badge_bg}] ● {_esc(status.upper())} [/]",
            "",
            f"[{FG} b]{_esc(run_id)}[/]",
            f"[{FGDIM}]lane[/]     [{FG}]{_esc(lane)}[/]",
            f"[{FGDIM}]provider[/] [{FG}]{_esc(provider)}[/]",
            f"[{FGDIM}]model[/]    [{FG}]{_esc(model)}[/]",
            f"[{FGDIM}]start[/]    [{FG}]{_esc(started)}[/]",
            f"[{FGDIM}]slut[/]     [{FG}]{_esc(finished)}[/]",
        ]
        preview = str(r.get("text_preview", "") or "")
        if preview:
            if len(preview) > 200:
                preview = preview[:199] + "…"
            lines += ["", f"[{FGDIM} b]PREVIEW[/]", f"[{FG}]{_esc(preview)}[/]"]
        error = str(r.get("error", "") or "")
        if error:
            if len(error) > 200:
                error = error[:199] + "…"
            lines += ["", f"[{RED} b]FEJL[/]", f"[{RED}]{_esc(error)}[/]"]
        panel.update(Text.from_markup("\n".join(lines)))

    # -- Approvals (autonomy proposals) ------------------------------------
    def _populate_approvals(self) -> None:
        try:
            table = self.query_one("#nerve-table", DataTable)
        except Exception:
            return
        self._reset_columns(table, ("forslag", 40), ("art", 18), ("status", 12))
        try:
            self._autonomy = (datasource.autonomy(self._client) if self._client
                              else {"proposals": [], "pending_count": 0})
        except Exception:
            self._autonomy = {"proposals": [], "pending_count": 0}
        proposals = self._autonomy.get("proposals") or []
        pending = self._autonomy.get("pending_count") or 0
        pend_color = AMBER if pending > 0 else FGDIM
        self._set_paneh(
            f"[{CYAN}]AUTONOMI[/] [{FGDIM}]— [/]"
            f"[{pend_color}]{pending} afventer[/]"
            f"  [{FGDIM}]· ↵ på et forslag → godkend/afvis[/]"
        )
        if not proposals:
            table.add_row(
                Text("— ingen afventende forslag —", style=DIM), Text(""), Text("")
            )
            return
        for p in proposals:
            title = (p.get("title") or p.get("summary") or p.get("description")
                     or p.get("kind") or "—")
            kind = p.get("kind") or p.get("type") or "—"
            status = p.get("status") or "pending"
            table.add_row(
                Text(_esc(str(title)), style=FG),
                Text(_esc(str(kind)), style=FGDIM),
                Text(_esc(str(status)), style=FGDIM),
            )

    # -- Agents ------------------------------------------------------------
    def _populate_agents(self) -> None:
        try:
            table = self.query_one("#nerve-table", DataTable)
        except Exception:
            return
        self._reset_columns(table, ("model", 26), ("rolle", 12),
                            ("status", 12), ("aktivitet", 22), ("last run", 9),
                            ("tokens", 12), ("$", 9), ("tools", 6))
        if self._client is None:
            return
        try:
            rows = datasource.agents(self._client)
        except Exception:
            rows = []
        self._agent_rows = rows
        try:
            self._council = datasource.council(self._client)
        except Exception:
            self._council = []
        n_active = sum(1 for r in rows if str(r.get("status", "")) == "active")
        n_idle = sum(1 for r in rows if str(r.get("status", "")) == "idle")
        n_inact = sum(1 for r in rows if str(r.get("status", "")) == "inactive")
        self._set_paneh(
            f"[{CYAN}]AGENTS[/] [{FGDIM}]— {len(rows)} modeller · "
            f"{n_active} aktive · {n_idle} idle · {n_inact} inaktive · "
            f"{len(self._council)} råds-sessioner[/]"
        )
        if not rows:
            table.add_row(
                Text("— ingen modeller —", style=DIM),
                Text(""), Text(""), Text(""), Text(""),
                Text(""), Text(""), Text(""),
            )
            return
        for r in rows:
            status = str(r.get("status", "") or "")
            inactive = status == "inactive"
            # Whole INACTIVE row is greyed out; active/idle rows keep FG body.
            body = DIM if inactive else FG
            dim = DIM if inactive else FGDIM
            scolor = DIM if inactive else _AGENT_STATUS.get(status, FG)
            prov = str(r.get("provider", "") or "")
            model = str(r.get("model", "") or "")
            mk = str(r.get("model_key", "") or r.get("agent_id", "") or "")
            label = f"{prov}/{model}" if (prov and model) else (model or mk or "—")
            marker = "● " if status == "active" else ""
            status_cell = f"{marker}{status}" if status else "—"
            ti = int(r.get("tokens_in", 0) or 0)
            to = int(r.get("tokens_out", 0) or 0)
            cost = float(r.get("cost_usd", 0.0) or 0.0)
            activity = str(r.get("activity", "") or "") or "—"
            table.add_row(
                Text(_esc(label), style=body),
                Text(_esc(str(r.get("role", "") or "")), style=dim),
                Text(_esc(status_cell), style=scolor),
                Text(_esc(activity), style=dim),
                Text(self._rel_age(r.get("last_run", "")), style=dim),
                Text(f"{ti}/{to}", style=dim, justify="right"),
                Text(f"${cost:.4f}", style=dim, justify="right"),
                Text(str(int(r.get("tool_calls", 0) or 0)), style=dim,
                     justify="right"),
            )

    def _render_agent_detail(self, row: int) -> None:
        try:
            panel = self.query_one("#hud-detail", Static)
        except Exception:
            return
        rows = self._agent_rows or []
        if not (0 <= row < len(rows)):
            self._set_side_paneh(f"[{CYAN}]AGENT-DETALJE[/] [{DIM}]— —[/]")
            panel.update(Text.from_markup(f"[{GREEN} b]◈ INGEN AGENTER[/]"))
            return
        r = rows[row]
        status = str(r.get("status", "") or "—")
        color = _AGENT_STATUS.get(status, FG)
        model_key = str(r.get("model_key", "") or r.get("agent_id", "") or "")
        role = r.get("role", "")
        ti = int(r.get("tokens_in", 0) or 0)
        to = int(r.get("tokens_out", 0) or 0)
        burned = int(r.get("tokens_burned", ti + to) or 0)
        cost = float(r.get("cost_usd", 0.0) or 0.0)
        badge_bg = {GREEN: "#06251a", DIM: "#0f1824", BLUE: "#06202e",
                    RED: "#1f0d0d"}.get(color, "#06202e")
        self._set_side_paneh(f"[{CYAN}]AGENT-DETALJE[/] [{DIM}]— {_esc(model_key)}[/]")
        lines = [
            f"[{color} b on {badge_bg}] ● {_esc(status.upper())} [/]",
            "",
            f"[{FG} b]{_esc(model_key)}[/]",
            f"[{FGDIM}]rolle[/]      [{FG}]{_esc(role)}[/]",
            f"[{FGDIM}]aktivitet[/]  [{FG}]{_esc(str(r.get('activity', '') or '—'))}[/]",
            f"[{FGDIM}]last run[/]   [{FG}]{_esc(self._rel_age(r.get('last_run', '')))}[/]",
            f"[{FGDIM}]tokens[/]     [{FG}]{ti}/{to} ({burned})[/]",
            f"[{FGDIM}]cost[/]       [{FG}]${cost:.4f}[/]",
            f"[{FGDIM}]tools[/]      [{FG}]{_esc(int(r.get('tool_calls', 0) or 0))}[/]",
        ]
        # any remaining fields on the raw agent/roster dict (never fabricated)
        raw = r.get("raw") or {}
        _known = ("agent_id", "model_key", "provider", "model", "role", "status",
                  "last_run_at", "last_run", "tokens_in", "tokens_out",
                  "tokens_burned", "cost_usd", "current_activity", "activity",
                  "tool_calls")
        extra = [k for k in raw if k not in _known]
        if extra:
            lines += ["", f"[{FGDIM} b]FELTER[/]"]
            for k in extra:
                v = str(raw.get(k))
                if len(v) > 60:
                    v = v[:59] + "…"
                lines.append(f"[{FGDIM}]{_esc(k)}[/]  [{FG}]{_esc(v)}[/]")
        panel.update(Text.from_markup("\n".join(lines)))

    # -- Balancer (cheap-lane / load-balancer pool) ------------------------
    # local status→color map (healthy=green, cooldown/recovering=amber,
    # breaker=red, stale/disabled=grey) — kept local so the balancer view owns
    # its severity. "recovering" = breaker tripped but cooldown expired (half-
    # open, eligible again) → amber, NOT red: it is not a live outage.
    _BAL_STATUS = {
        "healthy": GREEN, "ok": GREEN, "active": GREEN, "live": GREEN,
        "cooldown": AMBER, "throttled": AMBER, "degraded": AMBER, "warn": AMBER,
        "recovering": AMBER,
        "breaker": RED, "open": RED, "error": RED, "failed": RED, "down": RED,
        "stale": DIM, "disabled": DIM, "idle": DIM, "off": DIM,
    }
    # egress lane→color (home=green, vpn=blue, he6=amber tunnel)
    _BAL_EGRESS = {"home": GREEN, "vpn": BLUE, "he6": AMBER}

    def _populate_balancer(self) -> None:
        try:
            table = self.query_one("#nerve-table", DataTable)
        except Exception:
            return
        self._reset_columns(table, ("provider", 14), ("model", 22),
                            ("profil", 10), ("egress", 8), ("status", 11),
                            ("weight", 7), ("headroom", 9), ("rpm", 8),
                            ("last run", 9), ("succ%", 6))
        if self._client is None:
            return
        try:
            result = datasource.balancer(self._client)
        except Exception:
            result = {"header": {}, "rows": []}
        header = result.get("header") or {}
        rows = result.get("rows") or []
        self._balancer_rows = rows
        total = int(header.get("total_slots", len(rows)) or 0)
        healthy = int(header.get("healthy", 0) or 0)
        cooldown = int(header.get("cooldown", 0) or 0)
        breaker = int(header.get("breaker", 0) or 0)
        recovering = int(header.get("recovering", 0) or 0)
        stale = int(header.get("stale", 0) or 0)
        disabled = int(header.get("disabled", 0) or 0)
        profiles = "/".join(str(k) for k in (header.get("by_profile") or {})) or "—"
        egresses = "/".join(str(k) for k in (header.get("by_egress") or {})) or "—"
        self._set_paneh(
            f"[{CYAN}]BALANCER[/] [{FGDIM}]— {total} slots · [/]"
            f"[{GREEN}]{healthy} healthy[/] [{FGDIM}]· [/]"
            f"[{AMBER}]{cooldown} cooldown[/] [{FGDIM}]· "
            f"{recovering} recovering · {breaker} breaker · {stale} stale · "
            f"{disabled} disabled · "
            f"profil {_esc(profiles)} · egress {_esc(egresses)}[/]"
        )
        if not rows:
            table.add_row(
                Text("— ingen slots —", style=DIM),
                Text(""), Text(""), Text(""), Text(""),
                Text(""), Text(""), Text(""), Text(""), Text(""),
            )
            return
        for r in rows:
            status = str(r.get("status", "") or "")
            is_stale = bool(r.get("stale"))
            grey = is_stale or status.lower() in ("stale", "disabled", "idle", "off")
            body = DIM if grey else FG
            dim = DIM if grey else FGDIM
            scolor = DIM if grey else self._BAL_STATUS.get(status.lower(), AMBER)
            egr = str(r.get("egress", "") or "")
            ecolor = DIM if grey else self._BAL_EGRESS.get(egr.lower(), FGDIM)
            marker = "● " if status.lower() in ("healthy", "ok", "active", "live") else ""
            status_cell = f"{marker}{status}" if status else "—"
            weight = float(r.get("weight", 0.0) or 0.0)
            headroom = float(r.get("daily_headroom", 0.0) or 0.0)
            hr_cell = (f"{headroom:.0%}" if 0.0 <= headroom <= 1.0
                       else f"{headroom:g}")
            rpm = f"{int(r.get('rpm_used', 0) or 0)}/{int(r.get('rpm_limit', 0) or 0)}"
            sr = float(r.get("success_rate", 0.0) or 0.0)
            sr_cell = f"{sr * 100:.0f}%" if sr <= 1.0 else f"{sr:.0f}%"
            table.add_row(
                Text(_esc(str(r.get("provider", "") or "—")), style=body),
                Text(_esc(str(r.get("model", "") or "—")), style=body),
                Text(_esc(str(r.get("auth_profile", "") or "—")), style=dim),
                Text(_esc(egr or "—"), style=ecolor),
                Text(_esc(status_cell), style=scolor),
                Text(f"{weight:.2f}", style=dim, justify="right"),
                Text(hr_cell, style=dim, justify="right"),
                Text(rpm, style=dim, justify="right"),
                Text(self._rel_age(r.get("last_success_at", "")), style=dim),
                Text(sr_cell, style=dim, justify="right"),
            )

    def _render_balancer_detail(self, row: int) -> None:
        try:
            panel = self.query_one("#hud-detail", Static)
        except Exception:
            return
        rows = self._balancer_rows or []
        if not (0 <= row < len(rows)):
            self._set_side_paneh(f"[{CYAN}]SLOT-DETALJE[/] [{DIM}]— —[/]")
            panel.update(Text.from_markup(f"[{GREEN} b]◈ INGEN SLOTS[/]"))
            return
        r = rows[row]
        raw = r.get("raw") or {}
        status = str(r.get("status", "") or "—")
        is_stale = bool(r.get("stale"))
        color = (DIM if is_stale
                 else self._BAL_STATUS.get(status.lower(), AMBER))
        slot_id = str(r.get("slot_id", "") or "—")
        badge_bg = {GREEN: "#06251a", DIM: "#0f1824", BLUE: "#06202e",
                    AMBER: "#2a1f05", RED: "#1f0d0d"}.get(color, "#06202e")
        weight = float(r.get("weight", 0.0) or 0.0)
        headroom = float(r.get("daily_headroom", 0.0) or 0.0)
        sr = float(r.get("success_rate", 0.0) or 0.0)
        sr_txt = f"{sr * 100:.0f}%" if sr <= 1.0 else f"{sr:.0f}%"
        self._set_side_paneh(f"[{CYAN}]SLOT-DETALJE[/] [{DIM}]— {_esc(slot_id)}[/]")
        lines = [
            f"[{color} b on {badge_bg}] ● {_esc(status.upper())} [/]",
            "",
            f"[{FG} b]{_esc(str(r.get('provider', '') or '—'))}/"
            f"{_esc(str(r.get('model', '') or '—'))}[/]",
            f"[{FGDIM}]slot_id[/]    [{FG}]{_esc(slot_id)}[/]",
            f"[{FGDIM}]profil[/]     [{FG}]{_esc(str(r.get('auth_profile', '') or '—'))}[/]",
            f"[{FGDIM}]egress[/]     [{FG}]{_esc(str(r.get('egress', '') or '—'))}[/]",
            f"[{FGDIM}]weight[/]     [{FG}]{weight:.3f}[/]",
            f"[{FGDIM}]headroom[/]   [{FG}]{headroom:g}[/]",
            f"[{FGDIM}]daily[/]      [{FG}]{int(r.get('daily_used', 0) or 0)}"
            f"/{int(r.get('daily_limit', 0) or 0)}[/]",
            f"[{FGDIM}]rpm[/]        [{FG}]{int(r.get('rpm_used', 0) or 0)}"
            f"/{int(r.get('rpm_limit', 0) or 0)}[/]",
            f"[{FGDIM}]last run[/]   [{FG}]{_esc(self._rel_age(r.get('last_success_at', '')))}[/]",
            f"[{FGDIM}]success[/]    [{FG}]{sr_txt}[/]",
            f"[{FGDIM}]observed[/]   [{FG}]{bool(r.get('daily_observed'))}[/]",
            f"[{FGDIM}]stale[/]      [{FG}]{is_stale}[/]",
        ]
        # breaker / cooldown_until surfaced from the raw slot when present.
        if "breaker" in raw:
            lines.append(f"[{FGDIM}]breaker[/]    [{FG}]{_esc(str(raw.get('breaker')))}[/]")
        if raw.get("cooldown_until"):
            lines.append(
                f"[{FGDIM}]cooldown[/]   [{FG}]{_esc(str(raw.get('cooldown_until')))}[/]")
        # any remaining raw fields (never fabricated)
        _known = ("slot_id", "provider", "model", "auth_profile", "egress",
                  "status", "weight", "daily_headroom", "daily_used",
                  "daily_limit", "rpm_used", "rpm_limit", "last_success_at",
                  "success_rate", "daily_observed", "stale", "breaker",
                  "cooldown_until")
        extra = [k for k in raw if k not in _known]
        if extra:
            lines += ["", f"[{FGDIM} b]FELTER[/]"]
            for k in extra:
                v = str(raw.get(k))
                if len(v) > 60:
                    v = v[:59] + "…"
                lines.append(f"[{FGDIM}]{_esc(k)}[/]  [{FG}]{_esc(v)}[/]")
        panel.update(Text.from_markup("\n".join(lines)))

    # -- Mind & Self -------------------------------------------------------
    def _render_mind_self_panel(self) -> None:
        """Render Jarvis' reduced self as HIS presence in the Central — warm,
        never raw content: living_executive / self_model / world_model."""
        try:
            panel = self.query_one("#hud-panel", Static)
        except Exception:
            return
        try:
            slf = datasource.self_snapshot(self._client) if self._client else {}
        except Exception:
            slf = {}

        def _dot(surface: dict) -> str:
            return (f"[{GREEN}]●[/]" if bool((surface or {}).get("liveness"))
                    else f"[{DIM}]○[/]")

        lines = [
            f"[{CYAN} b]◈ MIND & SELF[/]  [{FGDIM}]— hans selv i Centralen[/]",
        ]
        if not slf:
            lines += ["", f"[{FGDIM}]— selvet er stille lige nu —[/]"]
        else:
            le = slf.get("living_executive") or {}
            le_sum = le.get("summary") or {}
            lines += [
                "",
                f"{_dot(le)} [{GREEN} b]◈ living_executive[/]",
                f"[{FGDIM}]mode[/]         [{FG}]{_esc(le.get('mode', '—'))}[/]",
                f"[{FGDIM}]trace_count[/]  [{FG}]{_esc(le_sum.get('trace_count', 0))}[/]"
                f"   [{FGDIM}]recent[/] [{FG}]{_esc(le_sum.get('recent_count', 0))}[/]",
                f"[{FGDIM}]last_choice[/]  [{FG}]{_esc(le_sum.get('last_choice', '—'))}[/]",
                f"[{FGDIM}]last_action[/]  [{FG}]{_esc(le_sum.get('last_action', '—'))}[/]",
            ]

            sm = slf.get("self_model") or {}
            sm_sum = sm.get("summary") or {}
            sections = sm_sum.get("sections") or []
            if isinstance(sections, list):
                sec_text = ", ".join(str(s) for s in sections)
            else:
                sec_text = str(sections)
            lines += [
                "",
                f"{_dot(sm)} [{GREEN} b]◈ self_model[/]",
                f"[{FGDIM}]layer_count[/]  [{FG}]{_esc(sm_sum.get('layer_count', 0))}[/]",
                f"[{FGDIM}]sections[/]     [{FG}]{_esc(sec_text or '—')}[/]",
            ]

            wm = slf.get("world_model") or {}
            wm_sum = wm.get("summary") or {}
            lines += [
                "",
                f"{_dot(wm)} [{GREEN} b]◈ world_model[/]",
                f"[{FGDIM}]active_count[/]  [{FG}]{_esc(wm_sum.get('active_count', 0))}[/]",
            ]

            # -- Fase C: AGENTUR — de private lag hvor emergent agentur bor.
            # Kun light (liveness + tællere); aldrig råt indhold. Self-safe:
            # manglende surface → springes over. Viser de vigtigste summary-
            # tællere pr. surface (op til 3 for at holde panelet roligt).
            agentur = (
                ("open_loops", slf.get("open_loops") or {}),
                ("runtime_awareness", slf.get("runtime_awareness") or {}),
                ("runtime_self_knowledge", slf.get("runtime_self_knowledge") or {}),
                ("counterfactual", slf.get("counterfactual") or {}),
            )
            if any(bool(s) for _, s in agentur):
                lines += ["", f"[{CYAN} b]◈ AGENTUR[/]  [{FGDIM}]— hvor agentur bor[/]"]
                for a_name, a_surf in agentur:
                    if not a_surf:
                        continue
                    dot = (f"[{GREEN}]●[/]" if a_surf.get("liveness")
                           else f"[{DIM}]○[/]")
                    lines.append(f"  {dot} [{FGDIM}]{_esc(a_name)}[/]")
                    a_sum = a_surf.get("summary") or {}
                    if isinstance(a_sum, dict):
                        shown = 0
                        for sk, sv in a_sum.items():
                            if shown >= 3:
                                break
                            if isinstance(sv, (str, int, float, bool)):
                                lines.append(
                                    f"      [{FGDIM}]{_esc(sk)}[/] "
                                    f"[{FG}]{_esc(sv)}[/]"
                                )
                                shown += 1

        # -- initiativ-stige (rådets #3) — hans initiativ observe→propose→
        # execute→learn med en gate før hvert løft. Kun skalarer/labels (§24.4).
        try:
            ini = datasource.initiative(self._client) if self._client else {}
        except Exception:
            ini = {}
        ini = ini or {}
        _stage = str(ini.get("stage") or "observe")
        _gate_open = bool(ini.get("gate_open"))
        _gate_reason = str(ini.get("gate_reason") or "")
        _top = str(ini.get("top_initiative") or "—")
        _icounts = ini.get("counts") or {}
        _stage_labels = {
            "observe": "OBSERVE",
            "propose": "PROPOSE",
            "execute": "EXECUTE",
            "learn": "LEARN",
        }
        _stage_txt = _stage_labels.get(_stage, _stage.upper())
        _gate_txt = (f"[{GREEN}]åben[/]" if _gate_open
                     else f"[{AMBER}]lukket[/]")
        lines += [
            "",
            f"[{CYAN} b]◈ INITIATIV[/]  [{FGDIM}]— trin: [/][{FG} b]{_stage_txt}[/]"
            f"  [{FGDIM}]· gate: [/]{_gate_txt}",
            f"  [{FGDIM}]{_esc(_gate_reason)}[/]",
            f"  [{FGDIM}]top[/] [{FG}]{_esc(_top)}[/]   "
            f"[{FGDIM}]obs[/] [{FG}]{_esc(_icounts.get('observe', 0))}[/] "
            f"[{FGDIM}]pro[/] [{FG}]{_esc(_icounts.get('propose', 0))}[/] "
            f"[{FGDIM}]exe[/] [{FG}]{_esc(_icounts.get('execute', 0))}[/] "
            f"[{FGDIM}]lrn[/] [{FG}]{_esc(_icounts.get('learn', 0))}[/]",
        ]

        # -- sjæl — mørke sjæle-/tids-signaler nu i nervesystemet (efter AGENTUR).
        # Reduceret: kun liveness+count pr. signal (aldrig rå tekst). Self-safe.
        try:
            soul = datasource.soul(self._client) if self._client else {}
        except Exception:
            soul = {}
        soul = soul or {}
        soul_live = int(soul.get("live_count") or 0)
        soul_total = int(soul.get("total") or 0)
        lines += [
            "",
            f"[{CYAN} b]◈ SJÆL — mørke signaler nu i nervesystemet[/]"
            f"  [{FGDIM}]{soul_live}/{soul_total}[/]",
        ]
        soul_sections = soul.get("signals") or {}
        if not soul_sections:
            lines.append(f"  [{DIM}]— stille —[/]")
        else:
            for name, sec in sorted(soul_sections.items()):
                sec = sec or {}
                dot = (f"[{GREEN}]●[/]" if sec.get("liveness") else f"[{DIM}]○[/]")
                cnt = int(sec.get("count") or 0)
                lines.append(f"  {dot} [{FGDIM}]{_esc(name)}[/] [{FG}]{cnt}[/]")

        # -- mørke produkter — daemon-PRODUKTER (ikke bare egress) nu i nerve-
        # systemet, hver i sin naturlige cluster. Reduceret: liveness+count.
        try:
            dark = datasource.dark_products(self._client) if self._client else {}
        except Exception:
            dark = {}
        dark = dark or {}
        dark_live = int(dark.get("live_count") or 0)
        dark_total = int(dark.get("total") or 0)
        lines += [
            "",
            f"[{CYAN} b]◈ MØRKE PRODUKTER — nu i nervesystemet[/]"
            f"  [{FGDIM}]{dark_live}/{dark_total}[/]",
        ]
        dark_sections = dark.get("signals") or {}
        if not dark_sections:
            lines.append(f"  [{DIM}]— stille —[/]")
        else:
            for name, sec in sorted(dark_sections.items()):
                sec = sec or {}
                dot = (f"[{GREEN}]●[/]" if sec.get("liveness") else f"[{DIM}]○[/]")
                cnt = int(sec.get("count") or 0)
                lines.append(f"  {dot} [{FGDIM}]{_esc(name)}[/] [{FG}]{cnt}[/]")

        # -- memory-pipeline (A5) — always rendered, even if self is empty --
        try:
            mh = datasource.memory_health(self._client) if self._client else {}
        except Exception:
            mh = {}
        self._memory_health = mh or {}
        added = int(mh.get("added_today") or 0)
        journal_mark = (f"[{GREEN}]✓[/]" if mh.get("journal_today")
                        else f"[{AMBER}]mangler[/]")
        lines += [
            "",
            f"[{CYAN} b]◈ HUKOMMELSE[/]  [{FGDIM}]— memory-pipeline[/]",
            f"  [{FGDIM}]tilføjet i dag[/] [{FG} b]{added}[/]  [{FGDIM}]·[/]  "
            f"[{FGDIM}]dagens journal[/] {journal_mark}",
        ]

        # -- indre liv (A8) — reduceret: kun liveness+count pr. sektion --
        try:
            il = datasource.inner_life(self._client) if self._client else {}
        except Exception:
            il = {}
        il = il or {}
        il_live = int(il.get("live_count") or 0)
        il_total = int(il.get("total") or 0)
        lines += [
            "",
            f"[{CYAN} b]◈ INDRE LIV — {il_live}/{il_total} sektioner[/]",
        ]
        il_sections = il.get("inner_life") or {}
        if not il_sections:
            lines.append(f"  [{DIM}]— stille —[/]")
        else:
            for name, sec in sorted(il_sections.items()):
                sec = sec or {}
                dot = (f"[{GREEN}]●[/]" if sec.get("liveness") else f"[{DIM}]○[/]")
                cnt = int(sec.get("count") or 0)
                lines.append(f"  {dot} [{FGDIM}]{_esc(name)}[/] [{FG}]{cnt}[/]")

        # -- experiment & læring — AGI/experiment-laget, samme dot+count-format --
        exp_sections = il.get("experiment") or {}
        lines += [
            "",
            f"[{CYAN} b]◈ EXPERIMENT & LÆRING[/]",
        ]
        if not exp_sections:
            lines.append(f"  [{DIM}]— stille —[/]")
        else:
            for name, sec in sorted(exp_sections.items()):
                sec = sec or {}
                dot = (f"[{GREEN}]●[/]" if sec.get("liveness") else f"[{DIM}]○[/]")
                cnt = int(sec.get("count") or 0)
                lines.append(f"  {dot} [{FGDIM}]{_esc(name)}[/] [{FG}]{cnt}[/]")

        panel.update(Text.from_markup("\n".join(lines)))

    @staticmethod
    def _rel_age(iso: str) -> str:
        """ISO timestamp → short relative age (2s / 4m / 3t / 2d). '—' on failure."""
        s = str(iso or "").strip()
        if not s or s == "—":
            return "—"
        try:
            ts = datetime.fromisoformat(s.replace("Z", "+00:00"))
            now = datetime.now(ts.tzinfo) if ts.tzinfo else datetime.now()
            secs = max(0, int((now - ts).total_seconds()))
        except Exception:
            return s[:8] if len(s) > 8 else s
        if secs < 60:
            return f"{secs}s"
        if secs < 3600:
            return f"{secs // 60}m"
        if secs < 86400:
            return f"{secs // 3600}t"
        return f"{secs // 86400}d"

    @staticmethod
    def _fmt_value(value: Any) -> str:
        if isinstance(value, bool):
            return "on" if value else "off"
        return str(value)

    # -- Healing -----------------------------------------------------------
    _HEALER_FLAG = {
        "central.daemon_dead": "daemon_restart_live",
        "central.syslog_flood": "syslog_restart_live",
    }

    def _healer_flag_name(self, healer: dict) -> str | None:
        return self._HEALER_FLAG.get(str(healer.get("kind") or ""))

    def _render_healing_panel(self) -> None:
        try:
            panel = self.query_one("#hud-panel", Static)
        except Exception:
            return
        try:
            self._healers = datasource.healers(self._client) if self._client else {}
        except Exception:
            self._healers = {}
        reg = bool(self._healers.get("registry_enabled"))
        reg_color, reg_label = (GREEN, "on") if reg else (DIM, "off")
        healers = self._healers.get("healers") or []
        lines = [
            f"[{CYAN} b]◈ HEALING[/]",
            "",
            f"[{FGDIM}]registry[/]  [{reg_color} b]● {reg_label}[/]",
            "",
            f"[{CYAN}]healere[/]",
        ]
        if not healers:
            lines.append(f"[{DIM}]— ingen healere registreret —[/]")
        for i, h in enumerate(healers):
            kind = str(h.get("kind") or "")
            mode = str(h.get("mode") or "")
            destructive = bool(h.get("destructive"))
            live_on = bool(h.get("live_flag_on"))
            d_mark = f"[{AMBER}]⚠[/]" if destructive else f"[{DIM}]—[/]"
            live_color, live_label = (GREEN, "live") if live_on else (DIM, "shadow")
            settable = self._healer_flag_name(h) is not None
            note = "" if settable else f"  [{DIM}](ikke flag-styret)[/]"
            lines.append(
                f"  [{DIM}]{i}[/] [{FG}]{_esc(kind)}[/]  [{FGDIM}]{_esc(mode)}[/]  "
                f"farlig {d_mark}  [{live_color} b]● {live_label}[/]{note}"
            )
        if self._pending_write is not None:
            lines += ["", self._confirm_line()]
        panel.update(Text.from_markup("\n".join(lines)))

    def _render_placeholder_panel(self, name: str) -> None:
        try:
            panel = self.query_one("#hud-panel", Static)
        except Exception:
            return
        from central_cli.hud import _TABS
        label = {k: lbl for k, lbl, _ in _TABS}.get(name, name)
        panel.update(Text.from_markup(f"[{DIM}]— {label}: venter på wiring —[/]"))
