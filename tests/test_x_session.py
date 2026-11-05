"""Enhedstests for core/desktop/x_session.py.

Dækker den rene input-oversættelse (ingen X nødvendig), afvisning af farligt
input, og at manglende X-pakker giver en struktureret fejl i stedet for en
exception. Den ægte X-session er verificeret manuelt mod en kørende Xvfb.
"""
from __future__ import annotations

from core.desktop import x_session as xs


def test_mus_flyt_og_klik_oversaettes():
    assert xs.bygg_input({"t": "mouse", "kind": "move", "x": 10, "y": 20}) == [["mousemove", "10", "20"]]
    assert xs.bygg_input({"t": "mouse", "kind": "down", "x": 1, "y": 2, "button": "right"}) == [
        ["mousemove", "1", "2"], ["mousedown", "3"]]
    assert xs.bygg_input({"t": "mouse", "kind": "up", "x": 1, "y": 2}) == [
        ["mousemove", "1", "2"], ["mouseup", "1"]]


def test_koordinater_klemmes():
    r = xs.bygg_input({"t": "mouse", "kind": "move", "x": 99999, "y": -5})
    assert r == [["mousemove", str(xs.BREDDE - 1), "0"]]


def test_hjul_retning():
    assert xs.bygg_input({"t": "mouse", "kind": "wheel", "x": 0, "y": 0, "dy": 50})[1] == ["click", "5"]
    assert xs.bygg_input({"t": "mouse", "kind": "wheel", "x": 0, "y": 0, "dy": -50})[1] == ["click", "4"]
    assert xs.bygg_input({"t": "mouse", "kind": "wheel", "x": 0, "y": 0, "dy": 0}) is None


def test_taster_oversaettes():
    assert xs.bygg_input({"t": "key", "kind": "down", "key": "Enter"}) == [["keydown", "Return"]]
    assert xs.bygg_input({"t": "key", "kind": "up", "key": "a"}) == [["keyup", "a"]]
    assert xs.bygg_input({"t": "key", "kind": "down", "key": "ArrowLeft"}) == [["keydown", "Left"]]


def test_tekst_bruger_dobbelt_bindestreg_og_fjerner_kontroltegn():
    r = xs.bygg_input({"t": "text", "text": "-rf\x00\x1b"})
    assert r == [["type", "--delay", "0", "--", "-rf"]]


def test_farlige_og_ugyldige_input_afvises():
    for d in (
        None, "tekst", [], {}, {"t": "nav", "action": "goto", "url": "x"},
        {"t": "resize", "w": 1, "h": 1}, {"t": "tab", "action": "new"},
        {"t": "mouse", "kind": "move", "x": "a", "y": 1},
        {"t": "mouse", "kind": "move", "x": float("nan"), "y": 1},
        {"t": "mouse", "kind": "move", "x": True, "y": 1},
        {"t": "mouse", "kind": "drop", "x": 1, "y": 1},
        {"t": "mouse", "kind": "down", "x": 1, "y": 1, "button": "9"},
        {"t": "key", "kind": "down", "key": "a; rm -rf /"},
        {"t": "key", "kind": "down", "key": "--help"},
        {"t": "key", "kind": "hold", "key": "a"},
        {"t": "key", "kind": "down", "key": 5},
        {"t": "text", "text": ""},
        {"t": "text", "text": "x" * 10_000},
        {"t": "text", "text": "\x00\x01"},
    ):
        assert xs.bygg_input(d) is None, d


def test_manglende_pakker_giver_struktureret_fejl(monkeypatch):
    monkeypatch.setattr(xs.shutil, "which", lambda _n: None)
    assert xs.mangler_pakker()
    res = xs.XSession().start()
    assert res["status"] == "error"
    assert res["code"] == "DESKTOP_UNAVAILABLE"
    assert res["error"]


def test_frame_og_input_uden_start_kaster_ikke():
    s = xs.XSession()
    f = s.frame()
    assert isinstance(f, dict) and f["code"] == "DESKTOP_UNAVAILABLE"
    i = s.input({"t": "key", "kind": "down", "key": "a"})
    assert i["code"] == "DESKTOP_UNAVAILABLE"


