"""Streaming-evnen skal MÅLES, ikke gættes.

MÅLT 20/11-2026: domænet «streaming og perceived performance» stod på 42 %
gennem 1.027 vektorer, sat af modellens eget skøn. `svar_tempo` målte TTFT
korrekt, men tallet gik kun i SSE-payloaden og blev aldrig gemt — så der
fandtes ingen historik at måle på.

Disse tests holder to ting fast: at målingen bliver gemt, og at måleren siger
«ikke målt» når der ikke er data nok — i stedet for at gætte.
"""
from __future__ import annotations

import pytest

from core.runtime import db_tempo
from core.services import streaming_capability as sc


def _seed_ttft(values: list[float]) -> None:
    for i, ms in enumerate(values):
        db_tempo.gem(f"r-{i}", ttft_ms=ms, tok_per_sek=20.0, output_tokens=100)


# ── Persistensen: tallet skal lande ──────────────────────────────────────────

def test_ttft_gemmes_og_laeses_tilbage(isolated_runtime):
    assert db_tempo.gem("run-a", ttft_ms=812.4, tok_per_sek=38.2, output_tokens=120)
    rows = db_tempo.seneste(limit=10)
    assert len(rows) == 1
    assert rows[0]["run_id"] == "run-a"
    assert rows[0]["ttft_ms"] == pytest.approx(812.4)
    assert rows[0]["tok_per_sek"] == pytest.approx(38.2)


def test_maalig_uden_ttft_gemmes_ikke(isolated_runtime):
    """`None` betyder «uret så intet token» — ikke «0 ms».

    Blev den gemt som nul, ville hver tur der døde undervejs trække medianen
    mod nul og få evnen til at se bedre ud end den er.
    """
    assert db_tempo.gem("run-doed", ttft_ms=None, tok_per_sek=None) is False
    assert db_tempo.seneste(limit=10) == []


def test_samme_run_taeller_kun_en_gang(isolated_runtime):
    """Begge SSE-veje (normal afslutning og gendannelse) kan aflæse samme run."""
    db_tempo.gem("run-d", ttft_ms=500.0, tok_per_sek=10.0)
    db_tempo.gem("run-d", ttft_ms=500.0, tok_per_sek=10.0)
    assert len(db_tempo.seneste(limit=10)) == 1


# ── Måleren: ingen data betyder «ikke målt» ──────────────────────────────────

def test_for_faa_maalinger_giver_ikke_et_tal(isolated_runtime):
    _seed_ttft([500.0] * 5)
    out = sc.measure(write=False)
    assert out["measured"] is False
    assert out["n"] == 5
    assert "required" in out


def test_ingen_maalinger_skriver_intet(isolated_runtime):
    out = sc.measure()
    assert out["measured"] is False
    assert out["written"] is None


# ── Måleren: tallet når det findes ───────────────────────────────────────────

def test_median_og_skala_paa_maalte_data(isolated_runtime):
    _seed_ttft([800.0] * 25)
    out = sc.measure(write=False)
    assert out["measured"] is True
    assert out["median_ttft_ms"] == pytest.approx(800.0)
    assert out["confidence"] == pytest.approx(0.90)


def test_langsom_streaming_saenker_confidence(isolated_runtime):
    _seed_ttft([9000.0] * 25)
    out = sc.measure(write=False)
    assert out["measured"] is True
    assert out["confidence"] == pytest.approx(0.30)


def test_p90_fanger_halen_som_medianen_skjuler(isolated_runtime):
    """Medianen kan se fin ud mens halen gør ondt — derfor rapporteres p90.

    Med ét enkelt outlier ud af 25 ville p90 med rette være 500: 24 af 25
    ligger under grænsen. Testen skal derfor have en hale der faktisk udgør
    ti procent, ellers måler den ingenting.
    """
    _seed_ttft([500.0] * 22 + [12000.0] * 3)
    out = sc.measure(write=False)
    assert out["median_ttft_ms"] == pytest.approx(500.0)
    assert out["p90_ttft_ms"] > 500.0


# ── Koblingen: målingen skal faktisk skrives ─────────────────────────────────

def test_maalingen_skrives_til_domaenet(isolated_runtime, monkeypatch):
    """En måler der ikke kalder skrive-stien er teater."""
    from core.services import capability_measurement

    kaldt: dict = {}

    def _fake(domain, value, *, evidence):
        kaldt.update({"domain": domain, "value": value, "evidence": evidence})
        return {"ok": True}

    monkeypatch.setattr(capability_measurement, "set_domain_confidence", _fake)
    _seed_ttft([700.0] * 25)

    out = sc.measure()
    assert kaldt["domain"] == sc.DOMAIN
    assert kaldt["value"] == pytest.approx(0.90)
    assert "median TTFT" in kaldt["evidence"]
    assert out["written"] == {"ok": True}


# ── Koblingen i SSE-stien: målingen skal nå basen ───────────────────────────

def test_sse_laes_tempo_gemmer_maalingen(isolated_runtime, monkeypatch):
    """`_laes_tempo` er den ENESTE søm begge SSE-veje går igennem.

    Målt 20/11-2026 gik tallet herfra og kun i payloaden. Testen beviser at
    det nu også lander i basen — uden den er hele måleren uden datakilde.
    """
    from core.services import svar_tempo, visible_runs_sse_v2 as sse

    svar_tempo.start("run-sse")
    svar_tempo.foerste_token("run-sse")

    tempo = sse._laes_tempo("run-sse", 50)
    assert tempo.get("ttft_ms") is not None, "uret gav ingen TTFT"

    rows = db_tempo.seneste(limit=5)
    assert [r["run_id"] for r in rows] == ["run-sse"]
    assert rows[0]["output_tokens"] == 50
