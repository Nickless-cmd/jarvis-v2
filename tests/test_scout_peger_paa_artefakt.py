"""Inbox-posten skal pege paa noget der FINDES — og paa en ABSOLUT sti.

Baggrund (27/10-2026): posten for `run-4316279150ea47ba` bar 702 tegn af en
tekst paa 2439, og `DAEKNING`-linjen — kontraktens egen noegle — stod i halen
der blev klippet. Foerste rettelse pegede paa artefakten, men med en RELATIV
sti (`state/agent-artifacts/...`), som en modtager uden for ~/.jarvis-v2 ikke
kan aabne. Disse vagter holder baade absolutheden og eksistensen fast.
"""

from pathlib import Path

from core.services.scout_inbox_delivery import record_scout_completion


def _surface(agent_id="agent-1", run_id="run-1", status="failed"):
    return {
        "agent_id": agent_id,
        "role": "researcher",
        "tool_policy": "read-only-runtime",
        "status": status,
        "goal": "E2E",
        "context": {"user_id": "bjorn"},
        "latest_run": {"run_id": run_id, "output_summary": "delvis svar"},
    }


def _fang(monkeypatch):
    from core.services import inbox_state

    fanget: dict[str, object] = {}

    def _reg(**kw):
        fanget.update(kw)
        return {"status": "ok"}

    monkeypatch.setattr(inbox_state, "registrer_kilde", _reg)
    return fanget


def test_pegeren_er_absolut_og_peger_paa_den_findes(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    mappe = tmp_path / ".jarvis-v2/state/agent-artifacts/agent-1/run-1"
    mappe.mkdir(parents=True)
    svar = mappe / "final.txt"
    svar.write_text("svaret", encoding="utf-8")

    fanget = _fang(monkeypatch)
    assert record_scout_completion(_surface()) is True

    tekst = str(fanget["beskrivelse"])
    assert str(svar) in tekst, "den absolutte sti skal staa i posten"
    assert Path(str(svar)).is_absolute(), "en relativ sti kan modtageren ikke aabne"
    assert Path(str(svar)).exists(), "pegeren maa ikke pege i tomme luft"


def test_uden_final_txt_peges_der_paa_mappen(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    mappe = tmp_path / ".jarvis-v2/state/agent-artifacts/agent-1/run-1"
    mappe.mkdir(parents=True)

    fanget = _fang(monkeypatch)
    assert record_scout_completion(_surface()) is True

    tekst = str(fanget["beskrivelse"])
    assert "Artefaktmappe" in tekst
    assert str(mappe) in tekst
    assert Path(str(mappe)).exists()


def test_uden_artefakt_siges_det_hojt(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))

    fanget = _fang(monkeypatch)
    assert record_scout_completion(_surface()) is True

    tekst = str(fanget["beskrivelse"])
    assert "Ingen artefakt" in tekst, "tavshed er den fejl vi retter"
    assert "Hele svaret" not in tekst
