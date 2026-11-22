"""Peer-kanalen skal vaere symmetrisk: kan du modtage, kan du svare (22/11-2026).

MAALT 22/11-2026 i `agent_assignments`: et team oprettes SPREDT — op til 708 sekunder
mellem foerste og sidste soeskende i samme `parent_run_id`. Foer blev
`send_message_to_agent` kun givet naar `peer_agent_ids` var ikke-tom VED RUN-START.

Konsekvensen var en ensrettet kanal: en agent der startede tidligt stod ikke i den
senere soesters liste, men den senere soester stod i dens — saa den tidlige kunne
MODTAGE en besked den ikke havde værktøjet til at besvare.

Reglen er derfor: en kontraktbunden agent faar altid værktøjet. Afvisningen af en
ugyldig modtager ligger i `send_agent_to_agent`, som svarer med en konkret fejl —
det er bedre end et værktøj der mangler uden at nogen kan se hvorfor.
"""
from __future__ import annotations

import core.runtime.db_agent_contract as contract
from core.services import agent_runtime_spawn as spawn

VERKTOEJ = "send_message_to_agent"


def _navne(payload: list[dict]) -> set[str]:
    return {str((t.get("function") or {}).get("name") or "") for t in payload if isinstance(t, dict)}


def test_en_kontraktagent_uden_peers_faar_alligevel_kanalen(monkeypatch):
    """Kaernen i rettelsen: fravaeret af peers ved start maa ikke fjerne værktøjet."""
    monkeypatch.setattr(contract, "open_assignment_for_agent",
                        lambda aid: {"assignment_id": "asg-1", "agent_id": aid})
    payload = spawn._snapshot_tools({"agent_id": "agent-a", "allowed_tools_json": '["read_file"]'})
    assert VERKTOEJ in _navne(payload), _navne(payload)
    assert "read_file" in _navne(payload), "den oprindelige tilladelse maa ikke forsvinde"


def test_kanalen_tilfoejes_kun_en_gang(monkeypatch):
    """Staar værktøjet allerede i `allowed_tools_json`, maa det ikke duplikeres."""
    monkeypatch.setattr(contract, "open_assignment_for_agent",
                        lambda aid: {"assignment_id": "asg-1", "agent_id": aid})
    payload = spawn._snapshot_tools(
        {"agent_id": "agent-a", "allowed_tools_json": f'["read_file", "{VERKTOEJ}"]'}
    )
    navne = [str((t.get("function") or {}).get("name") or "") for t in payload if isinstance(t, dict)]
    assert navne.count(VERKTOEJ) == 1, navne


def test_en_agent_uden_kontrakt_faar_ikke_kanalen(monkeypatch):
    """Legacy-agenter har ingen kontrakt og ingen indbakke — de skal ikke have værktøjet.

    Samme guard som drain: uden et aabent assignment findes der intet at levere til.
    """
    monkeypatch.setattr(contract, "open_assignment_for_agent", lambda aid: None)
    monkeypatch.setattr(spawn, "agent_tools_enabled", lambda: True)
    payload = spawn._snapshot_tools({"agent_id": "agent-legacy", "allowed_tools_json": '["read_file"]'})
    assert VERKTOEJ not in _navne(payload), _navne(payload)
