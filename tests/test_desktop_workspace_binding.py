"""Workspace-binding og indespærring af desktop-sessioner (5/11-2026).

Teknik (a): bubblewrap-namespace. Testene (e) kører ÆGTE bwrap — en test der
kun tjekkede kommandolinjen ville bevise strengen, ikke indespærringen.
"""
from __future__ import annotations

import inspect
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from core.desktop import x_session as xs
from core.runtime import workspace_paths as wp

BWRAP_OK = (
    shutil.which("bwrap") is not None
    and subprocess.run(["bwrap", "--ro-bind", "/", "/", "true"],
                       capture_output=True).returncode == 0
)


class _Proc:
    """Stand-in for Popen: kan faa attributter og har ingen proces bag sig."""
    args: list = []

    def poll(self):
        return None


@pytest.fixture
def miljo(tmp_path, monkeypatch):
    home = tmp_path / "home"
    for n in ("bjorn", "lotte", "mikkel"):
        (home / "workspaces" / n).mkdir(parents=True)
    (home / "shared").mkdir()
    monkeypatch.setenv("JARVIS_HOME", str(home))
    monkeypatch.setattr(xs, "_REGISTER_DIR", tmp_path / "reg")
    monkeypatch.setattr(xs, "_sessioner", {})
    navne = {"u-bjorn": "bjorn", "u-lotte": "lotte", "u-mikkel": "mikkel"}

    def opløs(uid):
        if uid not in navne:
            raise wp.NoUserContextError(uid)
        return navne[uid]

    monkeypatch.setattr(wp, "_user_id_to_workspace_name", opløs)
    return home


def test_a_to_members_faar_hver_sin_session_og_cwd(miljo):
    a = xs.session_for("u-lotte", "member")
    b = xs.session_for("u-mikkel", "member")
    assert a is not b
    assert a.display != b.display
    assert a.workspace == (miljo / "workspaces" / "lotte").resolve()
    assert b.workspace == (miljo / "workspaces" / "mikkel").resolve()
    assert xs.session_for("u-lotte", "member") is a


def test_klienter_starter_med_cwd_i_workspace(miljo, monkeypatch):
    set_ = []
    monkeypatch.setattr(xs.subprocess, "Popen",
                        lambda args, **kw: set_.append((list(args), kw.get("cwd"))) or _Proc())
    owner = xs.session_for("u-bjorn", "owner")
    owner._start_proc(["xterm"])
    owner._start_proc(["Xvfb", ":1"])
    assert set_[0] == (["xterm"], str(miljo / "workspaces" / "bjorn"))
    assert set_[1][1] is None  # X-serveren selv hører ikke hjemme i workspace


@pytest.mark.skipif(not BWRAP_OK, reason="bwrap ikke brugbar her")
def test_b_owner_starter_i_bjorn_og_er_ikke_indespaerret(miljo, tmp_path):
    s = xs.session_for("u-bjorn", "owner")
    assert s.workspace == (miljo / "workspaces" / "bjorn").resolve()
    udenfor = tmp_path / "udenfor.txt"
    udenfor.write_text("hemmelig")
    # owner-klienter køres uden sandbox og med cwd i workspace
    r = subprocess.run(["sh", "-c", f"pwd; cat {udenfor}; echo x > {tmp_path}/skrevet"],
                       cwd=s.workspace, capture_output=True, text=True)
    assert r.stdout.split("\n")[0] == str(s.workspace)
    assert "hemmelig" in r.stdout
    assert (tmp_path / "skrevet").exists()
    # og Popen-kaldet pakkes IKKE i bwrap
    kald = []
    import unittest.mock as m
    with m.patch.object(xs.subprocess, "Popen", lambda a, **k: kald.append(a) or _Proc()):
        s._start_proc(["xterm"])
    assert kald == [["xterm"]]


def test_c_self_deler_ejerens_skærm_og_er_ikke_indespærret(miljo, monkeypatch):
    """Jarvis arbejder PÅ ejerens skærm — ikke ved siden af den.

    En desktop vi ikke deler er to VNC-sessioner, og så er delingen af fladen
    væk (Bjørn 5/11-2026). Testen kræver SAMME objekt, ikke en kopi med samme
    display: en kopi ville se rigtig ud og alligevel være en anden skærm.
    """
    monkeypatch.setattr(xs, "_owner_user", lambda: "u-bjorn")
    min_ = xs.session_for("hvadsomhelst", "self")
    hans = xs.session_for("u-bjorn", "owner")
    assert min_ is hans
    assert min_.display == hans.display
    assert min_.workspace == (miljo / "workspaces" / "bjorn").resolve()
    kald = []
    monkeypatch.setattr(xs.subprocess, "Popen", lambda a, **k: kald.append(a) or _Proc())
    min_._start_proc(["xterm"])
    assert kald == [["xterm"]]  # ikke indespærret


def test_c_self_uden_ejer_fejler_uden_fallback(miljo, monkeypatch):
    """Ingen ejer at dele med -> nægt. Aldrig en lydløs separat session."""
    monkeypatch.setattr(xs, "_owner_user", lambda: "")
    with pytest.raises(xs.WorkspaceUnavailable):
        xs.session_for("hvadsomhelst", "self")
    assert xs._sessioner == {}


