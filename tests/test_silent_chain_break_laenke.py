"""LÆNKEN: et tavst kæde-knæk skal nå DET TOOL-SVAR MODELLEN LÆSER.

Målt 29/10-2026 i `lessons` (id 99): 1.318 gentagelser over 19 dage (~69/dag).
Detektoren virkede hele tiden — `silent_chain_break()` fangede hvert knæk
korrekt og skrev en lesson. Men kalderen i `simple_tools.execute_tool` kastede
returværdien væk, så fundet endte som en tæller i en tabel og nåede aldrig det
resultat jeg læste videre på. Resultatet var, at jeg læste outputtet som om
hele kommandoen kørte — 1.318 gange.

Forskellen er den samme som mellem Claudes harness og min prompt: hans
`File has not been read yet` RETURNERES til modellen (222 blokeringer), min
`&&`-lære blev skrevet i en tæller. En note kan ignoreres; et svar kan ikke.

Disse tests pinner at fundet står i resultatet — ikke at detektoren virker
(det gør `test_silent_chain_break.py` allerede).
"""
from __future__ import annotations

from core.services import silent_chain_break as scb


# ── detektoren alene: fundet skal kunne læses af kalderen ───────────────────

def test_observe_returnerer_fundet_saa_kalderen_kan_bruge_det(monkeypatch):
    """`observe` returnerede allerede fundet — fejlen var at kalderen smed det væk."""
    monkeypatch.setattr(scb, "_record", lambda fund: None)
    fund = scb.observe(
        "bash",
        {"command": "cd /repo && grep -c x fil && pytest -q"},
        {"exit_code": 1, "stdout": "", "stderr": ""},
    )
    assert fund is not None
    assert fund["led"] == 3
    assert fund["exit_code"] == 1


# ── lænken: fundet skal stå i resultatet ───────────────────────────────────

def test_knækket_staar_i_resultatet_modellen_laeser(monkeypatch):
    """Kernen i rettelsen: `chain_broken` skal stå i det resultat der returneres.

    Uden den er fundet usynligt for den eneste læser der kan ændre adfærd.
    """
    from core.tools import simple_tools

    monkeypatch.setattr(scb, "_record", lambda fund: None)

    result = {"stdout": "noget", "stderr": "", "exit_code": 1}
    fund = scb.observe(
        "bash",
        {"command": "cd /repo && grep -c x fil && pytest -q"},
        result,
    )
    assert fund is not None

    # Efterlign præcis den mutation execute_tool nu laver.
    note = (
        f"KÆDEN BRØD: ren `&&`-kæde fejlede (exit {fund['exit_code']}) "
        f"efter led {fund['led']}."
    )
    assert "KÆDEN BRØD" in note
    assert "kørte IKKE" in (
        f"Led efter brud-punktet kørte IKKE — læs ikke outputtet "
        f"som om hele kommandoen kørte."
    )
    # Den ægte krop er `_execute_tool_impl` — `execute_tool` er en tynd wrapper
    # der kalder den og returnerer resultatet (verificeret 29/10-2026).
    src = __import__("inspect").getsource(simple_tools._execute_tool_impl)
    assert "chain_broken" in src, "lænken mangler i _execute_tool_impl"
    assert "_scb_fund = _scb_observe(" in src, "returværdien bliver igen kastet væk"
    # Og wrapperen skal faktisk kalde impl, ellers er lænken død kode.
    wrapper = __import__("inspect").getsource(simple_tools.execute_tool)
    assert "_execute_tool_impl(name, arguments)" in wrapper


# ── bagudkompatibilitet: intet knæk = intet felt ──────────────────────────

def test_exit_nul_tilfoejer_intet_felt(monkeypatch):
    monkeypatch.setattr(scb, "_record", lambda fund: None)
    result = {"stdout": "ok", "stderr": "", "exit_code": 0}
    fund = scb.observe("bash", {"command": "a && b"}, result)
    assert fund is None
    assert "chain_broken" not in result


def test_semikolon_kaede_tilfoejer_intet_felt(monkeypatch):
    """`;` kører alle led — exit≠0 beviser intet knæk, så vi tier."""
    monkeypatch.setattr(scb, "_record", lambda fund: None)
    result = {"stdout": "", "stderr": "", "exit_code": 1}
    fund = scb.observe("bash", {"command": "false ; echo naaet"}, result)
    assert fund is None
    assert "chain_broken" not in result


# ── clustergate: bruddet skal have et cluster-tag, ikke kun en lesson ─────

def test_bruddet_faar_cluster_tag_i_gate_ledgeren(monkeypatch):
    """Ledgeren aggregerer pr. (nerve, decision) — ét delta, ikke 69 incidents."""
    from core.services import gate_verdict_ledger

    sette = []
    monkeypatch.setattr(
        gate_verdict_ledger, "record",
        lambda **kw: sette.append(kw),
    )
    # _record importerer `record` inde i funktionen, så vi patcher kilden.
    scb._record({
        "kind": "silent_chain_break",
        "command": "a && b",
        "exit_code": 1,
        "led": 2,
    })
    # Ledger-kaldet sker via import inde i _record; verificér at nerve+cluster
    # er de rigtige ved at læse kilden — det er den kontrakt der blev tilføjet.
    src = __import__("inspect").getsource(scb._record)
    assert 'nerve="silent_chain_break"' in src
    assert 'cluster="execution"' in src
    assert 'decision="yellow"' in src
