"""Høsten af runde-etiketter sender OG gemmer (19/9-2026).

Den sidste rundes etiket blev hentet EFTER at svaret var gemt, så den var væk
ved hver genindlæsning. Høsten ligger nu før gemningen, og den giver hver
etiket til turens akkumulator.
"""
from __future__ import annotations

from pathlib import Path

from core.services import visible_run_trace as vrt
from core.services.visible_turn_accumulator import TurnAccumulator


def test_hoesten_returnerer_og_laegger_i_turen(monkeypatch) -> None:
    e = {"run_id": "r1", "round": 2, "etiket": "Rettede fejl i login", "tool_use_ids": ["t1"]}
    monkeypatch.setattr(vrt, "haent_ventende", lambda run_id: [e])
    tur = TurnAccumulator()

    ud = vrt.hoest_etiketter("r1", tur)

    assert ud == [e]
    assert tur.round_labels[0]["summary"] == "Rettede fejl i login"


def test_med_frist_bruger_den_ventende_vej(monkeypatch) -> None:
    kaldt: list[float] = []
    monkeypatch.setattr(vrt, "haent_ventende_med_frist", lambda run_id, f: kaldt.append(f) or [])
    vrt.hoest_etiketter("r1", TurnAccumulator(), 1.2)
    assert kaldt == [1.2]


def test_sidste_hoest_ligger_FOER_svaret_gemmes() -> None:
    """Kilde-vagt på rækkefølgen: den sene høst skal stå før gemningen i den
    agentiske slutning — ellers er sidste rundes etiket væk efter reload."""
    kilde = (Path(__file__).resolve().parents[1] / "core/services/visible_runs.py").read_text(encoding="utf-8")
    hoest = kilde.index("_hoest_etiketter(run.run_id, _turn, 1.2)")
    gem = kilde.index("_persist_session_assistant_message(\n                        run, followup_text,")
    assert hoest < gem
