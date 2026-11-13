"""Emergence-detektoren — hvad der overlever, og hvad der skal nedgraderes.

13/11-2026: `detect_and_score_patterns` persisterede kandidater, men en række
hvis mønster holdt op med at generere en kandidat blev aldrig rørt. Den blev
stående som «upgraded» med frosset confidence, og fladen og initiativ-broen
blev ved med at læse den. Målt i den ægte base stod `capability_growth_procedures`
med conf=1.0 og «27 procedures indicate expanding stable capability», hvor de
27 rækker var en write-only bank uden hit.

Testene her rammer den grænse ændringen FAKTISK håndhæver: en række UDEN
kandidat nedgraderes, en række MED kandidat røres ikke.

13/11-2026 (senere): kilden til det falske mønster blev også rettet.
`_fetch_procedures_count` talte ALLE rækker i `cognitive_procedures` — 27
styk, alle «Sådan: <enkeltord>» med `hit_count=0`, og `hit_count` sættes kun af
`match_procedures_for_text`, som havde nul kaldere i hele træet. Tælleren
kræver nu målt brug eller en bevidst pinning.

Det der IKKE var rettet: at et absolut tal overhovedet bruges som udsagn om
vækst. Et stigende antal målte procedurer er stadig ikke en måling af at evnen
vokser — kun af at banken gør.

13/11-2026 (tredje runde): begge huller lukket.
* `procedures_prompt_section` er bankens LÆSER — `match_procedures_for_text`
  havde nul kaldere, så `hit_count` kunne per definition ikke stige, og
  kravet `hit_count > 0` var en betingelse intet kunne opfylde.
* Tælleren kræver nu også `created_at` inden for vinduet: et DELTA, ikke et
  niveau. Summary siger «N new procedures shown or pinned in the last W days»
  i stedet for «indicate expanding stable capability».
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.services import emergence as em


def _kandidat(key: str, *, ev: int = 5) -> em.EmergenceCandidate:
    return em.EmergenceCandidate(
        pattern_key=key,
        title=key.replace("_", " ").title(),
        summary="s",
        evidence_count=ev,
        base_confidence=0.5,
        competing_explanations=[],
        confounders=[],
    )


@pytest.fixture
def miljoe(monkeypatch):
    """Fanger persistering og læsning, så testen måler grænsen — ikke apophenia."""
    state: dict = {"skrevet": [], "laest": [], "persisteret": []}

    monkeypatch.setattr(
        em, "assess_pattern", lambda **k: {"confidence": 0.6, "status": "candidate"}
    )
    monkeypatch.setattr(em.event_bus, "publish", lambda *a, **k: None)
    monkeypatch.setattr(
        em,
        "_create_or_update_pattern",
        lambda **k: (state["skrevet"].append(k), k)[1],
    )

    def _list_patterns(*, status: str = "", limit: int = 120):
        state["laest"].append(status)
        return list(state["persisteret"]) if status == "upgraded" else []

    monkeypatch.setattr(em, "list_patterns", _list_patterns)
    return state


def test_en_upgraded_raekke_uden_kandidat_nedgraderes(miljoe, monkeypatch):
    """Kernen: en evidenskilde der holder op med at fyre må ikke blive ved at reklamere."""
    monkeypatch.setattr(em, "_detect_candidates", lambda **k: [_kandidat("stadig_aktiv")])
    miljoe["persisteret"] = [
        {
            "pattern_key": "doed_kilde",
            "title": "Død kilde",
            "summary": "s",
            "confidence": 1.0,
            "evidence_count": 27,
        }
    ]

    em.detect_and_score_patterns(window_days=21)

    ned = [k for k in miljoe["skrevet"] if k["pattern_key"] == "doed_kilde"]
    assert len(ned) == 1, miljoe["skrevet"]
    assert ned[0]["status"] == "downgraded"
    assert ned[0]["confidence"] <= 0.4, "en frosset conf=1.0 må ikke overleve"
    assert ned[0]["competing_explanations"] == ["evidence_no_longer_generates_candidate"]


def test_en_upgraded_raekke_MED_kandidat_roeres_ikke(miljoe, monkeypatch):
    """Modstykket: nedgraderingen må ikke ramme et mønster der faktisk fyrer."""
    monkeypatch.setattr(em, "_detect_candidates", lambda **k: [_kandidat("stadig_aktiv")])
    miljoe["persisteret"] = [
        {
            "pattern_key": "stadig_aktiv",
            "title": "Stadig aktiv",
            "summary": "s",
            "confidence": 0.98,
            "evidence_count": 140,
        }
    ]

    em.detect_and_score_patterns(window_days=21)

    ned = [
        k
        for k in miljoe["skrevet"]
        if k["pattern_key"] == "stadig_aktiv" and k["status"] == "downgraded"
    ]
    assert ned == [], "et aktivt mønster blev nedgraderet"


def test_nedgraderingen_bevarer_evidence_count(miljoe, monkeypatch):
    """Historikken skal blive stående — ellers kan nedgraderingen ikke efterprøves."""
    monkeypatch.setattr(em, "_detect_candidates", lambda **k: [])
    miljoe["persisteret"] = [
        {
            "pattern_key": "doed_kilde",
            "title": "Død kilde",
            "summary": "s",
            "confidence": 1.0,
            "evidence_count": 27,
        }
    ]

    em.detect_and_score_patterns(window_days=21)

    ned = [k for k in miljoe["skrevet"] if k["pattern_key"] == "doed_kilde"]
    assert ned[0]["evidence_count"] == 27


def test_kun_upgraded_raekker_gennemgaas(miljoe, monkeypatch):
    """Gennemgangen må ikke skrive i kandidat- og afviste rækker den ikke ejer."""
    monkeypatch.setattr(em, "_detect_candidates", lambda **k: [])

    em.detect_and_score_patterns(window_days=21)

    assert miljoe["laest"] == ["upgraded"], miljoe["laest"]


def test_kandidaterne_persisteres_stadig(miljoe, monkeypatch):
    """Stale-blokken ligger efter hovedløkken — den må ikke sluge den normale vej."""
    monkeypatch.setattr(em, "_detect_candidates", lambda **k: [_kandidat("stadig_aktiv")])

    ud = em.detect_and_score_patterns(window_days=21)

    assert len(ud) == 1
    assert any(
        k["pattern_key"] == "stadig_aktiv" and k["status"] == "candidate"
        for k in miljoe["skrevet"]
    )


# ── Tælleren: hvad der må tælles som evne ────────────────────────────────────


@pytest.fixture
def procedure_db(monkeypatch):
    """Ægte SQLite med den ægte tabel.

    En fake-forbindelse der returnerer de samme rækker uanset SQL kan ikke se
    forskel på «alle rækker» og «kun brugte rækker». Den ville måle sin egen
    mock i stedet for WHERE-grenen, og en grøn test ville ikke betyde noget.
    `created_at` er med, fordi tælleren nu også filtrerer på den.
    """
    import sqlite3

    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.execute(
        "CREATE TABLE cognitive_procedures "
        "(name TEXT, hit_count INTEGER, pinned INTEGER, deleted INTEGER, "
        " created_at TEXT)"
    )
    monkeypatch.setattr(em, "connect", lambda: db)
    return db


def _indsæt(db, *raekker, alder_dage: float = 0.0):
    """Indsæt rækker. `alder_dage` styrer `created_at`, så delta-grenen kan prøves."""
    ts = (datetime.now(UTC) - timedelta(days=alder_dage)).isoformat()
    db.executemany(
        "INSERT INTO cognitive_procedures VALUES (?, ?, ?, ?, ?)",
        [(n, h, p, d, ts) for (n, h, p, d) in raekker],
    )
    db.commit()


def test_ubrugte_procedurer_taeller_ikke_som_evne(procedure_db):
    """Den målte virkelighed 13/11: 27 rækker, nul læst, nul pinned."""
    _indsæt(procedure_db, *[(f"Sådan: ord{i}", 0, 0, 0) for i in range(27)])

    assert em._fetch_procedures_count() == 0


def test_brugte_og_pinnede_taeller_men_slettede_goer_ikke(procedure_db):
    _indsæt(
        procedure_db,
        ("brugt", 3, 0, 0),
        ("pinnet", 0, 1, 0),
        ("skrald", 0, 0, 0),
        ("slettet men brugt", 5, 0, 1),
    )

    assert em._fetch_procedures_count() == 2


def test_gamle_rutiner_er_ikke_vaekst(procedure_db):
    """Kernen i fix 3: et NIVEAU der har stået stille er ikke en ændring.

    Uden dette krav fyrede mønsteret på et lager fra uger tilbage, og ordet
    «growth» beskrev noget der ikke var sket i vinduet.
    """
    _indsæt(procedure_db, *[(f"gammel{i}", 1, 0, 0) for i in range(8)],
            alder_dage=90)

    assert em._fetch_procedures_count(window_days=21) == 0


def test_nye_rutiner_i_brug_taeller_som_vaekst(procedure_db):
    """Positiv kontrol: uden den kan den negative test ikke skelne «gammel»
    fra «ingen». Grænsen skal kunne passeres."""
    _indsæt(procedure_db, *[(f"ny{i}", 1, 0, 0) for i in range(5)])
    _indsæt(procedure_db, *[(f"gammel{i}", 1, 0, 0) for i in range(9)],
            alder_dage=90)

    assert em._fetch_procedures_count(window_days=21) == 5


def test_summary_paastaar_ikke_expanding(procedure_db, monkeypatch):
    """Ordvalget er påstanden. «expanding stable capability» om et niveau var
    en løgn; nu står der hvad der faktisk blev målt."""
    _indsæt(procedure_db, *[(f"ny{i}", 1, 0, 0) for i in range(5)])
    monkeypatch.setattr(em, "_fetch_recent_events", lambda **k: [])
    monkeypatch.setattr(em, "_fetch_decisions_count", lambda **k: 0)

    kandidater = em._detect_candidates(window_days=21)
    cap = [c for c in kandidater if c.pattern_key == "capability_growth_procedures"]

    assert cap, "positiv kontrol: kandidaten skal findes"
    assert "expanding" not in cap[0].summary
    assert "last 21 days" in cap[0].summary


def test_en_bank_uden_brug_foder_ingen_capability_kandidat(procedure_db, monkeypatch):
    """Mønsteret må ikke fyre på en write-only bank — det var den falske påstand."""
    _indsæt(procedure_db, *[(f"Sådan: ord{i}", 0, 0, 0) for i in range(27)])
    monkeypatch.setattr(em, "_fetch_recent_events", lambda **k: [])
    monkeypatch.setattr(em, "_fetch_decisions_count", lambda **k: 0)

    keys = {c.pattern_key for c in em._detect_candidates(window_days=21)}

    assert "capability_growth_procedures" not in keys


def test_en_bank_MED_brug_foder_kandidaten(procedure_db, monkeypatch):
    """Positiv kontrol: grenen skal kunne fyre, ellers beviser testen ovenfor intet."""
    _indsæt(procedure_db, *[(f"brugt{i}", 1, 0, 0) for i in range(5)])
    monkeypatch.setattr(em, "_fetch_recent_events", lambda **k: [])
    monkeypatch.setattr(em, "_fetch_decisions_count", lambda **k: 0)

    keys = {c.pattern_key for c in em._detect_candidates(window_days=21)}

    assert "capability_growth_procedures" in keys
