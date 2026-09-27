"""Task 1 (memory repair 2026-09-04): brain ranking must not be hijacked by salience.

Root cause: `search_brain` recomputed effective salience inline WITHOUT the
importance ceiling that `compute_effective_salience` applies, so an entry with
17.794 bumps contributed 1.26 to a score whose cosine part maxes at 0.7 — the
same 11 entries won every query. Auto-inject bumped every turn, closing the loop.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import numpy as np
import pytest


@pytest.fixture
def brain(tmp_path, monkeypatch):
    from core.services import jarvis_brain

    monkeypatch.setattr(jarvis_brain, "_workspace_root", lambda: tmp_path / "ws")
    monkeypatch.setattr(jarvis_brain, "_state_root", lambda: tmp_path / "state")
    return jarvis_brain


def _unit(direction: int) -> np.ndarray:
    v = np.zeros(768, dtype=np.float32)
    v[direction] = 1.0
    return v


def _write(brain, *, title: str, vec: np.ndarray, bumps: int, importance: float) -> str:
    now = datetime.now(timezone.utc)
    with patch.object(brain, "_embed_text", return_value=vec):
        entry_id = brain.write_entry(
            kind="fakta", visibility="personal", domain="test",
            title=title, content=f"{title} content", importance=importance,
        )
        brain.embed_pending_entries()
    conn = brain.connect_index()
    try:
        conn.execute(
            "UPDATE brain_index SET salience_bumps = ?, last_used_at = ? WHERE id = ?",
            (bumps, now.isoformat(), entry_id),
        )
        conn.commit()
    finally:
        conn.close()
    return entry_id


def test_relevant_entry_beats_runaway_salience(brain):
    """A (cos≈0.9, 0 bumps) must outrank B (cos≈0.4, 20 000 bumps, importance 0.8)."""
    q = np.zeros(768, dtype=np.float32)
    q[0] = 0.9
    q[1] = 0.436  # cos(q, e1) ≈ 0.44, cos(q, e0) ≈ 0.9
    a = _write(brain, title="relevant", vec=_unit(0), bumps=0, importance=0.8)
    b = _write(brain, title="runaway", vec=_unit(1), bumps=20_000, importance=0.8)

    with patch.object(brain, "_embed_text", return_value=q):
        results = brain.search_brain(query_text="anything", limit=2, use_temporal_boost=False)

    assert [e.id for e in results] == [a, b]


def test_search_effective_salience_is_capped_by_importance(brain):
    """Even with absurd bumps the salience term can never exceed importance."""
    q = _unit(0)
    _write(brain, title="capped", vec=_unit(0), bumps=50_000, importance=0.3)
    with patch.object(brain, "_embed_text", return_value=q):
        scored = brain.search_brain_scored(query_text="x", limit=1, use_temporal_boost=False)
    score, _eid = scored[0]
    # cos = 1.0 → 0.7 ; salience ≤ 0.3 → 0.09 ; total ≤ 0.79
    assert score <= 0.79 + 1e-6


def test_bump_salience_at_most_once_per_interval(brain):
    entry_id = _write(brain, title="bumpy", vec=_unit(0), bumps=0, importance=0.8)
    now = datetime.now(timezone.utc)
    brain.bump_salience(entry_id, now=now)
    brain.bump_salience(entry_id, now=now + timedelta(minutes=5))
    e = brain.read_entry(entry_id)
    assert e.salience_bumps == 1
    assert e.recall_count == 2
    brain.bump_salience(entry_id, now=now + timedelta(hours=25))
    assert brain.read_entry(entry_id).salience_bumps == 2


def test_tool_search_passes_cosine_floor(brain):
    from core.tools import jarvis_brain_tools

    captured: dict = {}

    def fake_search(**kwargs):
        captured.update(kwargs)
        return []

    with patch.object(brain, "search_brain", side_effect=fake_search):
        jarvis_brain_tools.search_jarvis_brain(query="pfsense nøgle", limit=5)
    assert captured.get("min_cosine") == pytest.approx(0.5)


def test_auto_inject_does_not_bump(brain):
    from unittest.mock import MagicMock

    from core.services.prompt_sections import jarvis_brain_facts as jbf

    fact = MagicMock()
    fact.id = "brn_X"
    fact.title = "t"
    fact.content = "c"
    with patch.object(brain, "search_brain", return_value=[fact]), \
         patch.object(brain, "bump_salience") as bump:
        out = jbf.build_brain_facts_section(user_message="hvad ved du om pfsense", session_id="s")
    assert "t" in out
    bump.assert_not_called()


def test_reset_salience_bumps_caps_file_and_index(brain):
    from scripts.brain_salience_reset import reset_salience_bumps

    hot = _write(brain, title="hot", vec=_unit(0), bumps=17_794, importance=0.8)
    cold = _write(brain, title="cold", vec=_unit(1), bumps=3, importance=0.8)
    # Mirror the bumps into the file (the file is truth) so the reset has to rewrite both.
    for eid, bumps in ((hot, 17_794), (cold, 3)):
        e = brain.read_entry(eid)
        e.salience_bumps = bumps
        brain._atomic_write(brain._workspace_root() / brain._index_path_for(eid),
                            brain.render_entry_markdown(e))

    changed = reset_salience_bumps(cap=20)
    assert changed == 1
    assert brain.read_entry(hot).salience_bumps == 20
    assert brain.read_entry(cold).salience_bumps == 3
    conn = brain.connect_index()
    try:
        row = conn.execute("SELECT salience_bumps FROM brain_index WHERE id = ?", (hot,)).fetchone()
    finally:
        conn.close()
    assert row[0] == 20


# ── Temporal-boostens afskæring (27/9-2026) ─────────────────────────────


def _kant(brain, fra: str, til: str, conf: float) -> None:
    conn = brain.connect_index()
    try:
        conn.execute(
            "INSERT INTO brain_temporal_edges "
            "(from_id, to_id, relation_type, confidence, inferred_at) "
            "VALUES (?,?,?,?,?)",
            (fra, til, "combined", conf, datetime.now(timezone.utc).isoformat()))
        conn.commit()
    finally:
        conn.close()


def test_loftet_passer_til_boost_faktoren():
    """`_MAX_TEMPORAL_BOOST` er afskæringens hele grundlag. Hæves
    `boost_factor` i `_compute_search_temporal_boost` uden at loftet følger
    med, bliver afskæringen for stram og rangeringen ændrer sig STILLE —
    ingen test ville fejle, resultaterne ville bare blive lidt forkerte.
    """
    import inspect

    from core.services import jarvis_brain

    sig = inspect.signature(jarvis_brain._compute_search_temporal_boost)
    faktor = sig.parameters["boost_factor"].default
    assert jarvis_brain._MAX_TEMPORAL_BOOST >= faktor, (
        "loftet må aldrig være mindre end den faktor det skal dække")


def test_afskaeringen_giver_SAMME_raekkefoelge_som_uden(brain):
    """Det eksakte krav: boosten må kun springe kandidater over der beviseligt
    ikke kan nå top-K. Her har den dårligste post en kant med fuld confidence
    og skal stadig ende sidst, fordi afstanden er større end loftet.
    """
    q = _unit(0)
    a = _write(brain, title="taet paa", vec=_unit(0), bumps=0, importance=0.5)
    b = _write(brain, title="langt fra", vec=_unit(5), bumps=0, importance=0.5)
    _kant(brain, b, a, 0.98)          # fuld boost til den dårligste

    with patch.object(brain, "_embed_text", return_value=q):
        med = brain.search_brain(query_text="x", limit=2, use_temporal_boost=True)
        uden = brain.search_brain(query_text="x", limit=2, use_temporal_boost=False)

    assert [e.id for e in med] == [e.id for e in uden] == [a, b]


def test_en_kant_INDEN_FOR_loftet_flytter_stadig_rangeringen(brain):
    """Afskæringen må ikke blive en stille deaktivering af boosten. To poster
    tæt på hinanden: den bageste har en kant og skal overhale."""
    q = np.zeros(768, dtype=np.float32)
    q[0] = 1.0
    q[1] = 0.97                      # cos ≈ 0,72 mod 0,74 — indenfor loftet
    a = _write(brain, title="forrest", vec=_unit(0), bumps=0, importance=0.5)
    b = _write(brain, title="bagerst", vec=_unit(1), bumps=0, importance=0.5)
    # Kanten skal pege VÆK fra kandidatsættet. Forsøg ét lagde `b -> a`, og
    # da opslaget rammer BEGGE endepunkter fik a og b samme boost — så kunne
    # rækkefølgen slet ikke ændre sig, og testen målte ingenting.
    _kant(brain, b, "brn_findes-ikke", 0.98)

    with patch.object(brain, "_embed_text", return_value=q):
        uden = [e.id for e in brain.search_brain(query_text="x", limit=2,
                                                 use_temporal_boost=False)]
        med = [e.id for e in brain.search_brain(query_text="x", limit=2,
                                                use_temporal_boost=True)]
    assert uden[0] == a, "opsætningen virker ikke — a skal føre uden boost"
    assert med[0] == b, "boosten blev afskåret væk"


def test_boosten_slaas_kun_op_for_kandidater_der_kan_naa_top_k(brain, monkeypatch):
    """Før 27/9-2026 blev boosten slået op for ALLE kandidater — målt 13.534
    for at returnere fem, i en `IN (...)` med 27.068 parametre. Det var 426 af
    de 551 ms; selve vektor-matmul'en er 2,5 ms."""
    q = _unit(0)
    _write(brain, title="naer", vec=_unit(0), bumps=0, importance=0.5)
    for i in range(1, 8):
        _write(brain, title=f"fjern{i}", vec=_unit(10 + i), bumps=0, importance=0.5)

    set_ids: list[int] = []
    aegte = brain._compute_search_temporal_boost
    monkeypatch.setattr(brain, "_compute_search_temporal_boost",
                        lambda ids, **kw: set_ids.append(len(ids)) or aegte(ids, **kw))
    with patch.object(brain, "_embed_text", return_value=q):
        brain.search_brain(query_text="x", limit=1, use_temporal_boost=True)

    assert set_ids, "boosten blev slet ikke kaldt"
    assert set_ids[0] < 8, f"slog op for {set_ids[0]} af 8 kandidater"


