"""Fastholder dommene i docs/notes/2026-11-07-doede-moduler.md.

Ærlig afgrænsning: to af modulerne er DUPLIKATER, så der er ingen kobling at
fjerne. Testene her måler i stedet at (a) den ægte implementation stadig har
de egenskaber dommen bygger på, og (b) de tre moduler stadig ingen
produktions-kaldere har — så en senere kobling tvinger dommen til at blive
genlæst i stedet for at gøre den stille forkert.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROD = Path(__file__).resolve().parent.parent
MODULER = ("retry_runtime", "prepared_request", "model_benchmark")


def _produktionsfiler():
    for d in ("core", "apps", "scripts"):
        for p in (ROD / d).rglob("*.py"):
            if "__pycache__" not in p.parts:
                yield p


@pytest.mark.parametrize("modul", MODULER)
def test_modulet_har_stadig_ingen_produktionskaldere(modul):
    moenster = re.compile(rf"\b{modul}\b")
    kaldere = [str(p.relative_to(ROD)) for p in _produktionsfiler()
               if p.stem != modul and moenster.search(p.read_text(encoding="utf-8", errors="ignore"))]
    assert kaldere == [], (
        f"{modul} har nu produktions-kaldere {kaldere} — genlæs dommen i "
        "docs/notes/2026-11-07-doede-moduler.md")


def test_ægte_retry_vej_har_de_tre_lofter_og_en_enkelt_klassifikation():
    """DUPLIKAT-dommen for retry_runtime hviler på at visible_runs har tur-loft."""
    kilde = (ROD / "core/services/visible_runs.py").read_text(encoding="utf-8")
    for nøgle in ("round_stream_max_retries", "turn_total_stream_retries",
                  "turn_total_wall_clock_s", "agentic_round_retry_enabled"):
        assert nøgle in kilde, nøgle


def test_ægte_retry_klassifikation_skelner_forbigaaende_fra_fast():
    """Samme skel som retry_runtime.decide(), men i den vej der kører."""
    from core.services.stream_failure_kind import FailureKind, is_retryable_kind
    resultat = {k: is_retryable_kind(k) for k in (
        FailureKind.HTTP_429, FailureKind.HTTP_5XX, FailureKind.TRANSIENT_DROP,
        FailureKind.USER_CANCEL, FailureKind.UNKNOWN, FailureKind.PROVIDER_STALL)}
    assert resultat == {
        FailureKind.HTTP_429: True, FailureKind.HTTP_5XX: True,
        FailureKind.TRANSIENT_DROP: True, FailureKind.USER_CANCEL: False,
        FailureKind.UNKNOWN: False, FailureKind.PROVIDER_STALL: False}
