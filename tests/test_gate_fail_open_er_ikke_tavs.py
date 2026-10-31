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


from core.services import gate_execution as G


def test_operator_grenen_RAPPORTERER_naar_vaernet_kaster(monkeypatch, caplog):
    import core.services.read_before_write_guard as rbw
    monkeypatch.setattr(rbw, "check_operator_read_before_write",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("infra-blip")))
    with caplog.at_level(logging.WARNING):
        G.execution_gate({"action": "operator", "path": "/x", "session_id": "s"})
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
    præcis det mønster der kostede synligheden.

    MÅLT 31/10-2026 — denne vagt var GRØN mens fire fald stod i `execution_gate`
    (linje 125, 163, 190, 263). Den havde TO blindheder, og begge skulle rettes:

    1. MØNSTRET matchede kun `check_*`-hjælperne, men faldene sad omkring de
       UNDERLIGGENDE værns kald (`check_bash_command_safe`,
       `check_read_before_write`, `guard_code_write`).
    2. `strip() == "pass"` matchede kun en bar `pass`. Faldene skrev
       `pass  # infra-blip → ...` — altså præcis den form kodebasen bruger
       overalt, og som vagten derfor var strukturelt blind for.

    En grøn vagt er ikke bevis for at målet er i orden: den målte kun én af
    flere former. Efterprøvet mod HEAD-filen, hvor den nu finder alle fire.
    """
    import pathlib
    import re
    GATE = re.compile(r"\b(check_command|check_file|check_operator|"
                      r"check_workspace_trust|check_upload|"
                      # de underliggende værn — det var HER faldene sad
                      r"check_bash_command_safe|check_read_before_write|"
                      r"check_operator_read_before_write|guard_code_write)\b")
    EXCEPT = re.compile(r"\s*except\b.*:\s*$")
    fund = []
    for f in [pathlib.Path("core/tools/simple_tools_operator.py"),
              pathlib.Path("core/services/gate_execution.py")]:
        linjer = f.read_text().splitlines()
        for i, linje in enumerate(linjer):
            if not GATE.search(linje) or linje.strip().startswith("#"):
                continue
            for j in range(i, min(i + 14, len(linjer))):
                if EXCEPT.match(linjer[j]):
                    # `pass  # begrundelse` er den form kodebasen FAKTISK
                    # bruger — en bar `== "pass"` så den ikke.
                    if linjer[j + 1].strip().startswith("pass"):
                        fund.append(f"{f.name}:{j+1}")
                    break
    assert not fund, f"tavse gate-kald: {fund}"