def test_afskaeringen_maa_ikke_skaere_en_post_der_KAN_naa_op(brain):
    """Mutationstesten 27/9-2026 fandt hullet her: at vende `graense` fra
    minus til PLUS bestod alle de øvrige tests.

    Grunden var at de havde lige så mange poster som `limit`, så
    `len(scored) > limit` var falsk og afskæringen aldrig blev kørt. En vagt
    der ikke rammer den gren den bevogter måler ingenting.

    Her er der TRE poster og `limit=1`, så grenen køres. `b` ligger under `a`
    i grundscore, men inden for loftet, og har en kant — den skal vinde.
    Med et plus i stedet for et minus bliver `b` skåret væk og `a` vinder.
    """
    q = np.zeros(768, dtype=np.float32)
    q[0] = 1.0
    q[1] = 0.97                      # b ligger ~0,015 under a — indenfor loftet
    a = _write(brain, title="forrest", vec=_unit(0), bumps=0, importance=0.5)
    b = _write(brain, title="naest", vec=_unit(1), bumps=0, importance=0.5)
    _write(brain, title="langt vaek", vec=_unit(40), bumps=0, importance=0.5)
    _kant(brain, b, "brn_findes-ikke", 0.98)

    with patch.object(brain, "_embed_text", return_value=q):
        uden = [e.id for e in brain.search_brain(query_text="x", limit=1,
                                                 use_temporal_boost=False)]
        med = [e.id for e in brain.search_brain(query_text="x", limit=1,
                                                use_temporal_boost=True)]
    assert uden == [a], "opsaetningen virker ikke — a skal foere uden boost"
    assert med == [b], "afskaeringen skar en post vaek der kunne naa op"
