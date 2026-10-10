"""Komprimerings-tråden skal bære den synlige kørsels kontekst (målt 10/10-2026).

`_maybe_auto_compact_session` starter en baggrundstråd for at holde
prompt-assembly fri. Men tråden startede UDEN `contextvars.copy_context()`, så
den arvede ikke `run_autonomy_context._run_id`.

Konsekvensen er tavs og dyr: `compact_llm._er_hans_tur()` læser netop den
ContextVar, svarer falsk, og komprimeringen falder til cheap lane. Cheap lane
svarer kort (29.466 af 60.000 svar under 60 tokens), kvalitetsgaten kræver ≥60
tegn, og resultatet er mekanisk fallback. Målt i `compaction_log`: 34 af 110
komprimeringer over 30 dage — hver tredje.

Testene her låser at tråden ser den kørsel forælderen stod i.
"""
from __future__ import annotations

import time


def _kør_komprimering(monkeypatch, session_id: str) -> list[str]:
    """Kør `_maybe_auto_compact_session` med en ÆGTE tråd og fang hvad den ser."""
    from core.services import prompt_contract as pc
    from core.services.prompt_sections import transcript_sections as ts
    from core.services.run_autonomy_context import current_run_id

    set_undervejs: list[str] = []

    def _falsk_komprimering(session_id, keep_recent, **kw):
        set_undervejs.append(current_run_id())
        with ts._compact_inflight_lock:
            ts._compact_inflight.discard(session_id)
        try:
            from core.context import compaction_signal as cs
            cs.marker_slut(session_id)
        except Exception:
            pass

    monkeypatch.setattr(pc, "_run_session_compaction", _falsk_komprimering)

    class _Beslutning:
        should_compact = True
        low_water_target = 1000

    import core.context.compaction_policy as cp
    monkeypatch.setattr(cp, "compaction_decision", lambda *a, **k: _Beslutning())

    class _S:
        context_keep_recent = 20

    ts._maybe_auto_compact_session(session_id, [], _S())

    for _ in range(100):
        if set_undervejs:
            break
        time.sleep(0.02)
    return set_undervejs


def test_komprimeringstraaden_ser_den_synlige_koersel(isolated_runtime, monkeypatch) -> None:
    """Tråden skal se forælderens run-id — ikke en tom kontekst."""
    from core.services.run_autonomy_context import set_run_identity

    set_run_identity("visible-kontekst-test", "interactive")
    try:
        set_undervejs = _kør_komprimering(monkeypatch, "s-ctx-1")
    finally:
        set_run_identity("")

    assert set_undervejs == ["visible-kontekst-test"], (
        "komprimeringstråden så ikke den synlige kørsel — "
        f"den arvede ikke ContextVar'en: {set_undervejs!r}")


def test_uden_synlig_koersel_er_konteksten_stadig_tom(isolated_runtime, monkeypatch) -> None:
    """Modprøven: fixet må ikke opfinde en kørsel der ikke findes."""
    from core.services.run_autonomy_context import set_run_identity

    set_run_identity("")
    try:
        set_undervejs = _kør_komprimering(monkeypatch, "s-ctx-2")
    finally:
        set_run_identity("")

    assert set_undervejs == [""], (
        f"tråden fandt en kørsel der ikke var der: {set_undervejs!r}")


def test_er_hans_tur_er_sand_inde_i_traaden(isolated_runtime, monkeypatch) -> None:
    """Den egenskab fixet faktisk skal give: primær-lanen bliver valgt."""
    from core.services.run_autonomy_context import set_run_identity
    from core.context import compact_llm as cl

    set_run_identity("visible-lane-test", "interactive")
    set_undervejs: list[bool] = []

    from core.services import prompt_contract as pc
    from core.services.prompt_sections import transcript_sections as ts

    def _falsk_komprimering(session_id, keep_recent, **kw):
        set_undervejs.append(cl._er_hans_tur())
        with ts._compact_inflight_lock:
            ts._compact_inflight.discard(session_id)
        try:
            from core.context import compaction_signal as cs
            cs.marker_slut(session_id)
        except Exception:
            pass

    monkeypatch.setattr(pc, "_run_session_compaction", _falsk_komprimering)

    class _Beslutning:
        should_compact = True
        low_water_target = 1000

    import core.context.compaction_policy as cp
    monkeypatch.setattr(cp, "compaction_decision", lambda *a, **k: _Beslutning())

    class _S:
        context_keep_recent = 20

    try:
        ts._maybe_auto_compact_session("s-ctx-3", [], _S())
        for _ in range(100):
            if set_undervejs:
                break
            time.sleep(0.02)
    finally:
        set_run_identity("")

    assert set_undervejs == [True], (
        "_er_hans_tur() var falsk i komprimeringstråden — "
        f"komprimeringen falder til cheap lane: {set_undervejs!r}")