def test_ugyldigt_input_paa_koerende_session_giver_fejl_dict(monkeypatch):
    s = xs.XSession()
    s._kor = True
    kaldt = []
    monkeypatch.setattr(xs.subprocess, "run", lambda *a, **k: kaldt.append(a))
    assert s.input({"t": "key", "kind": "down", "key": "a;b"})["code"] == "INVALID_INPUT"
    assert kaldt == []
    assert s.input({"t": "key", "kind": "down", "key": "a"})["status"] == "ok"
    assert kaldt[0][0] == ["xdotool", "keydown", "a"]


def test_conda_stier_fjernes_fra_x_miljoeet(monkeypatch):
    """Conda-miljoeets biblioteker skal ikke med til X-systembinaererne.

    De er bygget mod systemets libs. (At Xvfb ogsaa doede paa NVIDIA's EGL er
    en ANDEN aarsag — den haandteres med -extension GLX, se testen nedenfor.)
    """
    monkeypatch.setenv("LD_LIBRARY_PATH", "/home/bs/miniconda3/envs/ai/lib:/usr/local/lib")
    env = xs.XSession()._env()
    assert "miniconda" not in env.get("LD_LIBRARY_PATH", "")
    assert "/usr/local/lib" in env.get("LD_LIBRARY_PATH", "")
    assert env["DISPLAY"] == xs.DISPLAY


def test_kun_conda_sti_fjerner_variablen_helt(monkeypatch):
    monkeypatch.setenv("LD_LIBRARY_PATH", "/home/bs/miniconda3/envs/ai/lib")
    env = xs.XSession()._env()
    assert "LD_LIBRARY_PATH" not in env


# ── Xvfb-kommandoen: GLX skal vaere slaaet fra ────────────────────────────
# Maalt 5/11-2026: uden -extension GLX doer Xvfb med SIGABRT inde i
# libEGL_nvidia.so.0 — den toemte skaermen var altsaa ikke et stream-problem
# men en X-server der aldrig kom op.
def test_xvfb_slaar_glx_fra():
    args = xs.xvfb_args(":99", 1280, 800)
    assert args[0] == "Xvfb"
    assert "-extension" in args
    assert args[args.index("-extension") + 1] == "GLX"


def test_xvfb_bruger_display_og_stoerrelse():
    args = xs.xvfb_args(":42", 800, 600)
    assert ":42" in args
    assert "800x600x24" in args


# ── Skrivebordet skal have indhold ───────────────────────────────────────
def _stub_proc(args=None, pid=0):
    class P:
        def __init__(self):
            self.args = list(args or [])
            self.pid = pid
        def poll(self): return None
        def wait(self, timeout=None): return 0
        def terminate(self): pass
        def kill(self): pass
        def is_alive(self): return True
        def start(self): pass
    return P()


def _stub_koert():
    class R:
        returncode = 0
        stdout = b""
    return R()


def test_skrivebordet_faar_baggrund_og_terminal(monkeypatch):
    """En tom X-session er kulsort. Uden apps ser streamen ud som en fejl."""
    s = xs.XSession()
    kaldt: list[list[str]] = []
    koert: list[list[str]] = []
    monkeypatch.setattr(xs.shutil, "which", lambda n: "/usr/bin/" + n)
    monkeypatch.setattr(s, "_start_proc", lambda args: (kaldt.append(args), _stub_proc(args))[1])
    monkeypatch.setattr(s, "_har_vindue", lambda _m: False)
    monkeypatch.setattr(s, "_har_klasse", lambda _k: False)
    monkeypatch.setattr(xs.subprocess, "run", lambda cmd, **kw: (koert.append(cmd), _stub_koert())[1])
    s._fyld_skrivebord()
    kommandoer = [k[0] for k in kaldt]
    assert "pcmanfm" in kommandoer
    assert "xterm" in kommandoer
    assert any(xs.BAGGRUND in k for k in koert if k and k[0] == "xsetroot")


