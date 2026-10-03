"""Tester for baggrundsjob-vagtposten — hullet der blev lukket 3/10-2026.

Kernen er ikke at den kan læse en liste. Det er to ting den skal kunne:

1. SKELNE mellem «der var ingen nye» og «vi kunne ikke se». En vagt der siger
   «alt er fint» når broen tier er den samme fejlklasse som
   `test_publish_scan` blev skrevet for at fange.
2. Skelne DELVIS blindhed fra total. Anden udgave (samme dag) fangede at
   første udgave kastede HELE listen naar broen tav — ogsaa supervisor-jobs,
   der ligger lokalt og er laesbare uden bro. Det er samme fejl spejlet: en
   flade der siger «intet» naar den godt kunne se noget.

Og grundlinjen: `process_supervisor`-registret er et arkiv uden oprydning.
Uden den ville foerste koersel melde en proces der doede i maj.
"""
from __future__ import annotations

from contextlib import contextmanager

import pytest

from core.services import background_job_watch as w

#: Foer/efter-grundlinje. Faste strenge, saa testen ikke afhaenger af hvornaar
#: den koerer — og saa de to skriveres uenige ISO-format (`Z` mod `+00:00`)
#: begge bliver rørt.
_GAMMEL = "2026-05-02T06:14:18.585536Z"      # foer grundlinjen
_GRUNDLINJE = "2026-10-03T10:00:00+00:00"
_NY = "2026-10-03T11:00:00Z"                  # efter grundlinjen


def _job(jid: str = "bg_aaaaaaaaaaaa", kode: int | None = 0,
         navn: str = "byg", kilde: str = "operator",
         stopped_at: str | None = None) -> dict:
    j = {"id": jid, "kilde": kilde, "navn": navn, "exit_code": kode}
    if stopped_at is not None:
        j["stopped_at"] = stopped_at
    return j


@pytest.fixture
def isoleret_state(monkeypatch):
    """state_store i hukommelsen. Filen er delt mellem to processer i drift;
    i testen ville den bare lække mellem kørsler."""
    from core.runtime import state_store

    gemt: dict = {}
    monkeypatch.setattr(state_store, "load_json", lambda n, d: gemt.get(n, d))
    monkeypatch.setattr(state_store, "save_json", lambda n, d: gemt.__setitem__(n, d))

    @contextmanager
    def _laas(_navn):
        yield

    monkeypatch.setattr(state_store, "med_laas", _laas)
    return gemt


@pytest.fixture
def fast_grundlinje(isoleret_state):
    """Grundlinjen sat til et fast tidspunkt, saa supervisor-testene kan
    afgoere foer/efter uden at vente paa uret."""
    isoleret_state[w._GRUNDLINJE] = {"foerste_ved": _GRUNDLINJE}
    return isoleret_state


@pytest.fixture
def jobs(monkeypatch):
    """Stub for `background_jobs.liste` — holder svar og kald i hånden."""
    kasse: dict = {"svar": {"jobs": [], "bridge_ok": True}, "kast": None, "kald": 0}
    from core.services import background_jobs

    def _liste(*, uid="", exec_fn=None, kun_aktive=True):
        kasse["kald"] += 1
        if kasse["kast"] is not None:
            raise kasse["kast"]
        return kasse["svar"]

    monkeypatch.setattr(background_jobs, "liste", _liste)
    return kasse


@pytest.fixture
def followups(monkeypatch):
    """Stub for trigger-køen. Returnerer listen af lagte beskeder."""
    lagt: list = []
    from core.runtime import heartbeat_triggers

    def _set(*, reason, source, text=""):
        lagt.append({"reason": reason, "source": source, "text": text})
        return {"created_at": "2026-10-03T13:00:00+00:00"}

    monkeypatch.setattr(heartbeat_triggers, "set_trigger_for_default_workspace", _set)
    return lagt


# ── scan_finished: hvad tæller som fuldført ─────────────────────────────


def test_operator_og_supervisor_taelles_shells_og_agenter_ikke(fast_grundlinje, jobs):
    """To kilder baerer et fuldfoerelses-bevis: operatoer-shells (`.rc`) og
    supervisor-processer (exit-kode + stop-tid). Aabne shell-sessioner og
    scout-agenter har ingen exit-kode at maale paa — de skal ikke taelles."""
    jobs["svar"] = {"jobs": [
        _job(jid="shell-1", kilde="shell"),
        _job(jid="agent-1", kilde="agent"),
        _job(jid="sup-1", kilde="supervisor", stopped_at=_NY),
        _job(jid="bg_aaaaaaaaaaaa"),
    ]}
    nye = w.scan_finished(uid="bjorn")["nye"]
    assert [j["id"] for j in nye] == ["sup-1", "bg_aaaaaaaaaaaa"]


def test_igangvaerende_job_er_ikke_fuldfoert(isoleret_state, jobs):
    """`exit_code is None` betyder «kører endnu», ikke «færdig uden fejl».
    Den forskel er hele grunden til at feltet er `None` og ikke `0`."""
    jobs["svar"] = {"jobs": [_job(kode=None)]}
    assert w.scan_finished(uid="bjorn")["nye"] == []


