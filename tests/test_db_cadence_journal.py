"""Kadence-beslutningsjournal: et FRAVALG skal efterlade samme spor som en kørsel.

Målt 4/11-2026: `run_cadence_tick` samlede alle beslutninger i
`_last_tick_results`, som overskrives ved næste tick. En producer der aldrig
blev kørt efterlod derfor kun et manglende claim — fordi `note_producer_ran`
kun skrives i succesgrenen. Spørgsmålet «hvorfor kørte den ikke?» var derfor
ubesvarligt med data og kun besvarligt med simulation.

Acceptance-kravet er derfor ikke «bliver en logfunktion kaldt», men:
**en producer der IKKE bliver kørt skal kunne genfindes med sin årsag efter at
processens hukommelse er væk.** Testen rydder både in-memory-tilstanden og
DB-forbindelsen mellem skrivning og læsning — en journal der kun lever i
processen ville bestå en naiv test og fejle her.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from core.runtime.db_cadence_journal import (
    prune_cadence_decisions,
    recent_cadence_decisions,
    record_cadence_decisions,
    reason_code_for,
)


def _isolate(tmp_path, monkeypatch):
    """Frisk DB + tom in-memory cadence-tilstand."""
    from core.runtime import db_core

    db_core.close_pooled_connection()
    monkeypatch.setattr(db_core, "DB_PATH", tmp_path / "cadence-journal.db")
    from core.runtime.db_schema import init_db

    init_db()

    from core.services import internal_cadence as cad

    monkeypatch.setattr(cad, "_producers", {})
    monkeypatch.setattr(cad, "_last_run_at", {})
    monkeypatch.setattr(cad, "_last_tick_results", [])
    return cad


def test_fravalg_overlever_at_proceshukommelsen_ryddes(tmp_path, monkeypatch):
    """En producer der ikke kørte skal kunne forklares EFTER en «genstart»."""
    cad = _isolate(tmp_path, monkeypatch)

    koert: list[int] = []
    cad.register_producer(cad.ProducerSpec(
        name="a_koerer",
        cooldown_minutes=60,
        visible_grace_minutes=0,
        run_fn=lambda **_: koert.append(1) or {"ok": True},
        priority=1,
    ))
    cad.register_producer(cad.ProducerSpec(
        name="b_graced",
        cooldown_minutes=60,
        visible_grace_minutes=60,
        run_fn=lambda **_: {"ok": True},
        priority=2,
    ))

    nu = datetime.now(UTC)
    cad.run_cadence_tick(trigger="test", last_visible_at_iso=nu.isoformat())
    assert koert == [1], "testopsætningen er forkert: den kørbare producer kørte ikke"

    # Ryd proceshukommelsen — det er præcis hvad en genstart gør.
    from core.runtime import db_core

    cad._last_tick_results.clear()
    cad._last_run_at.clear()
    db_core.close_pooled_connection()
    for navn in ("a_koerer", "b_graced"):
        cad._stop_worker(navn)

    rows = {r["producer"]: r for r in recent_cadence_decisions(limit=50)}

    assert "a_koerer" in rows, "den kørte producer efterlod intet spor"
    assert rows["a_koerer"]["status"] == "ran"
    assert rows["a_koerer"]["reason_code"] == "dispatched"

    assert "b_graced" in rows, (
        "en producer der IKKE blev kørt efterlod intet beslutningsspor — så kan "
        "«hvorfor kørte den ikke?» ikke besvares efter en genstart"
    )
    assert rows["b_graced"]["status"] == "visible_grace"
    assert rows["b_graced"]["reason_code"] == "visible-grace"
    assert rows["b_graced"]["last_visible_at"], (
        "journalen gemte ikke den aktivitetstid grace-dommen blev truffet på"
    )
    assert rows["b_graced"]["dispatch_budget"] == cad._MAX_DISPATCHES_PER_TICK


def test_gentagne_fravalg_komprimeres_men_overgangen_bevares(tmp_path, monkeypatch):
    """121 producers × ticks må ikke blive 121 nye rækker pr. tick."""
    _isolate(tmp_path, monkeypatch)
    nu = datetime.now(UTC)

    # `reason` er formateret med tal der ændrer sig hvert tick. Komprimeringen
    # skal ramme alligevel — derfor er nøglen en stabil årsags-kode.
    for i in range(5):
        record_cadence_decisions(
            [{
                "producer": "p",
                "status": "cooling_down",
                "reason": f"cooldown:{i}m<60m",
            }],
            tick_id=f"t{i}",
            dispatch_budget=12,
            now=nu,
        )

    aabne = [r for r in recent_cadence_decisions(producer="p") if not r["closed_at"]]
    assert len(aabne) == 1, (
        f"hvert tick skrev sin egen række ({len(aabne)}) — tabellen vokser pr. "
        "tick i stedet for pr. tilstandsskift"
    )
    assert aabne[0]["occurrences"] == 5
    assert aabne[0]["reason_code"] == "cooldown"
    assert aabne[0]["reason_detail"] == "cooldown:4m<60m", (
        "detaljen skal være det nyeste øjebliksbillede, ikke det første"
    )

    # Tilstandsskift: den gamle post lukkes, en ny åbnes.
    record_cadence_decisions(
        [{
            "producer": "p",
            "status": "visible_grace",
            "reason": "visible-too-recent:3m<60m",
        }],
        tick_id="t5",
        dispatch_budget=12,
        now=nu,
    )

    alle = recent_cadence_decisions(producer="p")
    assert len(alle) == 2, "overgangen blev ikke bevaret som sin egen række"
    aabne = [r for r in alle if not r["closed_at"]]
    assert len(aabne) == 1 and aabne[0]["status"] == "visible_grace"


def test_retention_sletter_lukkede_men_aldrig_aabne(tmp_path, monkeypatch):
    """En åben post beskriver en tilstand der STADIG gælder — den er fredet."""
    _isolate(tmp_path, monkeypatch)
    gammel = datetime.now(UTC) - timedelta(days=90)

    # Tre skift → to lukkede poster og én åben, alle 90 dage gamle.
    for i, status in enumerate(("cooling_down", "ran", "cooling_down")):
        record_cadence_decisions(
            [{"producer": "skiftende", "status": status, "reason": "cooldown:1m<60m"}],
            tick_id=f"t{i}",
            now=gammel + timedelta(minutes=i),
        )

    # En producer der aldrig kom videre: stadig åben, lige så gammel.
    record_cadence_decisions(
        [{"producer": "fastlaast", "status": "deferred", "reason": "tick-dispatch-budget"}],
        tick_id="t9",
        now=gammel,
    )

    ud = prune_cadence_decisions(retention_days=30)
    assert ud["expired"] == 2, f"forventede 2 udløbne lukkede poster, fik {ud}"

    tilbage = recent_cadence_decisions(producer="skiftende")
    assert len(tilbage) == 1 and tilbage[0]["closed_at"] == ""

    assert len(recent_cadence_decisions(producer="fastlaast")) == 1, (
        "retention slettede en ÅBEN post — så kan spørgsmålet om en producer der "
        "stadig ikke kører ikke besvares"
    )


def test_reason_code_er_stabil_naar_detaljen_aendrer_sig():
    """Årsags-koden er kategorien; detaljen er øjebliksbilledet."""
    a = reason_code_for(status="cooling_down", reason="cooldown:2m<60m")
    b = reason_code_for(status="cooling_down", reason="cooldown:59m<60m")
    assert a == b == "cooldown"

    assert reason_code_for(status="deferred", reason="tick-dispatch-budget") == (
        "dispatch-budget"
    )
    assert reason_code_for(status="visible_grace", reason="visible-too-recent:3m<60m") == (
        "visible-grace"
    )
    assert reason_code_for(status="blocked", reason="dependency-not-met:x") == (
        "dependency-not-met"
    )
    assert reason_code_for(status="ran", reason="cadence-dispatched") == "dispatched"


def test_connect_er_ikke_bundet_paa_modul_niveau():
    """VAGT (4/11-2026): journalen maa ikke binde ``connect`` ved import.

    ``from core.runtime.db_core import connect`` binder funktionen til den
    db_core-instans der var importeret ved modul-load. ``isolated_runtime``
    reloader ``db_core`` med en tmp-HOME, men reloader ikke dette modul — saa
    skrev journalen til den LEVENDE base under tests. Maalt: 121 raekker med
    identisk tidsstempel midt i en pytest-koersel, altsaa et helt tick skrevet
    ned i produktionens database.

    Vagen er strukturel med vilje: den fanger ikke et symptom, men selve den
    binding der gjorde skaden — ogsaa hvis nogen genindfoerer den for at
    "rydde op" i importerne.
    """
    from core.runtime import db_cadence_journal as journal

    assert not hasattr(journal, "connect"), (
        "db_cadence_journal binder connect paa modul-niveau — saa skriver den "
        "til den db_core-instans der var importeret ved load, ikke den aktive. "
        "Importér connect LAZY inde i funktionen."
    )
