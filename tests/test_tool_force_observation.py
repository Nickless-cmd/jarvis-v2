"""Vagt: force-vejen skal ogsaa registrere sit forbrug.

MAALT 24/10-2026: `observe_tool_call` laa KUN i `execute_tool`. Synlige og
autonome koersler gaar gennem `execute_tool_force` (simple_tool_executor,
force=True), saa deres vaeltoejskald naaede aldrig `tool_usage`. Bevis fra
drift: `render_mermaid` blev kaldt kl. 22:41 og raekken stod stille paa
call_count=9 / last_used_at=17:54:58 — tælleren flyttede sig ikke.

Uden denne kobling er `tool_usage` blind for praecis den trafik der fylder
mest, og Centralen kan hverken ordne kataloget (mest-brugt foerst, doede
sidst) eller flagge doede værktøjer.
"""
from __future__ import annotations


def _stub_impl(monkeypatch, result):
    """Erstat den tunge impl — vi maaler observationen, ikke værktøjet."""
    from core.tools import simple_tools as st

    monkeypatch.setattr(
        st, "_execute_tool_force_impl", lambda name, args: dict(result)
    )


def test_force_vejen_observerer_sit_kald(monkeypatch):
    """Kernen: et force-kald skal naa observationslaget."""
    from core.tools import simple_tools as st
    from core.tools import tool_call_observation as obs

    set_kald: list = []
    _stub_impl(monkeypatch, {"status": "ok", "value": 1})
    monkeypatch.setattr(
        obs, "observe_tool_call", lambda n, a, r: set_kald.append((n, r))
    )

    st.execute_tool_force("render_mermaid", {"kilde": "flowchart TD\\n A --> B"})

    assert set_kald, (
        "force-vejen registrerede ikke sit kald — tool_usage bliver blind "
        "for alle synlige og autonome koersler"
    )
    assert set_kald[0][0] == "render_mermaid"
    assert set_kald[0][1].get("status") == "ok"


def test_force_vejen_observerer_ogsaa_naar_ejeren_har_godkendt(monkeypatch):
    """owner_approved-grenen maa ikke falde uden om observationen."""
    from core.tools import simple_tools as st
    from core.tools import tool_call_observation as obs

    set_kald: list = []
    _stub_impl(monkeypatch, {"status": "ok"})
    monkeypatch.setattr(obs, "observe_tool_call", lambda n, a, r: set_kald.append(n))

    st.execute_tool_force("write_file", {"path": "/tmp/x"}, owner_approved=True)

    assert set_kald == ["write_file"]


def test_force_vejen_taeller_ikke_systemets_egne_kald(monkeypatch):
    """Job-pollen er panelets puls, ikke et model-kald — samme vagt som execute_tool."""
    from core.tools import simple_tools as st
    from core.tools import tool_call_observation as obs

    set_kald: list = []
    _stub_impl(monkeypatch, {"status": "ok"})
    monkeypatch.setattr(obs, "observe_tool_call", lambda n, a, r: set_kald.append(n))
    monkeypatch.setattr(st, "er_internt_kald", lambda: True)

    st.execute_tool_force("bash", {"command": "echo hej"})

    assert set_kald == []


def test_observation_fejl_vaelter_ikke_kaldet(monkeypatch):
    """En maaling maa aldrig kunne vaelte kaldet den maaler."""
    from core.tools import simple_tools as st
    from core.tools import tool_call_observation as obs

    def _boom(*_a, **_k):
        raise RuntimeError("observationslag nede")

    _stub_impl(monkeypatch, {"status": "ok", "svar": 42})
    monkeypatch.setattr(obs, "observe_tool_call", _boom)

    result = st.execute_tool_force("render_mermaid", {"kilde": "x"})

    assert result == {"status": "ok", "svar": 42}
