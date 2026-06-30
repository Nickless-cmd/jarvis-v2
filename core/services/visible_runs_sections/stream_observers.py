"""Stream-observabilitets-nerver — Boy Scout-udtrækning fra visible_runs.py.

Én sammenhængende enhed: de self-safe nerver der gør tavse stream-/persist-
hændelser synlige i Centralen UDEN nogensinde at kaste tilbage ind i stream-
stien. Holdt adskilt fra run-orkestreringen så de kan læses/testes isoleret.

Symbolerne re-eksporteres fra visible_runs.py så eksisterende
imports/monkeypatches ikke knækker.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.services.visible_runs import VisibleRun


def observe_persist_failed(run: "VisibleRun", exc: BaseException) -> None:
    """H5 (spec §2/§4.5): persistering af assistant-beskeden fejlede MENS svaret
    allerede var vist live → "vist live, VÆK ved reload". Det er en DISTINKT klasse
    (svaret er IKKE tabt for brugeren nu, men forsvinder ved næste loadSession()).
    FØR forsvandt det tavst i ``except: pass`` — ingen nerve, ingen trace.

    Dette er KUN observabilitet — den faktiske persist-retry/transaktionelle HEAL
    er et senere Fase 2.5/5-punkt. Her gør vi blot fejlen synlig i Centralen.
    Self-safe: må aldrig kaste videre ind i stream-stien."""
    try:
        from core.services.central_core import central
        central().observe({
            "cluster": "stream", "nerve": "persist_failed",
            "run_id": getattr(run, "run_id", ""),
            "session_id": str(getattr(run, "session_id", "") or ""),
            "provider": getattr(run, "provider", ""),
            "model": getattr(run, "model", ""),
            "error": str(exc or "")[:200],
        })
    except Exception:
        pass


def observe_streamed_text_recovered(
    run: "VisibleRun", *, chars: int, source: str,
) -> None:
    """DAG-ÉT DIVERGENS-NERVE (2026-06-30, Bjørn: provider-agnostisk cutoff fra
    dag ét). Brugeren SÅ et svar streame ind, men serverens endelige tekst-kilde
    (``result.text``/``followup_text``) endte TOM → falsk empty_completion →
    fallback'en wipede det viste svar.

    Sandhedskilden for "hvad brugeren faktisk så" er de STREAMEDE bytes. Når den
    redningskilde fanger et svar som det normale kilde-felt tabte, fyrer denne
    nerve — så vi kan MÅLE hvor ofte divergensen rammer i produktion (og på tværs
    af hvilke providers/modeller), uafhængigt af thinking-content-healen.

    Self-safe: må aldrig kaste videre ind i stream-stien."""
    try:
        from core.services.central_core import central
        central().observe({
            "cluster": "stream", "nerve": "streamed_text_recovered",
            "run_id": getattr(run, "run_id", ""),
            "session_id": str(getattr(run, "session_id", "") or ""),
            "provider": getattr(run, "provider", ""),
            "model": getattr(run, "model", ""),
            "chars": int(chars),
            "source": str(source),
        })
    except Exception:
        pass
