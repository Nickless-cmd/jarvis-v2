"""Staged edits — og hvilken samtale kladden tilhører.

Testen findes fordi husets coverage-gate kræver den, men den maaler noget
virkeligt: at to samtaler ikke deler staging-scope.

Målt 19/11-2026, før rettelsen: `_current_session_id()` havde sin egen kopi af
opslaget med kun to kilder — `visible_run_context` og `chat_sessions` — som
begge er døde imports. Den ramte derfor aldrig den levende ContextVar og
returnerede `_default` for enhver session. Konsekvensen var at ALLE samtaler
delte ét staging-scope, så en kladde fra én tur kunne committes fra en anden.
"""
from __future__ import annotations

import pytest

from core.identity.workspace_context import reset_context, set_session_id
from core.tools.staged_edits_tools import (
    STAGED_EDITS_TOOL_HANDLERS,
    _current_session_id,
    _exec_discard_staged_edits,
    _exec_list_staged_edits,
    _exec_stage_write_file,
)


@pytest.fixture
def kontekst():
    """Sæt og ryd den LEVENDE ContextVar — ikke en efterligning af den."""
    tokens = []

    def saet(sid: str):
        tokens.append(set_session_id(sid))

    yield saet

    for tok in reversed(tokens):
        reset_context(tok)


@pytest.fixture(autouse=True)
def ryd_kladde(kontekst):
    """Ryd staged kladder før og efter, så testene ikke lækker til hinanden."""
    yield
    kontekst("_test_ryd")
    _exec_discard_staged_edits({})


# ─────────────────────────── sessions-scope ───────────────────────────


def test_session_id_foelger_konteksten(kontekst):
    """Den konkrete fejl: den stod fast på `_default` uanset kontekst."""
    kontekst("chat-ABC123")
    assert _current_session_id() == "chat-ABC123"


def test_uden_kontekst_falder_den_til_default(kontekst):
    kontekst("")
    assert _current_session_id() == "_default"


def test_to_samtaler_deler_IKKE_kladde(kontekst):
    """Regressionstesten.

    Før rettelsen stod begge sessioner på `_default`, så B ville se A's kladde.
    Nu skal B's liste være tom.
    """
    kontekst("chat-A")
    _exec_stage_write_file({"path": "/tmp/staged_scope_a.txt", "content": "fra A\n"})
    a_set = _exec_list_staged_edits({})
    assert a_set.get("count", 0) >= 1, f"A skulle have mindst én kladde, fik {a_set}"

    kontekst("chat-B")
    b_set = _exec_list_staged_edits({})
    assert b_set.get("count", 0) == 0, (
        "samtale B kan se samtale A's kladde — de deler staging-scope: "
        f"{b_set}"
    )


def test_samme_samtale_ser_sin_egen_kladde(kontekst):
    kontekst("chat-C")
    _exec_stage_write_file({"path": "/tmp/staged_scope_c.txt", "content": "fra C\n"})
    c_set = _exec_list_staged_edits({})
    assert c_set.get("count", 0) >= 1, f"C skulle se sin egen kladde, fik {c_set}"


# ─────────────────────────── registreringen ───────────────────────────


def test_alle_handlers_er_registreret():
    for navn in (
        "stage_edit_file",
        "stage_write_file",
        "list_staged_edits",
        "commit_staged_edits",
        "discard_staged_edits",
    ):
        assert navn in STAGED_EDITS_TOOL_HANDLERS, f"{navn} mangler i handler-registret"
