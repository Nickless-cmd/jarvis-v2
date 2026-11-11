"""Én vækker: kilder SIGNALERER via gatewayen, indbakken VURDERER og vækker.

Bjørn 11/11-2026: «kun en vækker (inbox) og de andre sender signalet til
inbox'en, den vurderer signalet og vækker.»
"""
from __future__ import annotations

import ast
import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path

import pytest

from core.runtime import db_inbox

BRUGER = "bjorn"


@pytest.fixture
def inbox_db(monkeypatch, tmp_path):
    sti = tmp_path / "gw.db"

    @contextmanager
    def _connect():
        k = sqlite3.connect(sti)
        k.row_factory = sqlite3.Row
        try:
            yield k
            k.commit()
        finally:
            k.close()

    monkeypatch.setattr(db_inbox, "connect", _connect)
    monkeypatch.setattr(db_inbox, "_skema_klar", False)
    return sti


@pytest.fixture
def waker(monkeypatch):
    """Waker med en optaget-tæller i stedet for et rigtigt run."""
    from core.services import inbox_idle_waker as w

    starter: list[dict] = []
    monkeypatch.setattr(w, "_maal_session", lambda post: "chat-1")
    monkeypatch.setattr(w, "_session_er_aktiv", lambda session_id: False)
    monkeypatch.setattr(w, "_noget_koerer", lambda: False)
    monkeypatch.setattr(
        w, "_start_run",
        lambda tekst, *, session_id, user_id, task_id="", permission_session="": starter.append(
            {"tekst": tekst, "session": session_id, "task_id": task_id,
             "permission_session": permission_session}) or True)
    w.starter = starter  # type: ignore[attr-defined]
    return w


def _anmod(**kw):
    from core.services.wake_gateway import anmod_om_vaekning

    kw.setdefault("kilde", "test-kilde")
    kw.setdefault("sag", "sag-1")
    kw.setdefault("tekst", "gør noget")
    kw.setdefault("bruger_id", BRUGER)
    return anmod_om_vaekning(**kw)


# ── gatewayen starter ikke selv et run ──────────────────────────────────────

def test_gateway_lægger_post_og_starter_intet(inbox_db, monkeypatch):
    import core.services.visible_autonomous_run as var

    def _forbudt(*a, **k):
        raise AssertionError("gatewayen må ikke starte et run")

    monkeypatch.setattr(var, "start_autonomous_run", _forbudt)
    kv = _anmod()
    assert kv["status"] == "queued", kv
    post = db_inbox.hent(bruger_id=BRUGER, kilde_id=kv["kilde_id"])
    assert post and post["kildetype"] == "vaekning"
    assert post["verificeret_ejer"] == db_inbox.EJER_JARVIS
    assert post["kraever_handling"] is False  # må aldrig gate en mutation


def test_to_kilder_samme_sag_giver_en_vaekning(inbox_db, waker):
    a = _anmod(kilde="scheduled", sag="paamind-42")
    b = _anmod(kilde="heartbeat", sag="paamind-42")
    assert (a["status"], b["status"]) == ("queued", "deduped"), (a, b)
    assert waker.vaek_paa_aabne_poster(bruger_id=BRUGER)["vaekket"] == 1
    assert len(waker.starter) == 1
    # Næste runde: allerede vækket, ingen ny.
    assert waker.vaek_paa_aabne_poster(bruger_id=BRUGER)["vaekket"] == 0
    assert len(waker.starter) == 1


def test_waker_bruger_kildens_tekst_og_samtale(inbox_db, waker):
    _anmod(tekst="TJEK DEPLOY")
    waker.vaek_paa_aabne_poster(bruger_id=BRUGER)
    assert waker.starter == [{
        "tekst": "TJEK DEPLOY", "session": "chat-1",
        "task_id": "", "permission_session": "",
    }]


