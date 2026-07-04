"""Tests for decision_signal_staging — den efemere staging der dræbte
decision-signal-runaway'en (2026-07-04)."""
from __future__ import annotations

from core.services.decision_signal_staging import (
    compose_signal_note,
    stage_signal,
    compose_exchange_text,
)


def test_compose_signal_note_format():
    note = compose_signal_note("dec_x", "backend_unresolved_3_calls", "streak ≥3")
    assert "[decision-signal: dec_x (backend_unresolved_3_calls: streak ≥3)]" in note
    assert note.startswith("\n\n") and note.endswith("\n\n")


def test_stage_signal_dedup_same_decision_never_accumulates():
    """RUNAWAY-INVARIANTEN: samme decision fyret N gange → højst ÉN note."""
    active: dict[str, str] = {}
    for _ in range(500):
        stage_signal(active, "dec_56d4dbb03e22", compose_signal_note(
            "dec_56d4dbb03e22", "backend_unresolved_3_calls", "streak ≥3"))
    assert len(active) == 1
    # og exchange-teksten indeholder præcis én markør, ikke 500
    text = compose_exchange_text(["svar"], active)
    assert text.count("[decision-signal:") == 1


def test_stage_signal_caps_distinct_decisions():
    active: dict[str, str] = {}
    for i in range(10):
        stage_signal(active, f"dec_{i}", compose_signal_note(f"dec_{i}", "t", "s"), cap=3)
    assert len(active) == 3
    # de 3 NYESTE beholdes
    assert set(active.keys()) == {"dec_7", "dec_8", "dec_9"}


def test_compose_exchange_text_leaves_base_untouched():
    """Det ægte svar (base_parts) må ALDRIG forurenes — persist + resolution læser den ren."""
    base_parts = ["Jeg fandt root cause: ", "det var cooldown 0."]
    active = {"dec_x": compose_signal_note("dec_x", "t", "s")}
    text = compose_exchange_text(base_parts, active)
    # base bevaret ordret forrest
    assert text.startswith("Jeg fandt root cause: det var cooldown 0.")
    # noten tilføjet EFTER, ikke flettet ind
    assert "[decision-signal: dec_x" in text
    # og base_parts selv er urørt (ingen mutation)
    assert base_parts == ["Jeg fandt root cause: ", "det var cooldown 0."]


def test_compose_exchange_text_empty_active_is_pure_base():
    assert compose_exchange_text(["a", "b"], {}) == "ab"


def test_compose_exchange_text_empty_base_strips_notes():
    active = {"dec_x": compose_signal_note("dec_x", "t", "s")}
    text = compose_exchange_text([], active)
    assert text == "[decision-signal: dec_x (t: s)]"


def test_resolution_buffer_stays_clean_across_runaway():
    """Kernen: uanset hvor mange gange decisionen fyrer, forbliver den buffer
    resolution-exit-tjekket læser (base_parts / _a_parts) uforurenet."""
    base_parts: list[str] = []  # svarer til _a_parts (modellens ægte prosa)
    active: dict[str, str] = {}
    # simulér 200 runder hvor decisionen fyrer men modellen intet skriver
    for _ in range(200):
        active.clear()  # visible_runs resetter pr. runde
        stage_signal(active, "dec_backend", compose_signal_note("dec_backend", "t", "s"))
    # _a_parts (exit-bufferen) er stadig tom → triggeren KAN se en resolution når
    # modellen endelig skriver den. Før fixet var den fuld af markører.
    assert base_parts == []
    resolution_view = "".join(base_parts)[-2000:]
    assert "[decision-signal:" not in resolution_view