def test_c_member_faar_aldrig_ejerens_session(miljo, monkeypatch):
    """Delingen gælder ejer+Jarvis. Et medlem har sin EGEN indespærrede skærm.

    Det er hele grunden til at `self` ikke må være en fælles session: der er
    flere brugere, og en delt skærm ville give dem ejerens.
    """
    monkeypatch.setattr(xs, "_owner_user", lambda: "u-bjorn")
    ejer = xs.session_for("u-bjorn", "owner")
    jarvis = xs.session_for(xs.SELF_USER, "self")
    assert jarvis is ejer
    for uid, navn in (("u-lotte", "lotte"), ("u-mikkel", "mikkel")):
        m = xs.session_for(uid, "member")
        assert m is not ejer
        assert m.display != ejer.display
        assert m.workspace != ejer.workspace
        assert m.workspace == (miljo / "workspaces" / navn).resolve()
        assert m.privilege == "member"


@pytest.mark.parametrize("bruger", ["ukendt", "", "  "])
def test_d_member_med_ugyldigt_workspace_faar_unavailable(miljo, bruger):
    with pytest.raises(xs.WorkspaceUnavailable):
        xs.session_for(bruger, "member")
    assert xs._sessioner == {}  # og INGEN session blev oprettet


def test_d_manglende_mappe_er_unavailable(miljo):
    import shutil as sh
    sh.rmtree(miljo / "workspaces" / "lotte")
    with pytest.raises(xs.WorkspaceUnavailable):
        xs.session_for("u-lotte", "member")


def test_d_ruten_lukker_med_workspace_unavailable(miljo, monkeypatch):
    import asyncio

    from apps.api.jarvis_api.routes import desktop_stream as ds
    from core.runtime import ws_auth

    monkeypatch.setattr(ws_auth, "verificer", lambda t: {"sub": "ukendt", "role": "member"})
    lukket = []

    class WS:
        headers = {}

        async def close(self, code, reason):
            lukket.append((code, reason))

        async def accept(self, **kw):
            pass

    asyncio.run(ds.desktop_stream(WS()))
    assert lukket == [(1008, "workspace_unavailable")]


@pytest.mark.skipif(not BWRAP_OK, reason="bwrap ikke brugbar her")
def test_e_member_kan_ikke_bryde_ud(miljo, tmp_path, monkeypatch):
    s = xs.session_for("u-lotte", "member")
    andens = miljo / "workspaces" / "mikkel"
    (andens / "hemmelig.txt").write_text("andens-data")
    mit = s.workspace
    (mit / "link_passwd").symlink_to("/etc/passwd")
    (mit / "link_ws").symlink_to(andens)
    # bwrap skal ikke bruge et ægte X-socket i testen
    sok = tmp_path / "X"
    sok.write_text("")

    def koer(kommando: str):
        a = _bwrap(s, sok) + ["sh", "-c", kommando]
        return subprocess.run(a, capture_output=True, text=True, cwd=mit)

    # cwd er workspace inde i sandboxen
    assert koer("pwd").stdout.strip() == str(mit)
    # absolut sti
    assert koer("cat /etc/passwd").returncode != 0
    assert koer(f"echo x > {andens}/ny.txt").returncode != 0
    assert koer(f"cat {andens}/hemmelig.txt").returncode != 0
    # ..
    assert koer("cat ../../../../../etc/passwd").returncode != 0
    assert koer("cat ../mikkel/hemmelig.txt").returncode != 0
    assert koer("echo x > ../mikkel/ny.txt").returncode != 0
    # symlink
    assert koer("cat link_passwd").returncode != 0
    assert koer("cat link_ws/hemmelig.txt").returncode != 0
    assert koer("echo x > link_ws/ny.txt").returncode != 0
    # værten er uberørt
    assert not (andens / "ny.txt").exists()
    # kontrol: egen mappe er læs- og skrivbar, ellers beviser ovenstående intet
    assert koer("echo ok > egen.txt && cat egen.txt").stdout.strip() == "ok"
    assert (mit / "egen.txt").read_text().strip() == "ok"


def _bwrap(s, sok):
    """Det RIGTIGE sandbox-præfiks, kun med X-socket'en byttet ud med en stub."""
    a = xs.sandbox_args(s.workspace, s.display)
    ægte = "/tmp/.X11-unix/X" + s.display.lstrip(":")
    out = []
    i = 0
    while i < len(a):
        if a[i] == "--bind" and a[i + 1] == ægte:
            out += ["--bind", str(sok), ægte]
            i += 3
            continue
        out.append(a[i])
        i += 1
    return out


def test_f_ingen_global_singleton_fallback():
    assert not hasattr(xs, "shared_session")
    assert not hasattr(xs, "_singleton")
    for modul in ("apps.api.jarvis_api.routes.desktop_stream", "core.tools.desktop_tools"):
        kilde = inspect.getsource(__import__(modul, fromlist=["x"]))
        assert "shared_session" not in kilde
    kilde = inspect.getsource(xs.session_for)
    assert "XSession()" not in kilde  # ingen kontekstløs session


def test_f_ugyldig_rettighed_afvises(miljo):
    with pytest.raises(ValueError):
        xs.session_for("u-lotte", "admin")


def test_display_er_stabilt_og_ikke_delt(miljo):
    d1 = xs._tildel_display("member:x")
    assert xs._tildel_display("member:x") == d1
    assert xs._tildel_display("member:y") != d1


@pytest.mark.skipif(not BWRAP_OK, reason="bwrap ikke brugbar her")
def test_member_uden_bwrap_starter_ikke(miljo, monkeypatch):
    s = xs.session_for("u-lotte", "member")
    monkeypatch.setattr(xs.shutil, "which", lambda n: None)
    with pytest.raises(OSError):
        s._start_proc(["xterm"])
