from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4


def _insert_reflection_signal(db, *, status: str = "integrating") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_reflection_signal(
        signal_id=f"reflection-{uuid4().hex}",
        signal_type="slow-integration",
        canonical_key="reflection-signal:slow-integration:danish-concise-calibration",
        status=status,
        title="Slow integration thread: Danish concise calibration",
        summary="Jarvis is carrying a slow integration thread around Danish concise calibration.",
        rationale="Validation reflection support.",
        source_kind="multi-signal-runtime-derivation",
        confidence="high",
        evidence_summary="Validation evidence should stay out of the helper block.",
        support_summary="Validation support should stay out of the helper block.",
        support_count=3,
        session_count=2,
        created_at=now,
        updated_at=now,
        status_reason="Validation integrating reflection.",
        run_id="validation-run",
        session_id="validation-session",
    )


def _bind_budget_profil(monkeypatch) -> None:
    """Bind budget-profilen, saa testen maaler sig selv og ikke sin omverden.

    Maalt 15/9-2026: testen var flaky (2-3 roede ud af 5) og aarsagen laa i
    `prompt_contract`:

        compact = (provider == "ollama") and not _is_cloud_model
                  and (0 < _win < 200_000)
        budget_profile = "visible_compact" if compact else "visible_full"

    Profilerne giver support-signaler 276 tegn (kompakt) mod 476 (fuld). I den
    kompakte er der ikke plads til hele refleksions-blokken, saa den blev
    klippet — og testen kunne ikke vide hvilken profil den fik, fordi den
    hverken binder udbyder eller kontekstvindue.

    Den maaler altsaa noget den ikke kontrollerer, og derfor binder den nu den
    fulde profil — den blokken er dimensioneret til.

    AERLIGT FORBEHOLD: bindingen gjorde den IKKE stabil. Maalt over mange
    koersler efter aendringen: 10/10 groenne i én omgang, 2/5 i den naeste,
    5/5 naar den koeres sammen med test_attention_budget. Raten varierer
    mellem koersler af samme kommando, saa der er en anden kilde jeg ikke har
    fundet. Udelukket undervejs: DB-isolationen (den ER isoleret, i
    /tmp/pytest-of-*), blok-byggeren (`_reflection_support_signal_instruction`
    returnerer altid det rigtige) og mine egne aendringer denne dag.

    Bindingen bliver staaende alligevel: en test skal maale noget den
    kontrollerer, uanset om det var kuren.
    """
    import core.services.model_context as mc
    # Et vindue over 200.000 slaar `compact` fra uanset udbyder.
    monkeypatch.setattr(mc, "model_context_window", lambda *a, **k: 1_000_000)


def _system_text_from_visible_input(visible_model, message: str = "Hello") -> str:
    payload = visible_model._build_visible_input(message, session_id="test-session")
    assert payload[0]["role"] == "system"
    return payload[0]["content"][0]["text"]


def test_visible_input_omits_reflection_support_block_when_no_relevant_signals_exist(isolated_runtime) -> None:
    system_text = _system_text_from_visible_input(isolated_runtime.visible_model)

    assert "Reflection support signal:" not in system_text


def test_visible_input_includes_small_subordinate_reflection_support_block(isolated_runtime, monkeypatch) -> None:
    _bind_budget_profil(monkeypatch)
    _insert_reflection_signal(isolated_runtime.db)

    system_text = _system_text_from_visible_input(isolated_runtime.visible_model)

    assert "Reflection support signal:" in system_text
    assert "dominant_reflection=Slow integration thread: Danish concise calibration" in system_text
    assert "reflection_state=integrating" in system_text
    assert "reflection_direction=slow-integration" in system_text
    assert "reflection_confidence=high" in system_text
    assert "Use only as subordinate support. Runtime and visible truth outrank it." in system_text


def test_visible_input_reflection_support_block_stays_bounded(isolated_runtime) -> None:
    _insert_reflection_signal(isolated_runtime.db)

    system_text = _system_text_from_visible_input(isolated_runtime.visible_model)
    reflection_block = next(
        part for part in system_text.split("\n\n")
        if part.startswith("Reflection support signal:")
    )

    assert "evidence_summary" not in reflection_block
    assert "support_summary" not in reflection_block
    assert "rationale" not in reflection_block
    assert "recent_history" not in reflection_block
