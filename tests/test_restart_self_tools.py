"""`restart_self` — Jarvis' egen genstart, nu med et blik først.

## Målingen

13/9-2026: **syv** nedlukninger på 75 minutter, **fem** dræbte kørsler. To af
dem havde preview'et «Forsæt» — altså den besked Bjørn skriver *når* en kørsel
er død.

Både denne vej og de manuelle ssh-genstarter spurgte ikke først. Jeg byggede et
script til min egen side; det her er den anden.

## Hvorfor den ikke bare nægter

En genstart der bare afviser ville blive omgået ad en anden vej, og så er vi
værre stillet. Værktøjet svarer i stedet med *hvad* der kører, så Jarvis selv
kan vælge at vente — og `force=true` er der, med prisen skrevet i beskrivelsen.
"""
from __future__ import annotations

import core.tools.restart_self_tools as rst


def test_afviser_naar_noget_koerer(monkeypatch):
    monkeypatch.setattr(rst, "_aktive_koersler",
                        lambda *a, **k: [{"run_id": "visible-1", "preview": "Forsæt"}])
    ud = rst._exec_restart_self({"services": ["jarvis-api"]})
    assert ud["status"] == "afvist"
    assert ud["aktive"][0]["preview"] == "Forsæt"
    assert "force=true" in ud["raad"]


def test_raadet_siger_hvad_det_KOSTER():
    """En noedudgang uden pris bliver brugt af vane. Det gjorde jeg selv, faa
    minutter efter at have bygget den tilsvarende vagt til mit eget script."""
    import json
    kilde = json.dumps(rst.RESTART_SELF_TOOL_DEFINITIONS, ensure_ascii=False)
    assert "api-nedlukning" in kilde
    assert "Forsæt" in kilde


def test_force_gaar_udenom(monkeypatch):
    """Vagten maa kunne omgaas MED VILJE — ellers goer den en noedvendig
    genstart umulig."""
    monkeypatch.setattr(rst, "_aktive_koersler",
                        lambda *a, **k: [{"run_id": "x", "preview": "y"}])
    kaldt: list = []
    monkeypatch.setattr(rst.subprocess, "Popen",
                        lambda *a, **k: kaldt.append(a) or type("P", (), {"pid": 1})())
    ud = rst._exec_restart_self({"services": ["jarvis-api"], "force": True})
    assert ud["status"] != "afvist"
    assert kaldt, "genstarten blev ikke sat i gang"


def test_ingen_aktive_lader_den_koere(monkeypatch):
    monkeypatch.setattr(rst, "_aktive_koersler", lambda *a, **k: [])
    monkeypatch.setattr(rst.subprocess, "Popen",
                        lambda *a, **k: type("P", (), {"pid": 1})())
    ud = rst._exec_restart_self({"services": ["jarvis-api"]})
    assert ud["status"] != "afvist"


def test_ukendte_services_afvises_stadig():
    """Den eksisterende vagt maa ikke forsvinde under den nye."""
    ud = rst._exec_restart_self({"services": ["nginx"]})
    assert ud["status"] == "error"


class _FalskConn:
    """Minimal conn der svarer med faste raekker — ingen DB i spil."""

    def __init__(self, raekker):
        self._raekker = raekker

    def execute(self, *a, **k):
        self._sidste = a
        return self

    def fetchall(self):
        return self._raekker

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _med_raekker(monkeypatch, raekker, levende: set[str]):
    import core.runtime.db as db
    from core.services import visible_runs as vr
    monkeypatch.setattr(db, "connect", lambda: _FalskConn(raekker))
    monkeypatch.setattr(vr, "is_visible_run_alive", lambda rid: rid in levende)


def test_vagten_spoerger_HEARTBEATET_ikke_tabellen(monkeypatch):
    """Kernen (30/9-2026). `visible_runs.status` bliver staaende paa `running`
    indtil noget rydder den, og raekken har intet heartbeat. Kun
    `is_visible_run_alive` kan svare — den laeser `last_activity_at` fra den
    delte tilstand med en stale-taerskel paa 75 sekunder.

    Her stod foer et ALDERSLOFT paa én time. Det slap et run paa tre minutter
    igennem som «levende» mens heartbeatet sagde doed, og blokerede en
    noedvendig genstart. Samme dag stod en raekke `running` i 191 minutter uden
    ét spor i journalen.
    """
    _med_raekker(monkeypatch,
                 [("visible-lever", "et rigtigt svar"),
                  ("autonomous-zombie", "doed raekke")],
                 levende={"visible-lever"})
    aktive = rst._aktive_koersler()
    assert [a["run_id"] for a in aktive] == ["visible-lever"], aktive


