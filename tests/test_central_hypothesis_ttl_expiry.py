"""TTL-udløb på hypoteser: døden skal SKRIVES, og udløbne må ikke bruges som aktive.

Målt 30/10-2026 i den levende base: 478 af 872 aktive hypoteser havde passeret deres
TTL (median afgørelsestid 3,57 t mod en frist på 168 t — fristen er altså ikke for
kort). De blev stadig hentet af `list_active_hypotheses()` (og kunne lande i Jarvis'
egen awareness-prompt) og stadig testet af sampler'en hvert 30. minut.

Årsagen er ikke en forkert TTL. Det er at `evaluate()` kun kaldes når et SAMPLE
ankommer — og en udløbet hypotese er netop den der ikke får samples. Dødsdommen
findes i governance (linje ~397), men der er ingen sweep der eksekverer den uden
et sample. Derfor denne fil.

Testene er adfærdstests mod en isoleret DB — ingen fake-forbindelse der svarer det
samme uanset forespørgslen (den ville aldrig kunne se et nyt WHERE-filter).
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from core.services import central_hypothesis_generator as gen
from core.services import central_hypothesis_sampler as sampler

_TTL = 168 * 3600  # 7 døgn — den værdi 137.175 af 137.217 rækker bærer


def _insert(hyp_id: str, *, age_hours: float, ttl_seconds: int = _TTL,
            mechanism: str = "causal_edges", family: str = "a->b") -> str:
    """Indsæt én hypotese med en BESTEMT alder, så TTL-grænsen kan rammes præcist."""
    from core.runtime.db import connect
    gen.ensure_schema()
    created = (datetime.now(timezone.utc) - timedelta(hours=age_hours)).isoformat()
    with connect() as c:
        c.execute(
            "INSERT INTO central_hypotheses (hyp_id, source, statement, prediction,"
            " null_hypothesis, success_criterion, sample_size, ttl_seconds, provenance_json,"
            " confidence, status, outcome, grounded_samples, created_at, resolved_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (hyp_id, "test", f"test-hypotese {hyp_id}", "p", "n", "s", 5, ttl_seconds,
             json.dumps({"mechanism": mechanism, "family": family, "cursor_id": "c1"}),
             0.3, "active", None, 0, created, None),
        )
        c.commit()
    return hyp_id


def _status(hyp_id: str) -> str | None:
    from core.runtime.db import connect
    with connect() as c:
        row = c.execute("SELECT status FROM central_hypotheses WHERE hyp_id=?",
                        (hyp_id,)).fetchone()
    return row["status"] if row else None


def _row(hyp_id: str) -> dict | None:
    from core.runtime.db import connect
    with connect() as c:
        row = c.execute("SELECT * FROM central_hypotheses WHERE hyp_id=?", (hyp_id,)).fetchone()
    return dict(row) if row else None


# ── 1. list_active_hypotheses må ikke levere udløbne ────────────────────────────────
def test_udloebet_hypotese_hentes_ikke_af_list_active(isolated_runtime):
    _insert("hyp-gammel", age_hours=24 * 30)
    ids = [h["hyp_id"] for h in gen.list_active_hypotheses(limit=50)]
    assert "hyp-gammel" not in ids


def test_frisk_hypotese_hentes_fortsat_af_list_active(isolated_runtime):
    _insert("hyp-frisk", age_hours=1)
    ids = [h["hyp_id"] for h in gen.list_active_hypotheses(limit=50)]
    assert "hyp-frisk" in ids


def test_list_active_limit_taeller_kun_levende(isolated_runtime):
    """LIMIT må ikke brænde pladser på udløbne — ellers skjuler de levende hinanden."""
    for i in range(3):
        _insert(f"hyp-dood-{i}", age_hours=24 * 60)
    _insert("hyp-levende", age_hours=2)
    active = gen.list_active_hypotheses(limit=1)
    assert len(active) == 1
    assert active[0]["hyp_id"] == "hyp-levende"


# ── 2. Sampler'en må ikke bruge kræfter på udløbne ──────────────────────────────────
def test_sampler_springer_udloebet_over(isolated_runtime, monkeypatch):
    _insert("hyp-gammel", age_hours=24 * 30)
    _insert("hyp-frisk", age_hours=1)
    tested: list[str] = []

    monkeypatch.setattr(
        sampler, "test_causal_hypothesis",
        lambda x, y, **kw: {"supports": True, "falsifies": False, "cursor": 7})
    monkeypatch.setattr(
        gen, "record_governed_sample",
        lambda hyp_id, **kw: (tested.append(hyp_id), {"status": "ok"})[1])

    sampler.run_hypothesis_sampler_tick()

    assert "hyp-frisk" in tested
    assert "hyp-gammel" not in tested


# ── 3. Sweep'en skriver døden — uden at slette eller falsificere ────────────────────
def test_sweep_markerer_udloebne_som_expired(isolated_runtime):
    _insert("hyp-gammel", age_hours=24 * 30)
    res = gen.expire_overdue_hypotheses()
    assert res["status"] == "ok"
    assert res["expired"] >= 1
    assert _status("hyp-gammel") == "expired"


def test_sweep_roerer_ikke_friske(isolated_runtime):
    _insert("hyp-frisk", age_hours=1)
    gen.expire_overdue_hypotheses()
    assert _status("hyp-frisk") == "active"


def test_sweep_bevarer_raekken_og_falsificerer_ikke(isolated_runtime):
    """Udløbet ≠ falsificeret. Rækken skal stå, og outcome må ikke sættes til 'falsified'."""
    _insert("hyp-gammel", age_hours=24 * 30)
    gen.expire_overdue_hypotheses()
    row = _row("hyp-gammel")
    assert row is not None, "rækken blev slettet — udløb er en tilstand, ikke en sletning"
    assert row["outcome"] != "falsified"
    assert row["statement"], "indholdet skal bevares"


def test_sweep_er_idempotent(isolated_runtime):
    _insert("hyp-gammel", age_hours=24 * 30)
    gen.expire_overdue_hypotheses()
    again = gen.expire_overdue_hypotheses()
    assert again["expired"] == 0, "en allerede udløbet hypotese tælles ikke igen"
    assert _status("hyp-gammel") == "expired"


def test_expired_hypotese_kan_faa_evidens_igen(isolated_runtime):
    """En udløbet hypotese er ikke død for evigt — nyt sample må genoplive den."""
    _insert("hyp-gammel", age_hours=24 * 30)
    gen.expire_overdue_hypotheses()
    assert _status("hyp-gammel") == "expired"
    res = gen.record_governed_sample(
        "hyp-gammel", supports=True, source="world_consequence",
        ground_ref="event-42", triggered_by="world")
    assert res.get("status") == "ok", f"sample blev afvist: {res}"
    assert _status("hyp-gammel") in {"active", "resolved"}, \
        "et nyt grounded sample skal genoplive eller afgøre hypotesen"


def test_genoplivet_hypotese_draebes_ikke_igen_af_naeste_sweep(isolated_runtime):
    """Ellers var genoplivningen meningsløs: sweep'en ville dræbe den igen med det samme.

    TTL måler tid UDEN ny evidens. Et sample oprettet efter fristen er netop den evidens,
    så sweep'en skal springe hypotesen over.
    """
    _insert("hyp-gammel", age_hours=24 * 30)
    gen.expire_overdue_hypotheses()
    gen.record_governed_sample(
        "hyp-gammel", supports=True, source="world_consequence",
        ground_ref="event-43", triggered_by="world")
    assert _status("hyp-gammel") in {"active", "resolved"}
    gen.expire_overdue_hypotheses()
    assert _status("hyp-gammel") in {"active", "resolved"}, \
        "sweep'en dræbte en hypotese der netop havde fået frisk evidens"
