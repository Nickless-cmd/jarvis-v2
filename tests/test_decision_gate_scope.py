"""En beslutning skal kunne gælde ét værktøj — ikke hele maskinrummet.

Målt 10/11-2026: `dec_6a234cd30460` («Undgå researcher til git-historik og
regressionsspørgsmål — den har ingen shell») blokerede hver eneste redigering af
en fil der nævnte ordet «researcher». Det ramte en budget-tabel pr. rolle, som
intet har med dispatch at gøre, og det gjorde det umuligt at bygge den rettelse
beslutningen selv var en del af.

Årsagen er mekanisk: `_detect_conflict` matcher et enkelt ord fra direktivet mod
værktøjs-konteksten, og «researcher» fylder 11 % af direktivet — over
`_MIN_ORD_ANDEL` på 0,08 — så det matcher alene. Gaten kan ikke læse en hensigt.

Rettelsen er ikke et bedre ord: det er et SCOPE. Beslutningen siger hvilke
værktøjer den gælder, og gaten springer den over for alle andre. Et manglende
scope betyder «alle værktøjer», så ingen gammel beslutning ændrer adfærd.
"""
from __future__ import annotations

import pytest

BESLUTNING = {
    "decision_id": "dec_6a234cd30460",
    "directive": "Undgå researcher til git-historik og regressionsspørgsmål — den har ingen shell.",
    "status": "active",
    "priority": 65,
}


@pytest.fixture
def aktive(monkeypatch):
    """Indsæt en kontrolleret beslutningsliste i stedet for den levende database."""
    from core.services import behavioral_decisions

    def _indsæt(*beslutninger):
        monkeypatch.setattr(
            behavioral_decisions, "list_active_decisions",
            lambda limit=500: [dict(b) for b in beslutninger],
        )

    return _indsæt


FIL_REDIGERING = {
    "path": "/media/projects/jarvis-v2/core/services/agent_task_facade.py",
    "new_text": '_BUDGET_DEFAULT = {"researcher": 60_000, "critic": 16_000}',
}
DISPATCH = {
    "subagent_type": "researcher",
    "prompt": "kør git log og find regressionen",
    "description": "git-historik",
}


def test_scope_frir_redigeringen_der_blev_blokeret(aktive):
    """Kernen i rettelsen: en fil der NÆVNER rollen er ikke en dispatch."""
    from core.services.decision_gate import check_decision_gate

    aktive({**BESLUTNING, "scope_tools": '["Task", "dispatch_agent"]'})

    for vaerktoej in ("edit_file", "write_file"):
        ok, reason = check_decision_gate(vaerktoej, FIL_REDIGERING, "")
        assert ok is True, f"{vaerktoej} blev stadig blokeret: {reason}"


def test_scope_bevarer_dispatch_blokken(aktive):
    """Tænderne skal blive siddende: en rigtig dispatch til rollen rammes stadig."""
    from core.services.decision_gate import check_decision_gate

    aktive({**BESLUTNING, "scope_tools": '["Task", "dispatch_agent"]'})

    ok, reason = check_decision_gate("Task", DISPATCH, "")
    assert ok is False, "beslutningen mistede sine tænder"
    assert "researcher" in str(reason).lower() or "6a234cd3" in str(reason)


def test_beslutning_uden_scope_rammer_stadig_alt(aktive):
    """Bagudkompatibilitet: en gammel beslutning må ikke ændre adfærd af sig selv."""
    from core.services.decision_gate import check_decision_gate

    aktive(dict(BESLUTNING))  # intet scope_tools

    ok, _ = check_decision_gate("edit_file", FIL_REDIGERING, "")
    assert ok is False, "en beslutning uden scope skal opføre sig præcis som før"


def test_tom_scope_liste_betyder_alle_vaerktoejer(aktive):
    from core.services.decision_gate import check_decision_gate

    aktive({**BESLUTNING, "scope_tools": "[]"})

    ok, _ = check_decision_gate("edit_file", FIL_REDIGERING, "")
    assert ok is False, "en tom liste er ikke et scope — den er et fravær"


def test_scope_graderes_ogsaa_i_den_bloede_variant(aktive):
    """Begge gate-funktioner skal scopere ens, ellers siger de to ting om samme kald."""
    from core.services.decision_gate import evaluate_decision_conflict

    aktive({**BESLUTNING, "scope_tools": '["Task"]'})

    sev, _ = evaluate_decision_conflict("edit_file", FIL_REDIGERING, "")
    assert sev == "none", "den graderede variant scopede ikke"

    sev, _ = evaluate_decision_conflict("Task", DISPATCH, "")
    assert sev == "hard", "den graderede variant mistede blokken"


def test_kolonnen_er_idempotent(tmp_path):
    """`_ensure_decision_scope_column` skal kunne køre to gange uden at kaste."""
    import sqlite3

    from core.runtime.db_schema import _ensure_decision_scope_column

    conn = sqlite3.connect(tmp_path / "t.db")
    conn.execute(
        "CREATE TABLE behavioral_decisions (decision_id TEXT PRIMARY KEY, directive TEXT, "
        "priority INTEGER DEFAULT 50, scope_tools TEXT)"
    )
    conn.execute(
        "INSERT INTO behavioral_decisions (decision_id, directive, scope_tools) VALUES (?, ?, ?)",
        ("dec_eksisterende", "Undgå researcher til git-historik", '["Task"]'),
    )
    conn.execute(
        "INSERT INTO behavioral_decisions (decision_id, directive) VALUES (?, ?)",
        ("dec_uden_scope", "Undgå researcher til git-historik"),
    )
    conn.commit()

    _ensure_decision_scope_column(conn)
    _ensure_decision_scope_column(conn)  # anden kørsel må ikke kaste

    cols = {r[1] for r in conn.execute("PRAGMA table_info(behavioral_decisions)")}
    assert "scope_tools" in cols

    # Migreringen opretter kolonnen — den må ikke selv tildele scope. Hvilke
    # beslutninger der har et scope hører på beslutningen. 10/11-2026 stod der
    # en hardkodet UPDATE på et bestemt id; den er fjernet sammen med beslutningen.
    bevaret = conn.execute(
        "SELECT scope_tools FROM behavioral_decisions WHERE decision_id='dec_eksisterende'"
    ).fetchone()[0]
    assert bevaret == '["Task"]', "migreringen overskrev et eksisterende scope"

    urørt = conn.execute(
        "SELECT scope_tools FROM behavioral_decisions WHERE decision_id='dec_uden_scope'"
    ).fetchone()[0]
    assert urørt is None, "migreringen tildelte et scope som beslutningen ikke selv har"
    conn.close()
