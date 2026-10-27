"""Inbox-posten skal pege paa noget der FINDES (27/10-2026).

Maalt paa `run-4316279150ea47ba`: beskrivelsen bar 702 tegn af en tekst paa 2439,
og `DAEKNING`-linjen stod i halen der blev klippet. Samtidig pegede den paa
`get_agent(agent_id=…)` — et vaerktoej der ikke findes i kilden. En modtager der
fulgte pekeren fandt ingenting.

Vagten kræver den konkrete artefakt-sti og afviser den doede peker.
"""

from __future__ import annotations


def _koer(monkeypatch, *, status: str = "failed") -> str:
    from core.services import inbox_state

    kald: list[dict[str, object]] = []

    def fake_registrer(**kwargs):
        kald.append(kwargs)
        return {"status": "ok"}

    monkeypatch.setattr(inbox_state, "registrer_kilde", fake_registrer)

    from core.services.scout_inbox_delivery import record_scout_completion

    ok = record_scout_completion({
        "agent_id": "agent-1",
        "role": "researcher",
        "tool_policy": "read-only-runtime",
        "status": status,
        "goal": "E2E: fejl-stiens leverance",
        "context": {"user_id": "bjorn"},
        "latest_run": {"run_id": "run-1", "output_summary": "agentens tekst"},
    })
    assert ok is True, "posten blev ikke registreret"
    assert len(kald) == 1
    return str(kald[0]["beskrivelse"])


def test_beskrivelsen_peger_paa_artefakten(monkeypatch):
    tekst = _koer(monkeypatch)
    assert "state/agent-artifacts/agent-1/run-1/final.txt" in tekst


def test_den_doede_peker_er_vk(monkeypatch):
    """`get_agent` findes ikke i kilden — en peker paa den sender modtageren i tomrum."""
    tekst = _koer(monkeypatch)
    assert "get_agent" not in tekst
