"""X-session til Jarvis' desktop-fane.

Starter `Xvfb :99` + en window manager, griber skærmen som JPEG og oversætter
input-dicts til `xdotool`-kald. Tåler at X-pakkerne mangler: i stedet for at
kaste returneres `{"status":"error","code":"DESKTOP_UNAVAILABLE","error":...}`.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import threading
import time
from typing import Any

DISPLAY = ":99"
BREDDE = 1280
HOEJDE = 800
_MAX_TEKST = 500
# Skrivebordsbaggrund. En rå X-session uden rodmotiv er kulsort, og en sort
# skaerm ser ud som en fejl selv naar streamen virker (maalt 5/11-2026).
BAGGRUND = "#2b3a4a"
_WM_KANDIDATER = ("openbox", "fluxbox", "icewm", "xfwm4", "twm")
_TASTE_RE = re.compile(r"^[A-Za-z0-9_]{1,32}$")
_KNAPPER = {"left": "1", "middle": "2", "right": "3"}

# Browser-tastenavne -> xdotool/X11 keysyms.
_TASTE_ALIAS = {
    "Enter": "Return", "Backspace": "BackSpace", "Escape": "Escape", "Tab": "Tab",
    "ArrowUp": "Up", "ArrowDown": "Down", "ArrowLeft": "Left", "ArrowRight": "Right",
    "Delete": "Delete", "Home": "Home", "End": "End", "PageUp": "Prior",
    "PageDown": "Next", "Shift": "Shift_L", "Control": "Control_L", "Alt": "Alt_L",
    "Meta": "Super_L", " ": "space", "Insert": "Insert",
}


def _fejl(kode: str, tekst: str) -> dict[str, Any]:
    return {"status": "error", "code": kode, "error": tekst}


def _utilgaengelig(tekst: str) -> dict[str, Any]:
    return _fejl("DESKTOP_UNAVAILABLE", tekst)


def _tal(v: Any, lo: float, hi: float) -> int | None:
    """Klem et tal til [lo, hi]; None hvis det ikke er et endeligt tal."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    if v != v or v in (float("inf"), float("-inf")):
        return None
    return int(max(lo, min(hi, v)))


def _taste(navn: Any) -> str | None:
    if not isinstance(navn, str):
        return None
    navn = _TASTE_ALIAS.get(navn, navn)
    if len(navn) == 1 and navn.isalnum():
        return navn
    if _F_TASTE.match(navn) or _TASTE_RE.match(navn):
        return navn
    return None


_F_TASTE = re.compile(r"^F([1-9]|1[0-2])$")


def bygg_input(msg: Any) -> list[list[str]] | None:
    """Ren funktion: input-dict -> liste af xdotool-argumentlister (eller None).

    Ugyldige, ukendte eller farlige input giver None. Intet kører her.
    """
    if not isinstance(msg, dict):
        return None
    t = msg.get("t")
    if t == "mouse":
        x = _tal(msg.get("x"), 0, BREDDE - 1)
        y = _tal(msg.get("y"), 0, HOEJDE - 1)
        kind = msg.get("kind")
        if x is None or y is None:
            return None
        flyt = ["mousemove", str(x), str(y)]
        if kind == "move":
            return [flyt]
        if kind == "wheel":
            dy = _tal(msg.get("dy"), -1000, 1000) or 0
            if dy == 0:
                return None
            return [flyt, ["click", "5" if dy > 0 else "4"]]
        knap = _KNAPPER.get(msg.get("button") or "left")
        if knap is None:
            return None
        if kind == "down":
            return [flyt, ["mousedown", knap]]
        if kind == "up":
            return [flyt, ["mouseup", knap]]
        return None
    if t == "key":
        navn = _taste(msg.get("key"))
        kind = msg.get("kind")
        if navn is None or kind not in ("down", "up"):
            return None
        return [["keydown" if kind == "down" else "keyup", navn]]
    if t == "text":
        tekst = msg.get("text")
        if not isinstance(tekst, str) or not tekst or len(tekst) > _MAX_TEKST:
            return None
        # Kontroltegn fjernes; "--" stopper at tekst tolkes som flag.
        ren = "".join(c for c in tekst if c == "\n" or (c.isprintable()))
        if not ren:
            return None
        return [["type", "--delay", "0", "--", ren]]
    # resize/nav/tab findes ikke på en rå desktop: afvis.
    return None