def test_skrivebordet_starter_ikke_dubletter(monkeypatch):
    """Genbruges en X-server der allerede har apps, maa vi ikke stable oven paa.

    Terminalen tjekkes paa PROCESSEN der ejer et vindue — ikke paa vinduets
    titel, som skallen overskriver (maalt 5/11-2026).
    """
    s = xs.XSession()
    kaldt: list[list[str]] = []
    s._procs.append(_stub_proc(["xterm", "-title", "Jarvis"], pid=4242))
    monkeypatch.setattr(xs.shutil, "which", lambda n: "/usr/bin/" + n)
    monkeypatch.setattr(s, "_start_proc", lambda args: (kaldt.append(args), _stub_proc(args))[1])
    monkeypatch.setattr(s, "_har_vindue", lambda _m: True)
    monkeypatch.setattr(s, "_har_klasse", lambda _k: True)
    monkeypatch.setattr(s, "_vinduer_for", lambda _pid: ["123"])
    monkeypatch.setattr(xs.subprocess, "run", lambda cmd, **kw: _stub_koert())
    s._fyld_skrivebord()
    kommandoer = [k[0] for k in kaldt]
    assert "pcmanfm" not in kommandoer
    assert "xterm" not in kommandoer


def test_efter_api_genstart_adopteres_terminalen(monkeypatch):
    """En ny API-proces ejer ingen processer, men skaermen staar der endnu.

    Uden adoption ville hver genstart stable endnu en terminal oven paa den
    foerste (maalt 5/11-2026: fire xterm-processer, ét vindue).
    """
    s = xs.XSession()
    kaldt: list[list[str]] = []
    monkeypatch.setattr(xs.shutil, "which", lambda n: "/usr/bin/" + n)
    monkeypatch.setattr(s, "_start_proc", lambda args: (kaldt.append(args), _stub_proc(args))[1])
    monkeypatch.setattr(s, "_har_klasse", lambda _k: True)
    monkeypatch.setattr(xs.subprocess, "run", lambda cmd, **kw: _stub_koert())
    s._fyld_skrivebord()
    assert kaldt == []


def test_skrivebordet_taaler_manglende_apps(monkeypatch):
    """Mangler xterm/pcmanfm, er desktoppen stadig gyldig — ikke en fejl."""
    s = xs.XSession()
    kaldt: list[list[str]] = []
    monkeypatch.setattr(xs.shutil, "which", lambda n: None)
    monkeypatch.setattr(s, "_start_proc", lambda args: (kaldt.append(args), _stub_proc(args))[1])
    monkeypatch.setattr(s, "_har_vindue", lambda _m: False)
    s._fyld_skrivebord()
    assert kaldt == []


# ── Den delte desktop skal ikke raadne ───────────────────────────────────
# Maalt 5/11-2026: openbox og pcmanfm stod som <defunct> med API-processen som
# foraelder, mens sessionen meldte "ok". Skaermen blev tom, og ingen klient
# kunne se at der var noget galt — derfor skal sessionen vedligeholde sig selv.
def test_doede_boern_reapes():
    """poll() er det der reaper: et doedt barn maa ikke blive en zombie."""
    s = xs.XSession()
    doed = _stub_proc(["openbox"])
    doed.poll = lambda: 1
    levende = _stub_proc(["xterm"])
    s._procs.extend([doed, levende])
    s._ryd_doede()
    assert s._procs == [levende]


def test_wm_doed_opdages():
    s = xs.XSession()
    doed = _stub_proc(["openbox"])
    doed.poll = lambda: 1
    s._procs.append(doed)
    assert s._wm_oppe() is False


def test_wm_levende_opdages():
    s = xs.XSession()
    s._procs.append(_stub_proc(["/usr/bin/openbox"]))
    assert s._wm_oppe() is True


