"""De fire tavse fald i `execution_gate` — målt 31/10-2026.

Filen HAVDE allerede en `_rapporter_fail_open` med en docstring der sagde at
operator-grenen var fixet 9/9-2026. Det var den også. Men de fire andre grene
slugte stadig deres undtagelse med et bart `pass` — og to af dem havde endda en
kommentar der påstod det modsatte:

    except Exception:
        pass  # infra-blip → tillad (...), men traced

Der var ingen tracing. Kommentaren løj, og den løgn var dyrere end tavsheden:
en læser der stoler på den ville lede efter sporet i incident-loggen og ikke
finde det, uden at vide om det var fordi intet var sket — eller fordi sporet
aldrig blev skrevet.

Hver vagt her beviser TO ting: at fejlen efterlader et spor, OG at retningen er
uændret. Retningen er en politik (fail-open på et infra-blip brick'er ikke
ejeren), ikke en fejl — den må ikke ændres af en fejlrettelse.
"""
from __future__ import annotations

import logging


from core.services import gate_execution as G


def _kaster(exc: Exception):
    def _f(*a, **k):
        raise exc
    return _f


# ── 1. command-grenen: rbw kastede, kommandoen blev klassificeret alligevel ──
def test_command_rbw_fejl_logger_og_klassificerer_stadig(monkeypatch, caplog):
    import core.services.read_before_write_guard as rbw
    monkeypatch.setattr(rbw, "check_bash_command_safe", _kaster(RuntimeError("cache nede")))
    with caplog.at_level(logging.WARNING):
        v = G.execution_gate({"action": "command", "command": "ls -la", "session_id": "s"})
    assert "fail-open" in caplog.text and "cache nede" in caplog.text
    # retningen: en harmløs kommando skal stadig kunne køre
    assert v.decision.name == "GREEN"


# ── 2. file-grenen: kommentaren lovede "men traced" — den løj ──
def test_file_rbw_fejl_logger_og_tillader_stadig(monkeypatch, caplog):
    import core.services.read_before_write_guard as rbw
    monkeypatch.setattr(rbw, "check_read_before_write", _kaster(RuntimeError("blip")))
    with caplog.at_level(logging.WARNING):
        v = G.execution_gate({"action": "file", "path": "/tmp/ny.py", "session_id": "s"})
    assert "fail-open" in caplog.text and "blip" in caplog.text
    assert v.decision.name == "GREEN"


# ── 3. workspace_trust: "betroet" og "kunne ikke afgøres" var identiske ──
def test_workspace_trust_fejl_logger_og_tillader_stadig(monkeypatch, caplog):
    import core.services.workspace_trust as wt
    monkeypatch.setattr(wt, "guard_code_write", _kaster(RuntimeError("trust nede")))
    with caplog.at_level(logging.WARNING):
        v = G.execution_gate({"action": "workspace_trust", "tool_name": "write_file"})
    assert "fail-open" in caplog.text and "trust nede" in caplog.text
    assert v.decision.name == "GREEN"


# ── 4. _decide: koden der gør et kollaps LYD fejlede selv tavst ──
def test_decide_kollaps_efterlader_spor_selv_naar_incidenten_fejler(monkeypatch, caplog):
    """Den mest ironiske: incident-skrivningen er dét der skal gøre et
    gate-kollaps lydhørt. Fejler den, skal loggen bære begge fejl.

    Central-stien patches til at kaste FØRST — ellers fanger `central().decide`
    undtagelsen internt, og vi når aldrig den gren testen handler om.
    """
    import core.services.central_core as cc
    import core.runtime.db_central_incidents as inc
    monkeypatch.setattr(cc, "central", _kaster(RuntimeError("central nede")))
    monkeypatch.setattr(inc, "record_central_incident",
                        _kaster(RuntimeError("incident-db nede")))
    monkeypatch.setattr(G, "execution_gate", _kaster(RuntimeError("gaten selv kollapset")))
    with caplog.at_level(logging.ERROR):
        v = G._decide("exec_command", {"action": "command"})
    assert "incident-skrivning fejlede" in caplog.text
    assert "gaten selv kollapset" in caplog.text
    # sidste-udvej er stadig et Verdict — ikke None
    assert v is not None and v.decision.name == "GREEN"


# ── 5. støj-vagt: normal drift må ikke skrive én eneste advarsel ──
def test_normal_drift_stoejer_ikke(caplog):
    """Uden denne ville loggen drukne i normal-adfærd og de ægte fund forsvinde."""
    with caplog.at_level(logging.WARNING):
        G.execution_gate({"action": "command", "command": "ls", "session_id": "s"})
        G.execution_gate({"action": "file", "path": "/tmp/a.py", "session_id": "s"})
        G.execution_gate({"action": "workspace_trust", "tool_name": "write_file"})
    advarsler = [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert not advarsler, f"normal drift støjede: {[r.message for r in advarsler]}"


# ── 6. RETNINGEN: et ægte blok er stadig et blok ──
def test_et_aegte_blok_er_stadig_et_blok(monkeypatch):
    """Rapporteringen må ikke gøre gaten tandløs."""
    import core.services.read_before_write_guard as rbw
    monkeypatch.setattr(rbw, "check_read_before_write",
                        lambda *a, **k: (False, "du har ikke læst filen"))
    v = G.execution_gate({"action": "file", "path": "/tmp/a.py", "session_id": "s"})
    assert v.decision.name == "RED" and "læst" in v.reason
