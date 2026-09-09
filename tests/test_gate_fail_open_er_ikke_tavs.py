"""En SECURITY-gate der fejler ÅBENT må ikke gøre det tavst.

Gatens egen docstring lover at et infra-blip «bevarer den tidligere fail-open
adfærd MEN er nu traced via Centralen i stedet for et tavst `except: pass`».
Operator-grenen holdt ikke det løfte, og det gjorde de to kaldesteder heller
ikke: et værn der fejler blev til et værn der ikke fandtes, uden en linje
nogen steder.

Retningen ændres IKKE her. At blokere på et blip ville kunne spærre harmløse
ejer-handlinger, og dét er en politik-beslutning. Men det kan nu SES.
"""
from __future__ import annotations

import logging

import pytest

from core.services import gate_execution as G


def test_operator_grenen_RAPPORTERER_naar_vaernet_kaster(monkeypatch, caplog):
    import core.services.read_before_write_guard as rbw
    monkeypatch.setattr(rbw, "check_operator_read_before_write",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("infra-blip")))
    with caplog.at_level(logging.WARNING):
        v = G.execution_gate({"action": "operator", "path": "/x", "session_id": "s"})
    assert "fail-open" in caplog.text and "infra-blip" in caplog.text


def test_retningen_er_UAENDRET_fail_open(monkeypatch):
    """Handlingen skal stadig igennem — ellers ville et blip spærre ejeren."""
    import core.services.read_before_write_guard as rbw
    monkeypatch.setattr(rbw, "check_operator_read_before_write",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("blip")))
    v = G.execution_gate({"action": "operator", "path": "/x", "session_id": "s"})
    assert v.decision.name == "GREEN"


def test_et_AEGTE_blok_er_stadig_et_blok(monkeypatch):
    """Rapporteringen må ikke gøre gaten tandløs."""
    import core.services.read_before_write_guard as rbw
    monkeypatch.setattr(rbw, "check_operator_read_before_write",
                        lambda *a, **k: (False, "du har ikke læst filen"))
    v = G.execution_gate({"action": "operator", "path": "/x", "session_id": "s"})
    assert v.decision.name == "RED" and "læst" in v.reason


def test_rapporteringen_kan_ikke_vaelte_gaten(monkeypatch):
    """Selv-sikker: hverken loggen eller incidenten må kunne kaste videre."""
    import core.services.read_before_write_guard as rbw
    monkeypatch.setattr(rbw, "check_operator_read_before_write",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("blip")))
    monkeypatch.setattr(G.logger, "warning",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("log nede")))
    v = G.execution_gate({"action": "operator", "path": "/x", "session_id": "s"})
    assert v.decision.name == "GREEN"


# ── kaldestederne ────────────────────────────────────────────────────────

def test_operator_vaerktoejerne_rapporterer_ogsaa(caplog):
    from core.tools.simple_tools_operator import _rapporter_gate_svigt
    with caplog.at_level(logging.WARNING):
        _rapporter_gate_svigt("operator_edit_file", "/sti/fil.py", RuntimeError("nede"))
    assert "SPRUNGET OVER" in caplog.text
    assert "operator_edit_file" in caplog.text and "/sti/fil.py" in caplog.text


def test_kaldestedets_rapportering_kaster_aldrig(monkeypatch):
    """Rapporteringen må ikke kunne vælte det værktøj den beskytter."""
    import logging as _l
    from core.tools.simple_tools_operator import _rapporter_gate_svigt
    monkeypatch.setattr(_l.Logger, "warning",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("log nede")))
    _rapporter_gate_svigt("operator_multi_edit", "/x", RuntimeError("blip"))   # kaster ikke


def test_der_er_ingen_TAVSE_gate_kald_tilbage():
    """Vagten mod tilbagefald: et `except: pass` omkring et gate-kald er
    præcis det mønster der kostede synligheden."""
    import pathlib, re
    GATE = re.compile(r"\b(check_command|check_file|check_operator|"
                      r"check_workspace_trust|check_upload)\b")
    fund = []
    for f in [pathlib.Path("core/tools/simple_tools_operator.py"),
              pathlib.Path("core/services/gate_execution.py")]:
        linjer = f.read_text().splitlines()
        for i, l in enumerate(linjer):
            if not GATE.search(l) or l.strip().startswith("#"):
                continue
            for j in range(i, min(i + 14, len(linjer))):
                if re.match(r"\s*except\b.*:\s*$", linjer[j]):
                    if linjer[j + 1].strip() == "pass":
                        fund.append(f"{f.name}:{j+1}")
                    break
    assert not fund, f"tavse gate-kald: {fund}"
