"""Sandkassen må ikke lukke hele brugeradskillelsen ind.

Målt 22/10-2026: `wrap_bwrap` bandt `~/.jarvis-v2` SKRIVBAR i sin helhed. Det
gjorde `workspaces/bjorn/MEMORY.md` og alle andre brugeres mapper læsbare OG
skrivbare for enhver indespærret kommando — uanset hvilken bruger der kørte
den. Sandkassen beskyttede resten af maskinen og lukkede samtidig den grænse
ind som hele multi-bruger-planen hviler på.

Testen måler argv'en: for en ren funktion er argv'en den ægte søm. En test der
grep'er efter `--tmpfs` i kilden ville være grøn selv om mountet lå det forkerte
sted — den fejlform er allerede betalt for én gang i denne uge.
"""
from __future__ import annotations

import pathlib

import pytest

from core.services import bash_sandbox as bs


@pytest.fixture()
def hjem(monkeypatch, tmp_path):
    """Et falsk runtime-hjem med to brugeres workspaces."""
    rod = tmp_path / "runtime"
    (rod / "workspaces" / "bjorn").mkdir(parents=True)
    (rod / "workspaces" / "lotte").mkdir(parents=True)
    (rod / "state").mkdir()
    monkeypatch.setattr(bs, "_runtime_hjem", lambda: str(rod))
    return rod


def _argv(cwd, **kw):
    return bs.wrap_bwrap("echo hej", str(cwd), **kw)


def test_uden_egen_workspace_bindes_hjemmet_som_foer(hjem, tmp_path):
    """Ejeren er upåvirket: adfærden skal være byte-identisk med før."""
    argv = _argv(tmp_path)
    par = list(zip(argv, argv[1:]))
    assert (str(hjem), str(hjem)) in par, "hjemmet blev ikke bundet"
    indeks = argv.index(str(hjem))
    assert argv[indeks - 1] == "--bind", (
        "ejerens hjem skal fortsat være skrivbart — ellers brækker eksisterende "
        "kommandoer der skriver til tilstand eller database"
    )


def test_egen_workspace_goer_hjemmet_read_only(hjem, tmp_path):
    """En medlems kommando må ikke kunne skrive i hjemmet."""
    argv = _argv(tmp_path, egen_workspace=str(hjem / "workspaces" / "lotte"))
    indeks = argv.index(str(hjem))
    assert argv[indeks - 1] == "--ro-bind", (
        "hjemmet blev bundet skrivbart for en medlem — så kan kommandoen "
        "ændre database og tilstand"
    )


def test_andre_brugeres_workspaces_er_usynlige(hjem, tmp_path):
    """Kernen: en tmpfs skal skygge workspaces/, så de ikke FINDES."""
    argv = _argv(tmp_path, egen_workspace=str(hjem / "workspaces" / "lotte"))
    ws_rod = str(hjem / "workspaces")

    par = list(zip(argv, argv[1:]))
    assert ws_rod in argv, (
        "workspaces/ blev ikke skygget — så er andre brugeres mapper stadig "
        "læsbare, og lækagen er ikke lukket"
    )
    indeks = argv.index(ws_rod)
    assert argv[indeks - 1] == "--tmpfs", (
        "workspaces/ blev bundet i stedet for skygget — en bind oven på det "
        "eksisterende mount skjuler intet"
    )
    assert (ws_rod, ws_rod) not in par, (
        "workspaces/ blev bundet til sig selv — så er tmpfs'en virkningsløs"
    )


def test_kun_egen_workspace_bindes_skrivbar(hjem, tmp_path):
    """Den ene mappe der SKAL være skrivbar, og ingen anden."""
    egen = str(hjem / "workspaces" / "lotte")
    argv = _argv(tmp_path, egen_workspace=egen)
    par = list(zip(argv, argv[1:]))

    assert (egen, egen) in par, "egen workspace blev ikke bundet skrivbar"
    indeks = argv.index(egen)
    assert argv[indeks - 1] == "--bind"

    andres = str(hjem / "workspaces" / "bjorn")
    assert andres not in argv, (
        "en anden brugers workspace optræder i argv'en — den skal være usynlig, "
        "ikke bare beskyttet"
    )


def test_enforcement_videresender_parameteren(hjem, tmp_path, monkeypatch):
    """Parameteren skal nå helt frem — ellers er fixen død kode."""
    monkeypatch.setattr(bs, "is_enabled", lambda: True)
    monkeypatch.setattr(bs, "kan_koere", lambda **_: (True, "proevet"))
    egen = str(hjem / "workspaces" / "lotte")

    e = bs.enforcement("echo hej", str(tmp_path), egen_workspace=egen)

    assert e.actual is True
    assert e.argv is not None
    assert egen in e.argv, "enforcement kastede parameteren væk på vejen"
    assert "--tmpfs" in e.argv
