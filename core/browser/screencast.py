"""CDP-screencast af Jarvis' server-side browser — kilden til PWA'ens delte browser.

Playwrights sync-API maa ikke kaldes fra asyncio-loopet; alt gaar gennem
``run_in_playwright``. To fakta om sync-API'et former designet:

* CDP-events (``Page.screencastFrame``) leveres KUN mens worker-traaden kalder
  ind i Playwright. Worker'en sidder ellers og blokerer paa sin kommandokoe.
  Derfor ``pump()``: en kort ``wait_for_timeout`` som lader events loebe.
* Man maa ikke kalde sync-metoder inde fra en event-handler. Handleren lægger
  derfor kun framen i en traadsikker koe og noterer sessionId; selve
  ``Page.screencastFrameAck`` sendes i naeste ``pump()``.
"""
from __future__ import annotations

import base64
import logging
import queue
import threading
from typing import Any, Callable
from urllib.parse import urlparse

from core.browser.playwright_session import run_in_playwright

logger = logging.getLogger(__name__)

MAX_DIM = 4096
MIN_DIM = 100
_PUMP_MS = 40
_TILLADTE_SKEMAER = {"http", "https"}
_MUS_KNAPPER = {"left", "middle", "right"}


def normaliser_url(url: Any) -> str | None:
    """Kun http(s) og about:blank. file:, javascript:, chrome: m.fl. afvises."""
    t = str(url or "").strip()
    if not t or len(t) > 4096:
        return None
    if t == "about:blank":
        return t
    if "://" not in t and " " not in t and "." in t:
        t = "https://" + t
    p = urlparse(t)
    if p.scheme.lower() in _TILLADTE_SKEMAER and p.netloc:
        return t
    return None


def _tal(v: Any, lo: float, hi: float) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):  # ikke et tal: kalderen skal se "ugyldig", ikke 0
        return None
    if f != f or f < lo or f > hi:  # NaN eller udenfor
        return None
    return f


class ScreencastSession:
    """Én WS-forbindelses skærmstrøm + input mod den aktive side."""

    def __init__(self, *, quality: int = 60, max_queue: int = 2) -> None:
        self.quality = quality
        self.frames: queue.Queue[bytes] = queue.Queue(maxsize=max_queue)
        self._cdp: Any = None
        self._page: Any = None
        self._acks: list[int] = []
        self._lock = threading.Lock()

    # ── kaldes KUN fra worker-traaden (inde i run_in_playwright) ──────────
    def _on_frame(self, params: dict) -> None:
        try:
            raw = base64.b64decode(params.get("data") or "")
        except Exception:  # ugyldig base64 = ingen frame; CDP kan sende tom data
            raw = b""
        with self._lock:
            sid = params.get("sessionId")
            if isinstance(sid, int):
                self._acks.append(sid)
        if not raw:
            return
        try:
            self.frames.put_nowait(raw)
        except queue.Full:
            try:
                self.frames.get_nowait()  # smid den aeldste — klienten skal se NU
            except queue.Empty:  # en anden toemte den foerst; intet at smide
                pass
            try:
                self.frames.put_nowait(raw)
            except queue.Full:  # stadig fuld efter toemning: drop frame, aldrig bloker
                pass

    def _detach(self) -> None:
        cdp, self._cdp, self._page = self._cdp, None, None
        if cdp is None:
            return
        for step in (lambda: cdp.send("Page.stopScreencast"), cdp.detach):
            try:
                step()
            except Exception:  # siden/CDP kan allerede vaere lukket; oprydning skal fortsaette
                pass

    def _attach(self, ctx: Any) -> None:
        self._detach()
        page = ctx.page
        cdp = page.context.new_cdp_session(page)
        cdp.on("Page.screencastFrame", self._on_frame)
        cdp.send("Page.startScreencast", {
            "format": "jpeg", "quality": self.quality, "everyNthFrame": 1,
        })
        self._cdp, self._page = cdp, page

    def _start_fn(self, ctx: Any) -> bool:
        self._attach(ctx)
        return True

    def _pump_fn(self, ctx: Any) -> bool:
        # Aktiv side skiftet (faneskift/ny fane)? Saa flyttes strømmen med.
        if ctx.page is not self._page:
            self._attach(ctx)
        ctx.page.wait_for_timeout(_PUMP_MS)  # lader CDP-events loebe
        with self._lock:
            acks, self._acks = self._acks, []
        if self._cdp is not None:
            for sid in acks:
                try:
                    self._cdp.send("Page.screencastFrameAck", {"sessionId": sid})
                except Exception:  # CDP kan vaere revet ned midt i pump; ack er best-effort
                    pass
        return True

    def _stop_fn(self, ctx: Any) -> bool:
        self._detach()
        return True

    # ── kaldes fra enhver traad ────────────────────────────────────────────
    def start(self) -> None:
        run_in_playwright(self._start_fn, timeout=30.0)

    def pump(self) -> None:
        run_in_playwright(self._pump_fn, timeout=10.0)

    def stop(self) -> None:
        try:
            run_in_playwright(self._stop_fn, timeout=5.0)
        except Exception:  # worker kan vaere doed eller optaget; stop er best-effort
            pass

    def next_frame(self, timeout: float = 0.2) -> bytes | None:
        try:
            return self.frames.get(timeout=timeout)
        except queue.Empty:  # ingen frame inden for timeout: det er det normale svar
            return None


