"""Telemetrien skal sige HVOR LÆNGE den har målt, ikke kun hvad den målte.

Maalt 10/11-2026, to fejl der tilsammen gjorde et 7-doegns-tal umuligt at stole
paa:

1. `_rotér` flyttede filen til `.1` og ÉN generation var alt. Ved den maalte
   skrivehastighed (4,19 MB/doegn) daekkede 8 MB kun 1,9 doegn — med `.1` i
   alt 4,7 doegn. Et «7-dages» tal fra telemetrien var i praksis 44 timer.
2. `build_cache_telemetry_surface` laeser kun de seneste 2 MB og rapporterede
   en procentsats UDEN at sige hvilket tidsrum den daekkede. «Hit 95,5 %» kunne
   derfor laeses som 7 dage, mens halen var 17,4 timer.

Et tal uden sit tidsrum er ikke et maal. Begge er rettet her, og begge har en
vagt der fejler hvis de kommer tilbage.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from core.services import cache_telemetry as ct


def _linje(ts: datetime, hit: int = 900, miss: int = 100, lane: str = "agentic_round") -> str:
    return json.dumps({
        "timestamp": ts.isoformat(), "lane": lane, "hit": hit, "miss": miss,
        "pct": round(100.0 * hit / (hit + miss), 1), "prefix_sha": "abc123",
        "tools_sha": "def456", "run_id": "r1", "round": 1,
    }) + "\n"


def _skriv_sti(tmp_path):
    return tmp_path / "logs" / "cache_telemetry.jsonl"


# ── rotation ──────────────────────────────────────────────────────────────

def test_rotationen_ruller_gennem_alle_generationer(tmp_path, monkeypatch):
    """`.3`→`.4`, `.2`→`.3`, `.1`→`.2`, fil→`.1`. Den ældste falder bort."""
    sti = _skriv_sti(tmp_path)
    sti.parent.mkdir(parents=True, exist_ok=True)
    sti.write_text("ny")
    for n in range(1, ct.ROTATION_GENERATIONER + 1):
        sti.with_suffix(sti.suffix + f".{n}").write_text(f"gen{n}")

    monkeypatch.setattr(ct, "LOG_MAKS_BYTES", 1)
    ct._rotér(sti)

    assert sti.with_suffix(sti.suffix + ".1").read_text() == "ny"
    assert sti.with_suffix(sti.suffix + ".2").read_text() == "gen1"
    assert sti.with_suffix(sti.suffix + ".3").read_text() == "gen2"
    assert sti.with_suffix(sti.suffix + ".4").read_text() == "gen3"
    # `gen4` er skubbet ud: der er intet `.5`, og det er meningen med loftet.
    assert not sti.with_suffix(sti.suffix + ".5").exists()


def test_roterer_ikke_under_loftet(tmp_path, monkeypatch):
    sti = _skriv_sti(tmp_path)
    sti.parent.mkdir(parents=True, exist_ok=True)
    sti.write_text("lille")
    monkeypatch.setattr(ct, "LOG_MAKS_BYTES", 10_000)
    ct._rotér(sti)
    assert sti.exists() and sti.read_text() == "lille"
    assert not sti.with_suffix(sti.suffix + ".1").exists()


def test_historikken_raekker_mindst_syv_doegn_ved_maalt_hastighed():
    """Loftet skal dimensioneres efter den MAALTE hastighed, ikke et gaet.

    Maalt 10/11-2026: 4,19 MB/doegn. Syv doegn kraever ~29,3 MB.
    """
    maalt_mb_pr_doegn = 4.19
    kapacitet_mb = ct.LOG_MAKS_BYTES * ct.ROTATION_GENERATIONER / 1024 / 1024
    doegn = kapacitet_mb / maalt_mb_pr_doegn
    assert doegn >= 7, (
        f"{kapacitet_mb:.1f} MB daekker kun {doegn:.1f} doegn ved den maalte "
        f"hastighed — et 7-doegns-tal ville vaere umuligt"
    )


# ── spænd ─────────────────────────────────────────────────────────────────

def test_spaendet_laeses_paa_tvaers_af_generationerne(tmp_path):
    """En procentsats fra ÉN fil er ikke en historik."""
    sti = _skriv_sti(tmp_path)
    sti.parent.mkdir(parents=True, exist_ok=True)
    nu = datetime.now(timezone.utc)
    # .1 = 3 dage gammel, hoved = nu
    sti.with_suffix(sti.suffix + ".1").write_text(
        _linje(nu - timedelta(days=3)) + _linje(nu - timedelta(days=2))
    )
    sti.write_text(_linje(nu - timedelta(hours=2)) + _linje(nu))

    s = ct.telemetri_spaend(sti=sti)

    assert s["generationer"] == 2
    assert s["timer"] == pytest.approx(72.0, abs=0.2)
    assert s["doegn"] == pytest.approx(3.0, abs=0.1)
    assert s["daekker_7_doegn"] is False


def test_spaendet_siger_til_naar_syv_doegn_ER_daekket(tmp_path):
    sti = _skriv_sti(tmp_path)
    sti.parent.mkdir(parents=True, exist_ok=True)
    nu = datetime.now(timezone.utc)
    sti.with_suffix(sti.suffix + ".4").write_text(_linje(nu - timedelta(days=8)))
    sti.write_text(_linje(nu))

    s = ct.telemetri_spaend(sti=sti)

    assert s["daekker_7_doegn"] is True
    assert s["doegn"] >= 7


def test_overfladen_siger_hvor_mange_timer_den_maalte(tmp_path, monkeypatch):
    """Kernen i fejlen: `hit_pct` uden `read_hours` kan laeses som 7 dage."""
    sti = _skriv_sti(tmp_path)
    sti.parent.mkdir(parents=True, exist_ok=True)
    nu = datetime.now(timezone.utc)
    sti.write_text(
        "".join(_linje(nu - timedelta(hours=6 - i)) for i in range(7))
    )
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))

    u = ct.build_cache_telemetry_surface()
    sig = u["signals"]

    assert sig["calls_read"] == 7
    assert sig["read_hours"] == pytest.approx(6.0, abs=0.2), (
        "overfladen rapporterede en procentsats uden det tidsrum den daekker"
    )
    assert sig["history_days"] is not None
    assert "timer" in u["summary"], "summary skal naevne tidsrummet, ikke kun procenten"