def test_vedligehold_genstarter_doed_wm(monkeypatch):
    """En delt session maa ikke melde ok paa en skaerm ingen kan bruge."""
    s = xs.XSession()
    s._kor = True
    startet: list[list[str]] = []
    monkeypatch.setattr(xs.shutil, "which", lambda n: "/usr/bin/" + n)
    monkeypatch.setattr(s, "_start_proc", lambda args: (startet.append(args), _stub_proc(args))[1])
    monkeypatch.setattr(s, "_fyld_skrivebord", lambda: None)
    monkeypatch.setattr(xs.time, "sleep", lambda _s: None)
    s._vedligehold()
    assert "openbox" in [k[0] for k in startet]


def test_vedligehold_genstarter_ikke_levende_wm(monkeypatch):
    s = xs.XSession()
    s._kor = True
    s._procs.append(_stub_proc(["openbox"]))
    startet: list[list[str]] = []
    monkeypatch.setattr(xs.shutil, "which", lambda n: "/usr/bin/" + n)
    monkeypatch.setattr(s, "_start_proc", lambda args: (startet.append(args), _stub_proc(args))[1])
    monkeypatch.setattr(s, "_fyld_skrivebord", lambda: None)
    s._vedligehold()
    assert startet == []


def test_start_paa_doed_server_starter_forfra(monkeypatch):
    """Svarer X-serveren ikke, maa start() rydde op i stedet for at melde ok."""
    s = xs.XSession()
    s._kor = True
    stoppet = []
    monkeypatch.setattr(s, "_server_svarer", lambda: False)
    monkeypatch.setattr(s, "stop", lambda: stoppet.append(True))
    monkeypatch.setattr(xs, "mangler_pakker", lambda: ["Xvfb"])
    res = s.start()
    assert stoppet == [True]
    assert res["status"] == "error"


def test_vagten_startes_kun_en_gang(monkeypatch):
    s = xs.XSession()
    startet = []
    monkeypatch.setattr(xs.threading, "Thread", lambda **kw: (startet.append(kw), _stub_proc())[1])
    s._start_vagt()
    s._start_vagt()
    assert len(startet) == 1
    assert startet[0]["daemon"] is True


# ── Sessionen pr. bruger ─────────────────────────────────────────────────
def test_session_for_er_cachet_pr_bruger(monkeypatch, tmp_path):
    """Desktoppen er en tilstand: samme bruger faar SAMME skaerm igen."""
    monkeypatch.setattr(xs, "_REGISTER_DIR", tmp_path / "reg")
    monkeypatch.setattr(xs, "_sessioner", {})
    monkeypatch.setattr(xs, "_workspace_for", lambda u, p: tmp_path)
    assert xs.session_for("a", "owner") is xs.session_for("a", "owner")
    assert not hasattr(xs, "shared_session")


def test_doed_socket_ryddes(monkeypatch, tmp_path):
    sok = tmp_path / "X99"
    sok.write_text("")
    lock = "/tmp/.X99-lock"
    s = xs.XSession()
    s._ryd_doed_socket(str(sok))
    assert not sok.exists()


def test_doed_socket_rydder_ikke_fremmede_filer(monkeypatch, tmp_path):
    """En fil vi ikke kan slette maa ikke kaste — start() skal fejle aerligt."""
    s = xs.XSession()

    def nægt(_p):
        raise PermissionError("ikke vores")

    monkeypatch.setattr(xs.os, "unlink", nægt)
    s._ryd_doed_socket("/tmp/.X11-unix/X99")  # kaster ikke



# ── Markøren, zoom og wait (5/11-2026) ───────────────────────────────────
# De tre medlemmer fra Anthropics computer-toolset. Markøren er den vigtigste:
# X11 tegner den UDEN FOR billedbufferen, så skærmgrebet indeholder den ikke —
# musen flyttede sig mens skærmen så død ud (målt 5/11-2026).
def _svar(stdout: bytes, rc: int = 0):
    class R:
        returncode = rc
    R.stdout = stdout
    return R


def test_cursor_laeser_position(monkeypatch):
    s = xs.XSession()
    s._kor = True
    monkeypatch.setattr(xs.subprocess, "run", lambda *a, **k: _svar(b"X=640\nY=400\nSCREEN=0\nWINDOW=1\n"))
    assert s.cursor() == {"status": "ok", "x": 640, "y": 400}


