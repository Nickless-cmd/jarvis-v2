"""En godkendt destruktiv kommando skal KØRE — og kun når et menneske sagde ja.

Fejlen (målt hos Bjørn 7/9-2026): kortet kom, han trykkede Godkend, og runnet
ventede videre til det timede ud. `_exec_bash` afviste destruktive kommandoer
ubetinget, med den begrundelse at en menneskelig godkendelse «kommer gennem
resolve_pending_approval ... ikke gennem det her flag».

Den antagelse holdt ikke: resolve_pending_approval kalder execute_tool_force →
_force_bash → _exec_bash(_runtime_trust_all=True), altså præcis dét flag. Den
godkendte kommando ramte sin egen gate igen og svarede approval_needed på ny.

Testene her holder BEGGE sider fast: godkendt kører, ikke-godkendt gør ikke.
"""

from __future__ import annotations

import pytest

DESTRUKTIV = {"command": "rm -rf /tmp/jarvis-test-findes-ikke-xyz"}


def test_uden_menneskelig_godkendelse_stoppes_en_destruktiv_kommando():
    """Autonome runs kalder execute_tool_force UDEN owner_approved.

    De skal blive ved med at blive stoppet — det var hullet som den
    oprindelige gate blev bygget for at lukke.
    """
    from core.tools.simple_tools import execute_tool_force

    r = execute_tool_force("bash", dict(DESTRUKTIV))
    assert r.get("status") == "approval_needed"
    assert r.get("classification") == "destructive"


def test_med_menneskelig_godkendelse_koerer_den():
    """Det symptom Bjørn så: godkendelsen kom frem, handlingen skete aldrig."""
    from core.tools.simple_tools import execute_tool_force

    r = execute_tool_force("bash", dict(DESTRUKTIV), owner_approved=True)
    assert r.get("status") != "approval_needed", (
        "en godkendt destruktiv kommando bad om godkendelse IGEN — løkken er tilbage"
    )


def test_modellen_kan_ikke_forfalske_sin_egen_godkendelse():
    """Markøren må ALDRIG kunne komme fra tool-argumenterne.

    Modellen skriver selv argumenterne. Lå godkendelsen dér, kunne den lukke
    gaten op indefra ved bare at sende det rigtige felt med.
    """
    from core.tools.simple_tools import execute_tool_force

    for forsoeg in ("_runtime_owner_approved", "owner_approved", "ejer_godkendt"):
        r = execute_tool_force("bash", {**DESTRUKTIV, forsoeg: True})
        assert r.get("status") == "approval_needed", (
            "argumentet %s lukkede den destruktive gate op" % forsoeg
        )


def test_trust_alene_aabner_ikke_gaten():
    """`_runtime_trust_all` er IKKE en menneskelig godkendelse.

    Det sættes af autonome runs. Blandes de to sammen, kan Jarvis køre
    rm -rf uden at nogen har set kommandoen.
    """
    from core.tools.simple_tools import execute_tool_force

    r = execute_tool_force("bash", {**DESTRUKTIV, "_runtime_trust_all": True})
    assert r.get("status") == "approval_needed"


def test_markoeren_nulstilles_ogsaa_naar_kaldet_kaster(monkeypatch):
    """Ellers stod porten åben for det NÆSTE kald i samme tråd."""
    from core.tools import simple_tools as st
    from core.tools.owner_approval import er_ejer_godkendt

    def eksploder(name, arguments):
        assert er_ejer_godkendt() is True
        raise RuntimeError("noget gik galt midt i")

    monkeypatch.setattr(st, "_execute_tool_force_impl", eksploder)
    with pytest.raises(RuntimeError):
        st.execute_tool_force("bash", dict(DESTRUKTIV), owner_approved=True)
    assert er_ejer_godkendt() is False


def test_resolve_giver_ejer_godkendelsen_videre(monkeypatch):
    """Selve koblingen: klikker Bjørn Godkend, skal flaget følge med.

    Uden den er alt ovenstående bygget men ikke forbundet — husets hyppigste
    fejl.
    """
    set_kald: list[dict] = []

    def fake_force(name, arguments, *, owner_approved=False):
        set_kald.append({"name": name, "owner_approved": owner_approved})
        return {"status": "ok", "result_text": "kørt"}

    import core.services.visible_runs as _vr
    from core.services import visible_runs_approvals as VA

    monkeypatch.setattr("core.tools.simple_tools.execute_tool_force", fake_force)
    monkeypatch.setattr("core.tools.simple_tools.format_tool_result_for_model",
                        lambda n, r: "kørt")
    monkeypatch.setattr(_vr, "_PENDING_APPROVALS",
                        {"a1": {"tool_name": "bash", "arguments": dict(DESTRUKTIV),
                                "run_id": "r1", "session_id": "", "status": "pending"}})
    monkeypatch.setattr(_vr, "_persist_pending_approvals", lambda: None)
    monkeypatch.setattr(_vr, "_get_visible_approval_state", lambda aid: {})
    monkeypatch.setattr(_vr, "_set_visible_approval_state", lambda aid, p: None)

    VA.resolve_pending_approval("a1", approved=True)
    assert set_kald and set_kald[0]["owner_approved"] is True, (
        "godkendelsen blev ikke givet videre til eksekveringen"
    )