def test_samme_job_siges_kun_en_gang(isoleret_state, jobs):
    jobs["svar"] = {"jobs": [_job()]}
    assert len(w.scan_finished(uid="bjorn")["nye"]) == 1
    assert w.scan_finished(uid="bjorn")["nye"] == []


def test_fejlet_job_rapporteres_med_koden(isoleret_state, jobs):
    jobs["svar"] = {"jobs": [_job(kode=2, navn="npm run build")]}
    nye = w.scan_finished(uid="bjorn")["nye"]
    assert len(nye) == 1
    assert nye[0]["exit_code"] == 2


# ── grundlinjen: arkivet maa ikke meldes som nyheder ────────────────────
#
# `process_supervisor` rydder ikke sit register. Maalt 3/10-2026: ni poster,
# nyeste stop 16. september, to fra maj. Uden en grundlinje ville foerste
# koersel melde dem alle som om de lige var blevet faerdige.


def test_supervisor_post_fra_foer_grundlinjen_er_historik(fast_grundlinje, jobs):
    """Posten har en exit-kode og ser fuldfoert ud — men den stoppede for fem
    maaneder siden. Den er arkiv, ikke begivenhed."""
    jobs["svar"] = {"jobs": [
        _job(jid="gammel", kilde="supervisor", stopped_at=_GAMMEL),
    ]}
    assert w.scan_finished(uid="bjorn")["nye"] == []


def test_supervisor_post_efter_grundlinjen_meldes(fast_grundlinje, jobs):
    jobs["svar"] = {"jobs": [
        _job(jid="ny", kilde="supervisor", stopped_at=_NY),
    ]}
    assert [j["id"] for j in w.scan_finished(uid="bjorn")["nye"]] == ["ny"]


def test_supervisor_uden_stop_tid_springes_over(fast_grundlinje, jobs):
    """Kan posten ikke dateres, kan vi ikke afgoere om den er ny. Vi tier —
    en ufuldstaendig post maa ikke blive en falsk nyhed."""
    jobs["svar"] = {"jobs": [
        _job(jid="udateret", kilde="supervisor", stopped_at=None),
    ]}
    assert w.scan_finished(uid="bjorn")["nye"] == []


def test_genstartet_navn_med_nyt_stop_meldes_igen(fast_grundlinje, jobs):
    """Supervisor-NAVNE genbruges: `grid-bot` kan startes, do og startes igen.
    Noeglen baerer derfor ogsaa stop-tidspunktet — ellers ville anden doed
    blive laest som «allerede rapporteret»."""
    jobs["svar"] = {"jobs": [_job(jid="grid-bot", kilde="supervisor", stopped_at=_NY)]}
    assert len(w.scan_finished(uid="bjorn")["nye"]) == 1

    jobs["svar"] = {"jobs": [
        _job(jid="grid-bot", kilde="supervisor", stopped_at="2026-10-03T12:00:00Z"),
    ]}
    assert len(w.scan_finished(uid="bjorn")["nye"]) == 1, (
        "en ny doed for samme navn er en ny begivenhed"
    )


def test_grundlinjen_saettes_en_gang_og_bliver_staaende(fast_grundlinje):
    foer = w._grundlinje()
    assert foer.isoformat() == _GRUNDLINJE.replace("Z", "+00:00")
    assert w._grundlinje() == foer


# ── tik: beskeden må kun komme naar vi VED det ──────────────────────────


def test_fuldfoert_job_giver_en_followup(isoleret_state, jobs, followups):
    jobs["svar"] = {"jobs": [_job(navn="npm run build")]}
    ud = w.tik(uid="bjorn")
    assert ud["status"] == "ok" and ud["nye"] == 1
    assert len(followups) == 1
    assert followups[0]["reason"] == "background-job-done"
    assert "npm run build" in followups[0]["text"]
    assert "færdig" in followups[0]["text"]


def test_broen_der_tier_giver_ingen_besked(isoleret_state, jobs, followups):
    """Det afgørende: en død bro er ikke «der kørte ingenting». Vi ved det
    ikke — og så siger vi ingenting frem for at sige alt er fint."""
    jobs["kast"] = RuntimeError("bridge_not_connected")
    ud = w.tik(uid="bjorn")
    assert ud["status"] == "ukendt"
    assert followups == []


def test_bridge_ok_false_er_ogsaa_blindhed(isoleret_state, jobs, followups):
    """`liste()` er fail-soft: den sluger `BroTier` og saetter bridge_ok=False.
    Uden et tjek paa det felt ville en TOM liste fra en blind bro blive laest
    som «der koerte ingenting» — maalt 3/10-2026, hvor roegtesten gav praecis
    det svar (NO_BRIDGE, men status=ok)."""
    jobs["svar"] = {"jobs": [], "bridge_ok": False}
    ud = w.tik(uid="bjorn")
    assert ud["status"] == "ukendt"
    assert followups == []


