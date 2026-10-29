"""Chat-composerens permission-vælger skal BIDE — ikke være teater (29/10-2026).

MÅLT gennem `execute_tool`: `_runtime_trust_all` var sat i et trust-run, men
`_exec_write_file` returnerede alligevel `approval_needed` for en sti uden for
auto-listen. Vælgeren ville have lovet fuld adgang og spurgt alligevel.

Testen går gennem `execute_tool` — ikke gennem den isolerede funktion — fordi
det var præcis den forskel der gjorde, at den første grønne måling intet beviste:
en ny fil i /tmp er auto-godkendt og spørger aldrig.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.tools.simple_tools import execute_tool  # noqa: E402

#: Uden for `_AUTO_APPROVE_WRITE_PREFIXES` → klassifikation `approval`.
APPROVAL_STI = "/var/tmp/jarvis_trust_test.txt"
#: Security-prædikat → `blocked`, uanset hvor meget adgang kørslen har.
BLOKERET_STI = "/home/bs/.ssh/authorized_keys"


def _skriv(path: str, **ekstra) -> dict:
    args = {"path": path, "content": "bevis\n", "_runtime_session_id": "trust-test"}
    args.update(ekstra)
    return execute_tool("write_file", args)


def test_uden_trust_kraever_den_godkendelse():
    Path(APPROVAL_STI).unlink(missing_ok=True)
    ud = _skriv(APPROVAL_STI)
    assert ud.get("status") == "approval_needed"
    assert not Path(APPROVAL_STI).exists()


def test_samtalens_trust_niveau_skriver_uden_kort():
    Path(APPROVAL_STI).unlink(missing_ok=True)
    ud = _skriv(APPROVAL_STI, _runtime_trust_mode=True)
    assert ud.get("status") == "ok", ud
    assert Path(APPROVAL_STI).exists()
    Path(APPROVAL_STI).unlink(missing_ok=True)


def test_autonomt_flag_alene_aabner_ikke():
    """`_runtime_trust_all` sættes også af autonome kørsler, hvor ingen kan
    svare på et kort. Det må derfor IKKE i sig selv give adgang uden for
    workspace — kun samtalens eget trust-niveau eller et ejer-godkendt kald."""
    Path(APPROVAL_STI).unlink(missing_ok=True)
    ud = _skriv(APPROVAL_STI, _runtime_trust_all=True)
    assert ud.get("status") == "approval_needed"
    assert not Path(APPROVAL_STI).exists()


def test_security_blokering_springes_aldrig_over():
    ud = _skriv(BLOKERET_STI, _runtime_trust_mode=True)
    assert ud.get("status") == "blocked"


def test_edit_file_foelger_samme_graense():
    Path(APPROVAL_STI).unlink(missing_ok=True)
    Path(APPROVAL_STI).write_text("gammel\n", encoding="utf-8")
    uden = execute_tool("edit_file", {
        "path": APPROVAL_STI, "old_text": "gammel", "new_text": "ny",
        "_runtime_session_id": "trust-test",
    })
    assert uden.get("status") == "approval_needed"
    med = execute_tool("edit_file", {
        "path": APPROVAL_STI, "old_text": "gammel", "new_text": "ny",
        "_runtime_session_id": "trust-test", "_runtime_trust_mode": True,
    })
    assert med.get("status") == "ok", med
    assert Path(APPROVAL_STI).read_text(encoding="utf-8") == "ny\n"
    Path(APPROVAL_STI).unlink(missing_ok=True)