def test_opgave_og_permissionssamtale_naar_hele_vejen_til_starteren(inbox_db, waker):
    """En migreret vækningskilde må ikke tabe det den bærer i dag.

    `wakeup_dispatcher` gav før `task_id` (hvilken forpligtelse vækningen
    fortsætter) og `permission_session` (hvor adgangsniveauet skal læses) til
    starteren. Flyttes vækningen gennem indbakken, skal begge felter overleve
    turen — ellers starter runnet uden bånd til opgaven og arver tilladelsen
    fra den silo det lander i. Tabet ville være usynligt: runnet starter jo.
    """
    _anmod(tekst="fortsæt opgaven", task_id="opg-7",
           permission_session="chat-booket")
    waker.vaek_paa_aabne_poster(bruger_id=BRUGER)
    assert waker.starter == [{
        "tekst": "fortsæt opgaven", "session": "chat-1",
        "task_id": "opg-7", "permission_session": "chat-booket",
    }]


# ── indbakkens vurdering gælder stadig ──────────────────────────────────────

def test_post_der_ikke_kraever_handling_vaekker_ikke(inbox_db, waker):
    db_inbox.opret_eller_hent(
        bruger_id=BRUGER, kildetype="info", kilde_id="i-1",
        verificeret_ejer=db_inbox.EJER_JARVIS, kraever_handling=False,
        beskrivelse="bare info")
    assert waker.kandidater(BRUGER) == []
    assert waker.vaek_paa_aabne_poster(bruger_id=BRUGER)["vaekket"] == 0
    assert waker.starter == []


def test_post_uden_verificeret_ejer_vaekker_ikke(inbox_db, waker):
    db_inbox.opret_eller_hent(
        bruger_id=BRUGER, kildetype="vaekning", kilde_id="vaek-ukendt",
        verificeret_ejer=db_inbox.EJER_UKENDT, kraever_handling=False,
        beskrivelse="hvem er jeg")
    assert waker.kandidater(BRUGER) == []
    assert waker.vaek_paa_aabne_poster(bruger_id=BRUGER)["vaekket"] == 0
    assert waker.starter == []


def test_vaekning_sker_ikke_mens_et_run_er_aktivt(inbox_db, waker, monkeypatch):
    _anmod()
    monkeypatch.setattr(waker, "_noget_koerer", lambda: True)
    res = waker.vaek_paa_aabne_poster(bruger_id=BRUGER)
    assert res["vaekket"] == 0 and res["aarsag"] == "aktivt_run"
    assert waker.starter == []
    # ... og aktiv MÅL-session blokerer også, uden at posten brændes af.
    monkeypatch.setattr(waker, "_noget_koerer", lambda: False)
    monkeypatch.setattr(waker, "_session_er_aktiv", lambda s: True)
    assert waker.vaek_paa_aabne_poster(bruger_id=BRUGER)["vaekket"] == 0
    assert waker.starter == []
    monkeypatch.setattr(waker, "_session_er_aktiv", lambda s: False)
    assert waker.vaek_paa_aabne_poster(bruger_id=BRUGER)["vaekket"] == 1


# ── self-safe og SYNLIG ─────────────────────────────────────────────────────

def test_gateway_fejl_vaelter_ikke_kalderen_og_logges(inbox_db, monkeypatch, caplog):
    def _brud(**k):
        raise RuntimeError("db nede")

    monkeypatch.setattr(db_inbox, "hent", _brud)
    with caplog.at_level(logging.WARNING, logger="core.services.wake_gateway"):
        kv = _anmod()
    assert kv["status"] == "rejected" and "gateway_fejl" in kv["grund"], kv
    assert any("db nede" in r.getMessage() for r in caplog.records)


@pytest.mark.parametrize("felt,grund", [
    ({"kilde": ""}, "mangler_kilde"),
    ({"sag": "  "}, "mangler_sag"),
    ({"tekst": ""}, "mangler_tekst"),
])
def test_afviser_med_grund(inbox_db, felt, grund):
    kv = _anmod(**felt)
    assert kv["status"] == "rejected" and kv["grund"] == grund, kv