# ── Input: ren validering -> en funktion der koeres i worker-traaden ──────

def bygg_input(msg: Any) -> Callable[[Any], Any] | None:
    """Oversaet en klientbesked til en worker-funktion, eller None hvis ugyldig.

    Alt valideres foer det naar Playwright: typer, graenser, tilladte skemaer.
    """
    if not isinstance(msg, dict):
        return None
    t = msg.get("t")

    if t == "mouse":
        kind = msg.get("kind")
        x = _tal(msg.get("x", 0), 0, 20000)
        y = _tal(msg.get("y", 0), 0, 20000)
        if x is None or y is None:
            return None
        knap = msg.get("button", "left")
        if knap not in _MUS_KNAPPER:
            return None
        if kind == "move":
            return lambda c: c.page.mouse.move(x, y)
        if kind == "down":
            return lambda c: (c.page.mouse.move(x, y), c.page.mouse.down(button=knap))
        if kind == "up":
            return lambda c: (c.page.mouse.move(x, y), c.page.mouse.up(button=knap))
        if kind == "wheel":
            dx = _tal(msg.get("dx", 0), -20000, 20000)
            dy = _tal(msg.get("dy", 0), -20000, 20000)
            if dx is None or dy is None:
                return None
            return lambda c: (c.page.mouse.move(x, y), c.page.mouse.wheel(dx, dy))
        return None

    if t == "key":
        key = msg.get("key")
        kind = msg.get("kind")
        if not isinstance(key, str) or not (1 <= len(key) <= 32):
            return None
        if kind == "down":
            return lambda c: c.page.keyboard.down(key)
        if kind == "up":
            return lambda c: c.page.keyboard.up(key)
        return None

    if t == "text":
        txt = msg.get("text")
        if not isinstance(txt, str) or not (1 <= len(txt) <= 2000):
            return None
        return lambda c: c.page.keyboard.insert_text(txt)

    if t == "resize":
        w = _tal(msg.get("w"), MIN_DIM, MAX_DIM)
        h = _tal(msg.get("h"), MIN_DIM, MAX_DIM)
        if w is None or h is None:
            return None
        return lambda c: c.page.set_viewport_size({"width": int(w), "height": int(h)})

    if t == "nav":
        action = msg.get("action")
        if action == "back":
            return lambda c: c.page.go_back()
        if action == "forward":
            return lambda c: c.page.go_forward()
        if action == "reload":
            return lambda c: c.page.reload()
        if action == "goto":
            url = normaliser_url(msg.get("url"))
            if url is None:
                return None
            return lambda c: c.page.goto(url, wait_until="commit")
        return None

    if t == "tab":
        action = msg.get("action")
        idx = msg.get("index")
        if action == "new":
            url = normaliser_url(msg.get("url") or "about:blank")
            if url is None:
                return None

            def _ny(c: Any) -> Any:
                p = c.page.context.new_page()
                c.switch_page(p)
                if url != "about:blank":
                    p.goto(url, wait_until="commit")
            return _ny
        if action in ("switch", "close") and isinstance(idx, int) and 0 <= idx < 200:
            def _fane(c: Any) -> Any:
                pages = c.all_pages()
                if idx >= len(pages):
                    return None
                p = pages[idx]
                if action == "switch":
                    p.bring_to_front()
                    c.switch_page(p)
                else:
                    p.close()
                    rest = c.all_pages()
                    if rest:
                        c.switch_page(rest[-1])
            return _fane
        return None

    return None


def hent_faner(ctx: Any) -> list[dict]:
    """Faneliste i samme form som Electron-broens `faner()`."""
    ud: list[dict] = []
    for i, p in enumerate(ctx.all_pages()):
        try:
            titel = p.title()
        except Exception:  # siden kan vaere midt i navigation; tom titel er aerlig
            titel = ""
        try:
            kan_tilbage = bool(p.evaluate("history.length > 1"))
        except Exception:  # evaluate fejler paa en side uden JS-koerende kontekst
            kan_tilbage = False
        ud.append({
            "id": i, "url": p.url, "titel": titel, "aktiv": p is ctx.page,
            "kanTilbage": kan_tilbage, "kanFrem": True, "henter": False,
        })
    return ud
