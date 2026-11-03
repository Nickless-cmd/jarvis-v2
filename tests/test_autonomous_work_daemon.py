"""Tests for autonomous_work_daemon — kø-grænsen OG forbrugeren (3/11-2026).

Baggrund (målt): daemonen skrev forslag ind i `autonomous_work_log.json` ved
hvert ledigt tick. `_save` trimmer til `_LOG_MAX` (300), så gamle forslag blev
ikke afvist — de blev kastet væk ved rotation. Målt i den levende fil: 300
poster, ALLE `pending`, ældste 28/10. `resolve_proposal` findes og virker, men
kaldes kun manuelt, så der var ingen automatisk forbruger.

Målt om de 300: de var **7 unikke forslag**. 294 var det SAMME research-forslag
om `seed-616b2bc12b`, fil'et hvert 15. minut i seks dage — fordi
`_maybe_propose_research` tog `list_seeds(status="maturing")[:1]`, altså altid
det første element i en usorteret liste.

Vagterne her låser tre ting:
- produktionen standser når køen er fuld af ubehandlede forslag,
- forbrugeren lukker dubletter og døde grundlag med en begrundelse,
- planneren frigøres fra det fastlåste første seed.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.services import autonomous_work_daemon as aw


def _entry(
    i: int,
    *,
    status: str = "pending",
    dage: int = 0,
    typ: str = "research",
    details: dict | None = None,
) -> dict:
    at = (datetime.now(UTC) - timedelta(days=dage)).isoformat()
    return {
        "proposal_id": f"aw-test{i}",
        "at": at,
        "type": typ,
        "title": f"forslag {i}",
        "details": details if details is not None else {},
        "rationale": "",
        "status": status,
    }


@pytest.fixture
def fuld_koe(monkeypatch):
    """Log fyldt til loftet med ubehandlede forslag.

    `_grundlag_findes` stubbes til «lever» — ellers ville forbrugeren lukke dem
    (fixturen har ingen rigtige seeds), og testen ville måle forbrugeren i
    stedet for kø-gaten.
    """
    poster = [_entry(i, dage=6) for i in range(aw._LOG_MAX)]
    monkeypatch.setattr(aw, "_load", lambda: list(poster))
    monkeypatch.setattr(aw, "_save", lambda items: None)
    monkeypatch.setattr(aw, "_is_low_activity", lambda: (True, "stub-idle"))
    monkeypatch.setattr(aw, "_proposals_last_hour", lambda: 0)
    monkeypatch.setattr(aw, "_grundlag_findes", lambda e: (True, "stub"))
    monkeypatch.setattr(aw, "consume_proposals", lambda **k: {"closed": 0, "kept": 0})
    return poster


# ── Kø-grænsen ──────────────────────────────────────────────────────────────

def test_tick_standser_naar_koeen_er_fuld_og_uforbrugt(fuld_koe):
    """Ved fuld kø må ticken IKKE producere flere forslag.

    Uden denne grænse blev hvert nyt forslag skrevet ind og skubbede et gammelt
    ud — rotation der skjuler at intet bliver behandlet.
    """
    resultat = aw.tick()
    assert resultat["skipped"] is True
    assert resultat["reason"] == "queue-full-unconsumed"
    assert resultat["pending"] == aw._LOG_MAX


def test_tick_producerer_naar_der_er_plads(monkeypatch):
    """Under loftet skal den stadig producere — grænsen må ikke gøre den død."""
    poster = [_entry(i, status="completed") for i in range(5)]
    monkeypatch.setattr(aw, "_load", lambda: list(poster))
    monkeypatch.setattr(aw, "_save", lambda items: None)
    monkeypatch.setattr(aw, "_is_low_activity", lambda: (True, "stub-idle"))
    monkeypatch.setattr(aw, "_proposals_last_hour", lambda: 0)
    monkeypatch.setattr(aw, "_plan_once", lambda: ["aw-ny"])
    monkeypatch.setattr(aw, "consume_proposals", lambda **k: {"closed": 0, "kept": 0})

    resultat = aw.tick()
    assert resultat["skipped"] is False
    assert resultat["proposals_created"] == 1


def test_fuld_koe_rapporteres_som_fuld(fuld_koe):
    """Fladen skal sige at køen er fuld — ikke se som en travl kø."""
    overflade = aw.build_autonomous_work_surface()
    assert overflade["pending_count"] == aw._LOG_MAX
    tekst = overflade["summary"]
    assert "FULD" in tekst
    assert "6 dage" in tekst


def test_aendelig_koe_rapporterer_alder(monkeypatch):
    """Også en ikke-fuld kø skal vise hvor gammelt det ældste forslag er."""
    poster = [_entry(0, dage=3), _entry(1, dage=0)]
    monkeypatch.setattr(aw, "_load", lambda: list(poster))
    tekst = aw.build_autonomous_work_surface()["summary"]
    assert "2 afventende" in tekst
    assert "3 dage" in tekst


# ── Forbrugeren ─────────────────────────────────────────────────────────────

@pytest.fixture
def butik(monkeypatch):
    """En muterbar log + en stub-seed-butik. Returnerer (log, seeds)."""
    log: list[dict] = []
    seeds: list[dict] = [{"seed_id": "seed-levende", "status": "maturing", "spark": "x"}]

    def _load():
        return list(log)

    def _save(items):
        log.clear()
        log.extend(items)

    monkeypatch.setattr(aw, "_load", _load)
    monkeypatch.setattr(aw, "_save", _save)
    monkeypatch.setattr(
        "core.services.creative_instinct_daemon.list_seeds",
        lambda status=None: [s for s in seeds if status is None or s.get("status") == status],
    )
    return log, seeds


def test_forbruger_lukker_dubletter(butik):
    """294 identiske forslag om det samme seed er ÉT forslag, ikke 294.

    Målt i den levende log: 300 poster var 7 unikke. Dubletterne skal lukkes
    med en note der peger på repræsentanten — ikke bare forsvinde.
    """
    log, _ = butik
    for i in range(5):
        log.append(_entry(i, details={"seed_id": "seed-levende"}))

    res = aw.consume_proposals()

    assert res["duplicates"] == 4
    assert res["kept"] == 1
    levende = [e for e in log if e.get("status") == "pending"]
    assert len(levende) == 1
    assert levende[0]["proposal_id"] == "aw-test0"  # den ældste er repræsentanten
    lukket = [e for e in log if e.get("status") == "rejected"]
    assert len(lukket) == 4
    assert all("dublet af aw-test0" in e["resolution_note"] for e in lukket)


def test_forbruger_lukker_research_uden_seed(butik):
    """Et research-forslag uden seed_id kan ikke behandles — og skal lukkes."""
    log, _ = butik
    log.append(_entry(0, details={}))

    res = aw.consume_proposals()

    assert res["closed"] == 1
    assert log[0]["status"] == "rejected"
    assert "seed_id" in log[0]["resolution_note"]


def test_forbruger_lukker_research_paa_forsvundet_seed(butik):
    """Peger forslaget på et seed der ikke findes, er grundlaget væk."""
    log, _ = butik
    log.append(_entry(0, details={"seed_id": "seed-findes-ikke"}))

    res = aw.consume_proposals()

    assert res["closed"] == 1
    assert "findes ikke" in log[0]["resolution_note"]


def test_forbruger_lukker_research_paa_withered_seed(butik):
    """Et withered seed er ikke længere værd at undersøge."""
    log, seeds = butik
    seeds.append({"seed_id": "seed-doed", "status": "withered", "spark": "y"})
    log.append(_entry(0, details={"seed_id": "seed-doed"}))

    aw.consume_proposals()

    assert log[0]["status"] == "rejected"
    assert "withered" in log[0]["resolution_note"]


def test_forbruger_beholder_levende_research(butik):
    """Et forslag hvis grundlag stadig lever skal IKKE lukkes."""
    log, _ = butik
    log.append(_entry(0, details={"seed_id": "seed-levende"}))

    res = aw.consume_proposals()

    assert res["closed"] == 0
    assert res["kept"] == 1
    assert log[0]["status"] == "pending"


def test_forbruger_lukker_incubator_som_allerede_udfoert(butik):
    """`incubator_seed` er en KVITTERING: `ci_tick` køres FØR forslaget fil'es.

    Derfor var `pending` en løgn — arbejdet var allerede gjort da posten blev
    skrevet. Den skal lukkes som afvist-med-grund, ikke stå som ventende.
    """
    log, _ = butik
    log.append(_entry(0, typ="incubator_seed"))

    aw.consume_proposals()

    assert log[0]["status"] == "rejected"
    assert "udført ved oprettelsen" in log[0]["resolution_note"]


def test_forbruger_lukker_foraeldet_dagskonsolidering(butik):
    """En konsolidering for en dag der er passeret er ikke længere «i dag»."""
    log, _ = butik
    gammel = (datetime.now(UTC).date() - timedelta(days=6)).isoformat()
    log.append(_entry(0, typ="memory_consolidate", details={"date": gammel}))

    aw.consume_proposals()

    assert log[0]["status"] == "rejected"
    assert "dage tilbage" in log[0]["resolution_note"]


def test_forbruger_beholder_aktuel_dagskonsolidering(butik):
    """I går er stadig inden for grænsen — den skal blive stående."""
    log, _ = butik
    igaar = (datetime.now(UTC).date() - timedelta(days=1)).isoformat()
    log.append(_entry(0, typ="memory_consolidate", details={"date": igaar}))

    res = aw.consume_proposals()

    assert res["kept"] == 1
    assert log[0]["status"] == "pending"


def test_forbruger_koerer_foer_koe_gaten(monkeypatch, butik):
    """Køen må ikke kunne låse daemonen fast: forbrugeren tømmer FØR gaten.

    Uden dette ville 300 dubletter blokere produktionen for evigt — gaten så
    kun `pending_count` og vidste ikke at de var 7 unikke.
    """
    log, _ = butik
    for i in range(aw._LOG_MAX):
        log.append(_entry(i, dage=1, details={"seed_id": "seed-levende"}))

    monkeypatch.setattr(aw, "_is_low_activity", lambda: (True, "stub-idle"))
    monkeypatch.setattr(aw, "_proposals_last_hour", lambda: 0)
    monkeypatch.setattr(aw, "_plan_once", lambda: [])

    resultat = aw.tick()

    assert resultat["skipped"] is False
    assert resultat["consumed"]["closed"] == aw._LOG_MAX - 1
    assert sum(1 for e in log if e.get("status") == "pending") == 1


def test_forbruger_taaler_at_butikken_kaster(monkeypatch, butik):
    """Kan seed-butikken ikke læses, er grundlaget UBEKRÆFTET — ikke dødt."""
    log, _ = butik
    log.append(_entry(0, details={"seed_id": "seed-levende"}))

    def _braek(status=None):
        raise RuntimeError("butik nede")

    monkeypatch.setattr("core.services.creative_instinct_daemon.list_seeds", _braek)

    res = aw.consume_proposals()

    assert res["kept"] == 1
    assert log[0]["status"] == "pending"


# ── Planneren ───────────────────────────────────────────────────────────────

def test_planner_springer_seed_over_der_allerede_venter(butik):
    """Samme seed må ikke få et nyt forslag hvert tick.

    Målt: 294 identiske forslag om `seed-616b2bc12b` over seks dage. Det var
    ikke iver — det var en planner der altid tog `maturing[:1]`.
    """
    log, seeds = butik
    seeds.append({"seed_id": "seed-anden", "status": "maturing", "spark": "z"})
    log.append(_entry(0, details={"seed_id": "seed-levende"}))

    nyt = aw._maybe_propose_research()

    assert nyt is not None
    fil = next(e for e in log if e["proposal_id"] == nyt)
    assert fil["details"]["seed_id"] == "seed-anden"  # den LEDIGE, ikke den optagede


def test_planner_tier_naar_alle_maturing_seeds_venter(butik):
    """Har alle maturing seeds et ventende forslag, er der intet at producere."""
    log, _ = butik
    log.append(_entry(0, details={"seed_id": "seed-levende"}))

    assert aw._maybe_propose_research() is None
    assert sum(1 for e in log if e.get("status") == "pending") == 1


# ── Fladen ──────────────────────────────────────────────────────────────────

def test_flade_skelner_unikke_fra_dubletter(butik):
    """300 ventende kan være 7 spørgsmål. Fladen skal vise begge tal."""
    log, _ = butik
    for i in range(10):
        log.append(_entry(i, details={"seed_id": "seed-levende"}))
    log.append(_entry(99, details={"seed_id": "seed-anden"}))

    overflade = aw.build_autonomous_work_surface()

    assert overflade["pending_count"] == 11
    assert overflade["pending_unique"] == 2
    assert "dubletter" in overflade["summary"]