def test_en_GAMMEL_men_levende_koersel_blokerer_stadig(monkeypatch):
    """Den anden retning, som alders-loftet fik forkert: et run der har koert
    laenge og STADIG lever, er praecis det vagten findes for. Et tidsloft ville
    have sluppet det forbi."""
    _med_raekker(monkeypatch,
                 [("visible-langt-run", "en lang agentisk tur")],
                 levende={"visible-langt-run"})
    assert len(rst._aktive_koersler()) == 1


def test_alle_doede_lader_genstarten_koere(monkeypatch):
    """Kontrollen. Uden den kunne testene ovenfor bestaa paa en vagt der
    altid blokerer — og en vagt der ikke kan tilfredsstilles bliver omgaaet."""
    _med_raekker(monkeypatch,
                 [("a", ""), ("b", ""), ("c", "")],
                 levende=set())
    assert rst._aktive_koersler() == []


def test_opslaget_kaster_aldrig(monkeypatch):
    """En vagt der blokerer paa sin EGEN fejl ville goere en noedvendig
    genstart umulig — vaerre end den fejl den beskytter mod."""
    import core.runtime.db as db
    monkeypatch.setattr(db, "connect",
                        lambda: (_ for _ in ()).throw(RuntimeError("nede")))
    assert rst._aktive_koersler() == []


def test_defer_until_idle_venter_paa_FAKTUM_ikke_paa_sekunder(monkeypatch):
    """Kernen (3/10-2026). Her laa en FAST `sleep 3`. Kaldes vaerktoejet midt i
    en tur, draeber de tre sekunder turen: runnet stemples `interrupted`,
    recovery-dispatcheren genoptager det senere — og Bjoern faar TO svar paa
    én besked (maalt kl. 15:43).

    Med `defer_until_idle` sendes runnets EGET id med, og genstarten venter paa
    et faktum — at runnet ikke laengere er i live — i stedet for et tal nogen
    skal ramme rigtigt. Jeg skrev systemd-timer-kommandoen i haanden tre gange
    paa én dag og ramte forkert én gang (60 s der naesten draebte turen).
    """
    monkeypatch.setattr(rst, "_aktive_koersler", lambda *a, **k: [])
    kaldt: list = []
    monkeypatch.setattr(rst.subprocess, "Popen",
                        lambda cmd, **k: kaldt.append(cmd)
                        or type("P", (), {"pid": 7})())
    from core.services import run_autonomy_context as rac
    monkeypatch.setattr(rac, "current_run_id", lambda: "visible-min-tur")

    ud = rst._exec_restart_self({"services": ["jarvis-api"], "defer_until_idle": True})

    assert ud["status"] == "ok" and ud["deferred"] is True
    assert ud["run_id"] == "visible-min-tur"
    assert kaldt, "den udskudte genstart blev ikke sat i gang"
    flad = " ".join(kaldt[0])
    assert "deferred_restart.py" in flad, kaldt[0]
    assert "visible-min-tur" in kaldt[0], (
        "runnets EGET id skal med — ellers ved scriptet ikke hvad det venter paa"
    )
    assert "sleep 3" not in flad, "den faste forsinkelse maa ikke overleve"


def test_uden_defer_bruges_den_gamle_vej(monkeypatch):
    """Kontrollen: den udskudte sti maa ikke stjaele den direkte. Uden flaget
    skal `sleep 3`-vejen stadig koere — ellers har jeg byttet én defekt ud med
    en anden."""
    monkeypatch.setattr(rst, "_aktive_koersler", lambda *a, **k: [])
    kaldt: list = []
    monkeypatch.setattr(rst.subprocess, "Popen",
                        lambda cmd, **k: kaldt.append(cmd)
                        or type("P", (), {"pid": 8})())
    ud = rst._exec_restart_self({"services": ["jarvis-api"]})
    assert ud.get("deferred") is not True
    assert "sleep 3" in " ".join(kaldt[0])
