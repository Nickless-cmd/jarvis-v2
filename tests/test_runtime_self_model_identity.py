"""Runtime self-model identity: falske sunde tilstande skal efterlade et spor.

MAALT 31/10-2026 paa den levende detektor: syv fald i
`core/services/runtime_self_model_identity.py`. Tre af dem returnerede en
FALSK SUND TILSTAND naar kaldet kastede — `{"wrongness_state": "clear"}`,
`{"active": False}`, `{"roles": []}`. En fejl var strukturelt identisk med
«alt er i orden», saa den aktive tilstand var den falske.

Fail-soft bevares (returvaerdien er uaendret); det der kommer til er et spor.
"""
from __future__ import annotations

# ── falske sunde tilstande skal efterlade et spor (31/10-2026) ────────────
#
# MAALT paa den levende detektor: tre flader returnerede en FALSK SUND
# TILSTAND naar kaldet kastede — `{"wrongness_state": "clear"}`,
# `{"active": False}`, `{"roles": []}`. En fejl var strukturelt identisk med
# «alt er i orden», saa den aktive tilstand var den falske.
#
# Fail-soft bevares (returvaerdien er uaendret); det der kommer til er et spor.

import core.services.runtime_self_model_identity as rsmi


def _logget(caplog, tekst):
    return any(tekst in r.getMessage() for r in caplog.records)


def test_epistemisk_flade_logger_men_paastaar_ikke_sundhed(monkeypatch, caplog):
    import core.services.epistemic_runtime_state as ers
    def _braek():
        raise RuntimeError("fladen kunne ikke bygges")
    monkeypatch.setattr(ers, "build_epistemic_runtime_state_surface", _braek)
    with caplog.at_level("WARNING", logger="core.services.runtime_self_model_identity"):
        ud = rsmi._epistemic_runtime_state_surface()
    assert ud["wrongness_state"] == "clear"  # fail-soft bevaret
    assert _logget(caplog, "epistemisk runtime-flade kunne ikke bygges"), \
        "en fejl rapporterede «clear» uden et spor"


def test_subagent_flade_logger_men_paastaar_ikke_tomhed(monkeypatch, caplog):
    import core.services.subagent_ecology as se
    def _braek():
        raise RuntimeError("fladen kunne ikke bygges")
    monkeypatch.setattr(se, "build_subagent_ecology_surface", _braek)
    with caplog.at_level("WARNING", logger="core.services.runtime_self_model_identity"):
        ud = rsmi._subagent_ecology_surface()
    assert ud["roles"] == []  # fail-soft bevaret
    assert _logget(caplog, "subagent-oekologi-fladen kunne ikke bygges")


def test_idle_flade_logger_men_paastaar_ikke_inaktiv(monkeypatch, caplog):
    import core.services.idle_consolidation as ic
    def _braek():
        raise RuntimeError("fladen kunne ikke bygges")
    monkeypatch.setattr(ic, "build_idle_consolidation_surface", _braek)
    with caplog.at_level("WARNING", logger="core.services.runtime_self_model_identity"):
        ud = rsmi._idle_consolidation_surface()
    assert ud["active"] is False  # fail-soft bevaret
    assert _logget(caplog, "idle-consolidation-fladen kunne ikke bygges")


def test_prompt_sektion_logger_naar_den_falder_til_none(monkeypatch, caplog):
    """En sektion der forsvinder ud af prompten skal kunne ses bagefter."""
    def _braek(*a, **k):
        raise RuntimeError("insight kunne ikke bygges")
    monkeypatch.setattr(rsmi, "_derive_self_insight_awareness", _braek, raising=False)
    with caplog.at_level("WARNING", logger="core.services.runtime_self_model_identity"):
        rsmi.build_self_insight_awareness_prompt_section()
    assert _logget(caplog, "self-insight-sektionen kunne ikke bygges")
