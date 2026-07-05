from __future__ import annotations

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Input, RichLog

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