def test_blind_bro_kaster_ikke_de_lokale_jobs(isoleret_state, jobs, followups):
    """Anden udgave, 3/10-2026. Foerste udgave kastede HELE listen naar broen
    tav — ogsaa supervisor-jobs, der ligger paa serveren og er laesbare uden
    bro. Det er samme fejl spejlet: «intet» naar vi godt kunne se noget.

    Den skal melde det den SAA, og sige at den ikke kunne se resten."""
    jobs["svar"] = {
        "jobs": [_job(jid="lokal", kilde="supervisor", stopped_at=_NY)],
        "bridge_ok": False,
    }
    fast = {"foerste_ved": _GAMMEL}
    isoleret_state[w._GRUNDLINJE] = fast

    ud = w.tik(uid="bjorn")
    assert ud["nye"] == 1, "den lokale fuldfoerelse maa ikke gaa tabt"
    assert ud["status"] == "ukendt", "men status er aerlig: vi kunne ikke se alt"
    assert len(followups) == 1
    assert "kunne ikke ses" in followups[0]["text"]


def test_throttle_springer_andet_kald_over(isoleret_state, jobs, followups):
    jobs["svar"] = {"jobs": [_job()]}
    assert w.tik(uid="bjorn")["status"] == "ok"
    andet = w.tik(uid="bjorn")
    assert andet["status"] == "skip" and andet["grund"] == "for-tidligt"


def test_trigger_der_returnerer_none_meldes_som_fejl(isoleret_state, jobs, monkeypatch):
    """`set_trigger_for_default_workspace` sluger sin egen fejl og giver
    None. Uden et tjek ville vi melde «sendt» om en besked der ikke findes —
    og jobbet er allerede markeret rapporteret."""
    from core.runtime import heartbeat_triggers
    monkeypatch.setattr(heartbeat_triggers, "set_trigger_for_default_workspace",
                        lambda **_: None)
    jobs["svar"] = {"jobs": [_job()]}
    ud = w.tik(uid="bjorn")
    assert ud["status"] == "fejl"
    assert ud["grund"] == "trigger-blev-ikke-lagt"


def test_uden_bruger_roerer_den_ikke_broen(isoleret_state, jobs, monkeypatch):
    """Uden en bruger er der ingen at maale for — og ingen at give besked.
    Vi maa ikke lave et bro-kald for at finde ud af det."""
    monkeypatch.setattr(w, "_bruger_id", lambda: "")
    ud = w.tik(uid="")
    assert ud["status"] == "skip"
    assert jobs["kald"] == 0


# ── beskrivelsen: mennesket skal kunne se HVAD der blev færdigt ─────────


def test_beskrivelsen_viser_navn_og_dom():
    assert "færdig" in w._beskriv(_job(navn="byg apk"))
    assert "FEJLEDE" in w._beskriv(_job(kode=1, navn="byg apk"))
    assert "byg apk" in w._beskriv(_job(navn="byg apk"))


def test_beskrivelsen_klipper_lange_kommandoer():
    lang = "x" * 400
    linje = w._beskriv(_job(navn=lang))
    assert len(linje) < 140


# ── hook-stedet: fejlen der gjorde den blind i drift ────────────────────
#
# 3/10-2026, maalt fire minutter efter commit: vagtposten laa i
# `tik_indre_daemoner` (de ubetingede daemoner), hvor `current_user_id()` er
# TOM uden for en request. Den svarede «ingen-bruger» hvert tik og gjorde
# intet — fuldfoerelses-signalet ligger paa operatoerens maskine, og
# bro-kaldet kraever et bruger-id. De to tests her pinner baade HVOR den
# kaldes og HVAD den faar med.


def test_vagtposten_ligger_i_per_bruger_konteksten(monkeypatch):
    """Den skal kaldes PER BRUGER, med id'et. Kilden er sandheden her, fordi
    fejlen netop var et spoergsmaal om HVOR kaldet stod — ikke om hvad det
    gjorde."""
    import inspect

    from core.services import heartbeat_daemon_ticks as hdt

    assert "background_job_watch" not in inspect.getsource(hdt.tik_indre_daemoner)
    assert "background_job_watch" in inspect.getsource(hdt._tik_for_bruger)


def test_hooket_sender_bruger_id_med(monkeypatch):
    """Uden id'et er bro-kaldet blindt: `user_id_mismatch`. Testen erstatter
    de tre andre per-bruger daemoner, saa den ene linje der betyder noget staar
    alene."""
    from core.services import heartbeat_daemon_ticks as hdt

    kaldt: list[str] = []
    monkeypatch.setattr(w, "tik", lambda *, uid="": (kaldt.append(uid), {"status": "ok"})[1])

    for navn in ("day_shape_memory", "relation_dynamics", "relational_warmth"):
        mod = __import__(f"core.services.{navn}", fromlist=["tick"])
        monkeypatch.setattr(mod, "tick", lambda *a, **k: None)

    hdt._tik_for_bruger("bjorn", "1246415163603816499")

    assert kaldt == ["1246415163603816499"], (
        "vagtposten skal have bruger-id'et med — ellers er bro-kaldet blindt"
    )