# ── vagten: der findes kun ÉN vej til et run ────────────────────────────────

REPO = Path(__file__).resolve().parents[1]
STARTERE = {"start_autonomous_run", "start_autonomous_stream_run"}

#: Filer der må NÆVNE en run-starter. Hver har en kategori:
#:   infra   — definerer/re-eksporterer starteren
#:   waker   — den ENESTE vækker (indbakken)
#:   kanal   — svar på et menneskes besked (ikke en vækning)
#:   gaeld   — en rigtig vækning der endnu kalder direkte og SKAL migreres
#: Listen må kun blive kortere. Et nyt kaldested uden om gatewayen fejler her.
TILLADT: dict[str, str] = {
    "core/services/visible_autonomous_run.py": "infra",
    "core/services/autonomous_stream_run.py": "infra",
    "core/services/visible_runs.py": "infra",
    "core/services/inbox_idle_waker.py": "waker",
    "core/services/discord_gateway.py": "kanal",
    "core/services/telegram_gateway.py": "kanal",
    "apps/api/jarvis_api/routes/plugins.py": "kanal",
    "core/services/scheduled_tasks.py": "gaeld",
    "core/services/recurring_tasks.py": "gaeld",
    "core/services/dreaming_session.py": "gaeld",
    "core/services/routine_trigger_adapters.py": "gaeld",
    "core/services/routine_dispatch.py": "gaeld",
    "core/services/autonomous_side_task_dispatcher.py": "gaeld",
    "core/services/session_spawn.py": "gaeld",
    "core/services/visible_runs_memory.py": "gaeld",
    "apps/api/jarvis_api/routes/jarvisx_processes.py": "gaeld",
}


def _filer_der_naevner_en_starter() -> set[str]:
    fundet: set[str] = set()
    for rod in ("core", "apps"):
        for sti in (REPO / rod).rglob("*.py"):
            try:
                træ = ast.parse(sti.read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeDecodeError):
                continue
            for node in ast.walk(træ):
                navn = None
                if isinstance(node, ast.Name):
                    navn = node.id
                elif isinstance(node, ast.Attribute):
                    navn = node.attr
                elif isinstance(node, ast.alias):
                    navn = node.name
                if navn in STARTERE:
                    fundet.add(sti.relative_to(REPO).as_posix())
                    break
    return fundet


def test_ingen_nye_kaldesteder_uden_om_gatewayen():
    ukendte = _filer_der_naevner_en_starter() - set(TILLADT)
    assert not ukendte, (
        f"Nyt kaldested for en run-starter: {sorted(ukendte)}. Vækninger skal "
        "gå via core.services.wake_gateway.anmod_om_vaekning — kun "
        "inbox_idle_waker må starte et run. Er det et kanal-svar, tilføj det "
        "til TILLADT med kategori 'kanal' og en begrundelse i findings-filen."
    )


def test_tilladt_listen_er_ikke_forældet():
    """Migreres en kilde, skal den ud af listen — ellers er vagten løs."""
    forældede = {f for f, k in TILLADT.items() if k in ("gaeld", "kanal", "waker")} \
        - _filer_der_naevner_en_starter()
    assert not forældede, f"Fjern fra TILLADT (kalder ikke længere): {sorted(forældede)}"


def test_der_findes_kun_en_definition_af_nogen_taler_nu():
    """`_active_turn_blocks` defineres ÉT sted; alle andre importerer den."""
    defs = []
    for sti in (REPO / "core").rglob("*.py"):
        træ = ast.parse(sti.read_text(encoding="utf-8"))
        for node in ast.walk(træ):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                    and node.name == "_active_turn_blocks":
                defs.append(sti.relative_to(REPO).as_posix())
    assert defs == ["core/services/wakeup_dispatcher.py"], defs


def test_gatewayen_selv_naevner_aldrig_en_starter():
    fundet = _filer_der_naevner_en_starter()
    assert "core/services/wake_gateway.py" not in fundet