def test_cursor_klemmer_til_skarmen(monkeypatch):
    s = xs.XSession()
    s._kor = True
    monkeypatch.setattr(xs.subprocess, "run", lambda *a, **k: _svar(b"X=99999\nY=-5\n"))
    assert s.cursor() == {"status": "ok", "x": xs.BREDDE - 1, "y": 0}


def test_cursor_ugyldigt_svar_giver_struktureret_fejl(monkeypatch):
    s = xs.XSession()
    s._kor = True
    monkeypatch.setattr(xs.subprocess, "run", lambda *a, **k: _svar(b"noget andet\n"))
    assert s.cursor()["code"] == "CURSOR_FAILED"
    monkeypatch.setattr(xs.subprocess, "run", lambda *a, **k: _svar(b"", rc=1))
    assert s.cursor()["code"] == "CURSOR_FAILED"


def test_cursor_og_zoom_uden_start_kaster_ikke():
    s = xs.XSession()
    assert s.cursor()["code"] == "DESKTOP_UNAVAILABLE"
    assert s.zoom(0, 0, 100, 100)["code"] == "DESKTOP_UNAVAILABLE"
    assert s.wait(100)["code"] == "DESKTOP_UNAVAILABLE"


def test_zoom_skalerer_et_udsnit_op(monkeypatch):
    s = xs.XSession()
    s._kor = True
    kaldt: list[list[str]] = []
    monkeypatch.setattr(xs.shutil, "which", lambda n: "/usr/bin/" + n)
    monkeypatch.setattr(xs.subprocess, "run", lambda cmd, **k: (kaldt.append(cmd), _svar(b"\xff\xd8jpeg"))[1])
    ud = s.zoom(100, 200, 300, 150, 3)
    assert ud == b"\xff\xd8jpeg"
    cmd = kaldt[0]
    assert cmd[0] == "import"
    assert "300x150+100+200" in cmd
    assert "300%" in cmd


def test_zoom_klemmer_udsnittet_ind_paa_skarmen(monkeypatch):
    s = xs.XSession()
    s._kor = True
    kaldt: list[list[str]] = []
    monkeypatch.setattr(xs.shutil, "which", lambda n: "/usr/bin/" + n)
    monkeypatch.setattr(xs.subprocess, "run", lambda cmd, **k: (kaldt.append(cmd), _svar(b"x"))[1])
    s.zoom(xs.BREDDE - 10, xs.HOEJDE - 10, 500, 500, 2)
    crop = kaldt[0][kaldt[0].index("-crop") + 1]
    w, h = crop.split("+")[0].split("x")
    assert int(w) <= 10 and int(h) <= 10


def test_zoom_afviser_ikke_tal(monkeypatch):
    s = xs.XSession()
    s._kor = True
    assert s.zoom("a", 0, 10, 10)["code"] == "INVALID_INPUT"
    assert s.zoom(0, 0, None, 10)["code"] == "INVALID_INPUT"


def test_wait_ser_naar_skaermen_aendrer_sig(monkeypatch):
    """Efter et klik skal vi kunne MAALE om der skete noget, ikke gætte."""
    s = xs.XSession()
    s._kor = True
    rammer = iter([b"a", b"a", b"b"])
    monkeypatch.setattr(s, "frame", lambda: next(rammer))
    monkeypatch.setattr(xs.time, "sleep", lambda _s: None)
    r = s.wait(2000)
    assert r["status"] == "ok" and r["changed"] is True


def test_wait_uden_aendring_loeber_ud(monkeypatch):
    s = xs.XSession()
    s._kor = True
    monkeypatch.setattr(s, "frame", lambda: b"a")
    monkeypatch.setattr(xs.time, "sleep", lambda _s: None)
    ur = iter(range(0, 100000, 100))
    monkeypatch.setattr(xs.time, "monotonic", lambda: next(ur))
    r = s.wait(500)
    assert r["status"] == "ok" and r["changed"] is False
