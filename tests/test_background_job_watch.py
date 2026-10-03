"""Tester for baggrundsjob-vagtposten — hullet der blev lukket 3/10-2026.

Kernen er ikke at den kan læse en liste. Det er at den kan SKELNE mellem
«der var ingen nye» og «vi kunne ikke se» — for kun den ene må blive til en
besked til Bjørn. En vagt der siger «alt er fint» når broen tier er den
samme fejlklasse som `test_publish_scan` blev skrevet for at fange.
"""
from __future__ import annotations

from contextlib import contextmanager

import pytest

from core.services import background_job_watch as w


def _job(jid: str = "bg_aaaaaaaaaaaa", kode: int | None = 0,
         navn: str = "byg") -> dict:
    return {"id": jid, "kilde": "operator", "navn": navn, "exit_code": kode}


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


def test_kun_operator_kilden_taelles(isoleret_state, jobs):
    jobs["svar"] = {"jobs": [
        {"id": "sup-1", "kilde": "supervisor", "navn": "worker", "exit_code": 0},
        _job(),
    ]}
    nye = w.scan_finished(uid="bjorn")
    assert [j["id"] for j in nye] == ["bg_aaaaaaaaaaaa"]


def test_igangvaerende_job_er_ikke_fuldfoert(isoleret_state, jobs):
    """`exit_code is None` betyder «kører endnu», ikke «færdig uden fejl».
    Den forskel er hele grunden til at feltet er `None` og ikke `0`."""
    jobs["svar"] = {"jobs": [_job(kode=None)]}
    assert w.scan_finished(uid="bjorn") == []


def test_samme_job_siges_kun_en_gang(isoleret_state, jobs):
    jobs["svar"] = {"jobs": [_job()]}
    assert len(w.scan_finished(uid="bjorn")) == 1
    assert w.scan_finished(uid="bjorn") == []


def test_fejlet_job_rapporteres_med_koden(isoleret_state, jobs):
    jobs["svar"] = {"jobs": [_job(kode=2, navn="npm run build")]}
    nye = w.scan_finished(uid="bjorn")
    assert len(nye) == 1
    assert nye[0]["exit_code"] == 2


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

