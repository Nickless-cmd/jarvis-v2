"""Inbox-posten skal pege paa noget der FINDES (27/10-2026).

Maalt paa `run-4316279150ea47ba`: beskrivelsen bar 702 tegn af en tekst paa 2439,
og `DAEKNING`-linjen stod i halen der blev klippet. Samtidig pegede den paa
`get_agent(agent_id=…)` — et vaerktoej der ikke findes i kilden. En modtager der
fulgte pekeren fandt ingenting.

Vagten kræver den konkrete artefakt-sti og afviser den doede peker.
"""

from __future__ import annotations


def _koer(monkeypatch, *, status: str = "failed", artifact_path: str = "") -> str:
    from core.services import inbox_state

    kald: list[dict[str, object]] = []

    def fake_registrer(**kwargs):
        kald.append(kwargs)
        return {"status": "ok"}

    monkeypatch.setattr(inbox_state, "registrer_kilde", fake_registrer)

    from core.services.scout_inbox_delivery import record_scout_completion

    latest_run: dict[str, object] = {"run_id": "run-1", "output_summary": "agentens tekst"}
    if artifact_path:
        latest_run["artifact_path"] = artifact_path

    ok = record_scout_completion({
        "agent_id": "agent-1",
        "role": "researcher",
        "tool_policy": "read-only-runtime",
        "status": status,
        "goal": "E2E: fejl-stiens leverance",
        "context": {"user_id": "bjorn"},
        "latest_run": latest_run,
    })
    assert ok is True, "posten blev ikke registreret"
    assert len(kald) == 1
    return str(kald[0]["beskrivelse"])


def test_beskrivelsen_peger_paa_artefakten(monkeypatch, tmp_path):
    """Stien kommer fra RAECKEN — ikke fra et gaet paa agent_id/run_id.

    27/10-2026: her stod en forventning om `state/agent-artifacts/agent-1/run-1/
    final.txt`, altsaa den sti koden selv regnede ud. Den var forkert to gange i
    traek (relativ, derefter et doedt vaerktoejsnavn). Nu skrives stien paa
    `agent_runs.artifact_path` i det oejeblik filen skrives, og posten arver den.
    Vagten laegger derfor filen et sted det gamle gaet ALDRIG kunne finde: finder
    posten den, er stien laest.
    """
    fil = tmp_path / "helt-andet-sted" / "svar.txt"
    fil.parent.mkdir(parents=True)
    fil.write_text("svaret", encoding="utf-8")

    tekst = _koer(monkeypatch, artifact_path=str(fil))
    assert str(fil) in tekst


def test_uden_skrevet_sti_lyver_posten_ikke(monkeypatch):
    """Ingen fil paa disken → posten siger det, i stedet for at naevne en gaettet sti."""
    tekst = _koer(monkeypatch)
    assert "Ingen artefakt" in tekst


def test_den_doede_peker_er_vk(monkeypatch):
    """`get_agent` findes ikke i kilden — en peker paa den sender modtageren i tomrum."""
    tekst = _koer(monkeypatch)
    assert "get_agent" not in tekst
