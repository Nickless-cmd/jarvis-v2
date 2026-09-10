"""Udloebne intentioner lukkes ogsaa naar ingen spoerger igen — Fase 11.

Udloebet var DOVENT: det skete kun naar den samme intention blev slaaet op paa
ny. En intention ingen spoerger til igen blev staaende `pending` for evigt.

MAALT 10/9-2026 i produktion: fire raekker med udloeb 23, 50, 115 og 115 dage
tilbage i tiden — alle stadig `pending`. Samme moenster som de 174
raadssessioner: en tilstandsmaskine med en doven overgang og ingen fejer til
halen. En flade der viser dem, rapporterer ventende godkendelser der ikke
findes.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta


def _lav(intent_key, *, udloeb_om_dage):
    from core.runtime.db_governance import create_tool_intent_approval_request
    nu = datetime.now(UTC)
    return create_tool_intent_approval_request(
        intent_key=intent_key, intent_type="inspect-working-tree",
        intent_target="x", approval_scope="bounded", approval_required=True,
        approval_reason="proeve",
        requested_at=nu.isoformat(),
        expires_at=(nu + timedelta(days=udloeb_om_dage)).isoformat(),
    )


def test_forlaengst_udloebne_lukkes(isolated_runtime):
    from core.runtime.db_governance import get_tool_intent_approval_request
    from core.services.tool_intent_approval_runtime import sweep_expired_intents

    _lav("gammel", udloeb_om_dage=-115)
    _lav("frisk", udloeb_om_dage=+7)

    ud = sweep_expired_intents()
    assert ud["lukket"] == 1, f"fejede forkert antal: {ud}"

    g = get_tool_intent_approval_request("gammel") or {}
    f = get_tool_intent_approval_request("frisk") or {}
    assert str(g.get("approval_state")) == "expired"
    assert str(f.get("approval_state")) == "pending", (
        "en intention der ikke er udloebet blev lukket")


def test_fejeren_kaster_aldrig(isolated_runtime, monkeypatch):
    """En fejer maa ikke kunne vaelte en opstart — den koerer i lifespan."""
    import core.services.tool_intent_approval_runtime as m

    monkeypatch.setattr(
        "core.runtime.db_governance.recent_tool_intent_approval_requests",
        lambda **kw: (_ for _ in ()).throw(RuntimeError("db nede")))
    ud = m.sweep_expired_intents()
    assert ud["lukket"] == 0