def xvfb_args(display: str = DISPLAY, bredde: int = BREDDE, hoejde: int = HOEJDE) -> list[str]:
    """Xvfb-kommandoen.

    ``-extension GLX`` er ikke kosmetik: uden det initialiserer Xvfb NVIDIA's
    EGL og dør med SIGABRT i ``libEGL_nvidia.so.0`` (målt 5/11-2026). En ren
    2D-desktop har ikke brug for GLX.
    """
    return ["Xvfb", display, "-screen", "0", f"{bredde}x{hoejde}x24",
            "-nolisten", "tcp", "-extension", "GLX"]


def mangler_pakker() -> list[str]:
    """Navne på manglende binære pakker (tom liste = klar)."""
    mangler = []
    for b in ("Xvfb", "xdotool"):
        if shutil.which(b) is None:
            mangler.append(b)
    if not any(shutil.which(w) for w in _WM_KANDIDATER):
        mangler.append("window manager (" + "/".join(_WM_KANDIDATER[:3]) + ")")
    if shutil.which("import") is None and shutil.which("ffmpeg") is None:
        mangler.append("import (ImageMagick) eller ffmpeg")
    return mangler


class XSession:
    def __init__(self, display: str = DISPLAY, bredde: int = BREDDE, hoejde: int = HOEJDE) -> None:
        self.display = display
        self.bredde = bredde
        self.hoejde = hoejde
        self._procs: list[subprocess.Popen] = []
        self._laas = threading.Lock()
        self._kor = False

    def _env(self) -> dict[str, str]:
        env = dict(os.environ)
        env["DISPLAY"] = self.display
        # Conda-miljoeets biblioteker skal ikke med til system-binaererne
        # (Xvfb, xdotool, xterm): de er bygget mod systemets libs.
        lp = env.get("LD_LIBRARY_PATH", "")
        renset = [
            p for p in lp.split(":")
            if p and "miniconda" not in p and "/conda" not in p
        ]
        if renset:
            env["LD_LIBRARY_PATH"] = ":".join(renset)
        else:
            env.pop("LD_LIBRARY_PATH", None)
        return env

    def _start_proc(self, args: list[str]) -> subprocess.Popen:
        p = subprocess.Popen(
            args, env=self._env(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        self._procs.append(p)
        return p

    def start(self) -> dict[str, Any]:
        if self._kor:
            return {"status": "ok"}
        mangler = mangler_pakker()
        if mangler:
            return _utilgaengelig("Mangler pakker: " + ", ".join(mangler))
        sok = "/tmp/.X11-unix/X" + self.display.lstrip(":")
        # En socket kan overleve sin X-server (draebt proces, genstartet
        # container). Uden dette tjek ville vi genbruge en doed skaerm og
        # melde "ok" paa et display ingen kan tegne paa.
        if os.path.exists(sok) and not self._server_svarer():
            self._ryd_doed_socket(sok)
        try:
            if not os.path.exists(sok):
                xvfb = self._start_proc(xvfb_args(self.display, self.bredde, self.hoejde))
                for _ in range(50):
                    if os.path.exists(sok) or xvfb.poll() is not None:
                        break
                    time.sleep(0.1)
                if not os.path.exists(sok):
                    self.stop()
                    return _utilgaengelig("Xvfb startede ikke")
            wm = next((w for w in _WM_KANDIDATER if shutil.which(w)), None)
            if wm:
                self._start_proc([wm])
            self._fyld_skrivebord()
        except OSError as exc:
            self.stop()
            return _utilgaengelig(f"Kunne ikke starte X-session: {exc}")
        self._kor = True
        return {"status": "ok"}

    def _server_svarer(self) -> bool:
        """Svarer X-serveren paa displayet? (ikke bare: findes socket-filen)"""
        try:
            res = subprocess.run(
                ["xdotool", "getdisplaygeometry"],
                env=self._env(), capture_output=True, timeout=3,
            )
        except (OSError, subprocess.TimeoutExpired):  # xdotool findes ikke eller svarer ikke: behandl som "nej"
            return False
        return res.returncode == 0 and bool(res.stdout.strip())

    def _ryd_doed_socket(self, sok: str) -> None:
        """Fjern resterne af en X-server der ikke svarer, saa vi kan starte en ny."""
        for sti in (sok, "/tmp/.X" + self.display.lstrip(":") + "-lock"):
            try:
                os.unlink(sti)
            except FileNotFoundError:  # allerede vaek: intet at rydde
                pass
            except OSError:  # ikke vores fil: lad den staa, start() fejler aerligt
                pass

    def _fyld_skrivebord(self) -> None:
        """Saet baggrund, filhaandtering og en terminal paa skrivebordet.

        Uden dette er sessionen en tom, sort skaerm: streamen virker, men der
        er intet at se eller klikke paa. Hver app er valgfri — mangler den,
        springes den over, og desktoppen er stadig gyldig.

        Idempotent: genbruges en X-server der allerede har apps paa skrivebordet
        (fx efter en genstart af API'et), startes ingen dubletter.
        """
        if shutil.which("xsetroot"):
            self._start_proc(["xsetroot", "-solid", BAGGRUND])
        if shutil.which("pcmanfm") and not self._har_vindue("pcmanfm"):
            self._start_proc(["pcmanfm", "--desktop"])
        if shutil.which("xterm") and not self._har_vindue("Jarvis"):
            self._start_proc([
                "xterm", "-fa", "Monospace", "-fs", "11",
                "-geometry", "100x28+40+40", "-title", "Jarvis",
            ])

    def _har_vindue(self, moenster: str) -> bool:
        """Findes der allerede et vindue med navnet? (saa vi ikke starter dubletter)"""
        try:
            res = subprocess.run(
                ["xdotool", "search", "--name", moenster],
                env=self._env(), capture_output=True, timeout=3,
            )
        except (OSError, subprocess.TimeoutExpired):  # xdotool findes ikke eller svarer ikke: behandl som "nej"
            return False
        return res.returncode == 0 and bool(res.stdout.strip())

    def stop(self) -> None:
        self._kor = False
        for p in reversed(self._procs):
            if p.poll() is None:
                p.terminate()
        for p in self._procs:
            try:
                p.wait(timeout=3)
            except subprocess.TimeoutExpired:  # lukker ikke pænt: dræb hårdt
                p.kill()
        self._procs.clear()

    def frame(self) -> bytes | dict[str, Any]:
        """Skærmen som JPEG-bytes, eller en struktureret fejl-dict."""
        if not self._kor:
            return _utilgaengelig("Desktop er ikke startet")
        if shutil.which("import"):
            cmd = ["import", "-window", "root", "-quality", "60", "jpeg:-"]
        elif shutil.which("ffmpeg"):
            cmd = ["ffmpeg", "-loglevel", "quiet", "-f", "x11grab", "-i", self.display,
                   "-frames:v", "1", "-q:v", "8", "-f", "mjpeg", "-"]
        else:
            return _utilgaengelig("Hverken import eller ffmpeg er installeret")
        try:
            res = subprocess.run(cmd, env=self._env(), capture_output=True, timeout=5)
        except (OSError, subprocess.TimeoutExpired) as exc:  # skaermgreb kan fejle eller hænge: rapportér i stedet for at dø
            return _fejl("FRAME_FAILED", f"Skærmgreb fejlede: {exc}")
        if res.returncode != 0 or not res.stdout:
            return _fejl("FRAME_FAILED", "Skærmgreb gav ingen data")
        return res.stdout

    def input(self, msg: Any) -> dict[str, Any]:
        """Oversæt og kør input. Aldrig exception; ugyldigt input giver fejl-dict."""
        if not self._kor:
            return _utilgaengelig("Desktop er ikke startet")
        kald = bygg_input(msg)
        if kald is None:
            return _fejl("INVALID_INPUT", "Ugyldigt eller afvist input")
        with self._laas:
            for args in kald:
                try:
                    subprocess.run(["xdotool", *args], env=self._env(),
                                   capture_output=True, timeout=5)
                except (OSError, subprocess.TimeoutExpired) as exc:  # xdotool findes ikke eller hænger: svar klienten i stedet for at dø
                    return _fejl("INPUT_FAILED", f"xdotool fejlede: {exc}")
        return {"status": "ok"}


_singleton: XSession | None = None
_singleton_laas = threading.Lock()


def shared_session() -> XSession:
    """Én delt X-session for hele processen.

    Desktoppen er en TILSTAND, ikke en forbindelse. Blev sessionen stoppet når
    den sidste websocket lukkede, forsvandt vinduerne og alt man var i gang
    med, hver gang man skiftede fane. Derfor deles den mellem alle klienter, og
    den stoppes kun ved eksplicit nedlukning.
    """
    global _singleton
    with _singleton_laas:
        if _singleton is None:
            _singleton = XSession()
        return _singleton
