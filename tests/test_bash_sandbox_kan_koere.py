"""«Findes» er ikke «virker» — sandkassens fem rapporterings-flader.

Maalt paa runtime 13/9-2026 under servicens egne betingelser:

    is_enabled()  : True
    is_available(): True
    faktisk bwrap-kald: bwrap: Unexpected capabilities but not setuid...  exit=1

`is_available()` er `shutil.which("bwrap") is not None`. Fem flader laeste det
som «sandkassen virker», og ingen af dem kunne se at hvert kald doede.
"""
from __future__ import annotations

import core.services.bash_sandbox as bs


def _braekket(monkeypatch):
    """bwrap findes, men naegter at starte — den faktiske produktionstilstand."""
    monkeypatch.setattr(bs, "is_available", lambda: True)
    monkeypatch.setattr(bs, "kan_koere", lambda **k: (
        False, "bwrap: Unexpected capabilities but not setuid, old file caps config?"))
    monkeypatch.setattr(bs, "is_enabled", lambda: True)


def test_status_siger_IKKE_aktiv_naar_bwrap_ikke_kan_starte(monkeypatch):
    """Den melding der lod fejlen staa: `aktiv: True` mens intet virkede."""
    _braekket(monkeypatch)
    s = bs.status()
    assert s["aktiv"] is False, "status meldte aktiv paa en bwrap der ikke kan starte"
    assert s["bwrap_findes"] is True and s["bwrap_kører"] is False
    assert "kan ikke starte" in s["note"]
    assert "Unexpected capabilities" in s["bwrap_grund"], \
        "grunden skal staa i klartekst — ellers leder nogen forkert sted"


def test_status_skelner_manglende_binaer_fra_braekket_binaer(monkeypatch):
    """To tilstande, to handlinger: installér bwrap, eller ret unit-filen."""
    monkeypatch.setattr(bs, "is_enabled", lambda: True)
    monkeypatch.setattr(bs, "is_available", lambda: False)
    monkeypatch.setattr(bs, "kan_koere", lambda **k: (False, "bwrap findes ikke paa PATH"))
    assert "findes ikke" in bs.status()["note"]


def test_status_er_aktiv_naar_bwrap_FAKTISK_koerer(monkeypatch):
    monkeypatch.setattr(bs, "is_enabled", lambda: True)
    monkeypatch.setattr(bs, "is_available", lambda: True)
    monkeypatch.setattr(bs, "kan_koere", lambda **k: (True, "proevet"))
    assert bs.status()["aktiv"] is True


def test_enforcement_rapporterer_IKKE_haandhaevelse_paa_braekket_bwrap(monkeypatch):
    """Fase 3 K9: «reports requested policy and actual enforcement».

    Mekanismen har vaeret her siden Fase 3 — den maalte bare et
    stedfortraeder-tal og meldte haandhaevelse paa en maskine hvor bwrap
    afviste hvert kald.
    """
    _braekket(monkeypatch)
    e = bs.enforcement("echo hej", "/tmp")
    assert e.requested is True, "oensket indespaerring skal stadig staa som oensket"
    assert e.actual is False, "K9's FAKTISK-side meldte haandhaevelse der ikke fandtes"
    assert e.honored is False
    # `available` BETYDER «findes bwrap her?» — og den GOER den. Feltet maa
    # ikke faa en ny betydning i smug; det er `actual` der skal vaere sand.
    assert e.available is True
    assert "kan ikke starte" in (e.reason or "")


def test_exec_stien_pakker_ikke_ind_naar_bwrap_ikke_kan_starte(monkeypatch):
    """Foer: kommandoen blev pakket ind og HVERT bash-kald doede.

    Fail-open er modulets egen dokumenterede adfaerd (`require=True` er den
    eneste vej til fail-closed), saa dette fjerner ingen beskyttelse der
    fandtes — det bytter «intet virker og intet er indespaerret» ud med «det
    virker, uindespaerret, og loggen siger det».
    """
    _braekket(monkeypatch)
    assert bs.maybe_wrap("echo hej", "/tmp") is None


def test_exec_stien_pakker_STADIG_ind_naar_bwrap_virker(monkeypatch):
    """Vagt mod at rettelsen slukker sandkassen for alle."""
    monkeypatch.setattr(bs, "is_enabled", lambda: True)
    monkeypatch.setattr(bs, "is_available", lambda: True)
    monkeypatch.setattr(bs, "kan_koere", lambda **k: (True, "proevet"))
    ud = bs.maybe_wrap("echo hej", "/tmp")
    assert ud is not None and "bwrap" in str(ud)


def test_kan_koere_caches(monkeypatch):
    """En exec pr. opslag er for dyrt — maaleren kaldes fra bogfoeringen."""
    bs._KAN_KOERE_CACHE = None
    kald = []
    ægte = __import__("subprocess").run

    def taeller(*a, **k):
        kald.append(1)
        return ægte(*a, **k)

    monkeypatch.setattr("subprocess.run", taeller)
    bs.kan_koere()
    bs.kan_koere()
    bs.kan_koere()
    assert len(kald) == 1, f"proevede {len(kald)} gange — cachen virker ikke"
    bs._KAN_KOERE_CACHE = None


def test_kan_koere_giver_grunden_med(monkeypatch):
    """En rapport uden grund sender nogen paa jagt i det forkerte lag."""
    bs._KAN_KOERE_CACHE = None

    class Svar:
        returncode = 1
        stderr = "bwrap: Unexpected capabilities but not setuid\n"
        stdout = ""

    monkeypatch.setattr("subprocess.run", lambda *a, **k: Svar())
    ok, grund = bs.kan_koere(tving=True)
    assert ok is False and "Unexpected capabilities" in grund
    bs._KAN_KOERE_CACHE = None
