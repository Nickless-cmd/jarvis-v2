"""Vagter for de tavse fald i ``simple_tools`` (31/10-2026).

Fælles form for alle 14: en ``except`` returnerer en værdi der er IDENTISK med
den legitime tilstand, så en fejl ser ud som normal drift.

- ``base = WORKSPACE_DIR`` betyder «workspace-opslag fejlede» — men ser ud som
  et normalt opslag, og skriver MEMORY.md i shared/ hvor prompten ikke læser.
- ``_role, _scope = "", ""`` betyder «unbound» = BETROET. Et kast giver altså
  MERE adgang, ikke mindre.
- ``_trust_block = None`` betyder «workspace er betroet» — også når tjekket
  aldrig blev gennemført.
- ``{"error": str(exc), "status": "error"}`` er korrekt, men uden ``exc_info``
  mistes stack-tracen.

Rettelsen ændrer ikke retningen: returværdien er den samme. Det der tilføjes er
et spor. Testene her beviser BEGGE halvdele — at fejlen logger, OG at
returværdien stadig er den fail-soft værdi kalderne forventer.
"""

from __future__ import annotations

import logging

import core.tools.simple_tools as st


def _kaster(exc: Exception):
    """En callable der kaster — til monkeypatch uden lambda-hack."""

    def _f(*_a, **_k):
        raise exc

    return _f


def _logget(caplog, tekst: str) -> bool:
    return any(tekst in r.getMessage() for r in caplog.records)


# ── canonical_identity_file_path ────────────────────────────────────────────


def test_workspace_opslag_fejler_logger_og_bevarer_shared_fallback(monkeypatch, caplog):
    """Faldet til shared/ skal STADIG ske — men ikke i tavshed.

    Uden sporet er dette præcis den bug der drew MEMORY.md fra hinanden
    2026-09-05: skrivningen lander et sted prompten ikke læser.
    """
    monkeypatch.setattr(
        "core.runtime.workspace_paths.workspace_dir_or_owner",
        _kaster(RuntimeError("intet workspace")),
    )
    with caplog.at_level(logging.WARNING, logger="core.tools.simple_tools"):
        sti = st.canonical_identity_file_path("MEMORY.md")

    assert sti.name == "MEMORY.md", "fail-soft skal bevares"
    assert _logget(caplog, "workspace-opslag fejlede"), "faldet var tavst"


def test_shared_fallback_fejler_logger_og_returnerer_uoplost_sti(monkeypatch, caplog):
    """Andet fald: stien kan ikke opløses. Vi returnerer den alligevel — men lydt."""
    monkeypatch.setattr(
        "core.services.prompt_sections.workspace_files._resolve_with_shared_fallback",
        _kaster(OSError("kunne ikke opløses")),
    )
    with caplog.at_level(logging.WARNING, logger="core.tools.simple_tools"):
        sti = st.canonical_identity_file_path("USER.md")

    assert sti.name == "USER.md", "fail-soft skal bevares"
    assert _logget(caplog, "shared-fallback fejlede"), "faldet var tavst"


def test_normalt_opslag_stoejer_ikke(monkeypatch, caplog):
    """Normal drift må ikke skrive advarsler — ellers drukner de ægte fejl."""
    with caplog.at_level(logging.WARNING, logger="core.tools.simple_tools"):
        sti = st.canonical_identity_file_path("MEMORY.md")

    assert sti.name == "MEMORY.md"
    assert not [r for r in caplog.records if "workspace-opslag" in r.getMessage()]


# ── _execute_tool_force_impl ────────────────────────────────────────────────


def test_force_handler_der_kaster_logger_og_bevarer_error(monkeypatch, caplog):
    """Handler-kast: status=error er korrekt — men stack-tracen må ikke forsvinde."""
    monkeypatch.setitem(st._FORCE_HANDLERS, "_test_kaster", _kaster(RuntimeError("bum")))
    with caplog.at_level(logging.WARNING, logger="core.tools.simple_tools"):
        res = st._execute_tool_force_impl("_test_kaster", {})

    assert res["status"] == "error", "returværdien skal vaere uaendret"
    assert "bum" in res["error"]
    assert _logget(caplog, "kastede i force-stien"), "faldet var tavst"


def test_emotional_gate_fejl_logger_og_blokerer_ikke(monkeypatch, caplog):
    """Gaten der kaster må ALDRIG blokere — men den skal sige det.

    Et kast her betyder at gaten slet ikke blev vurderet, så en blokering der
    SKULLE være sket, udebliver. Tavshed gør den usynlig.
    """
    monkeypatch.setattr(
        "core.services.emotional_controls.apply_emotional_controls",
        _kaster(RuntimeError("affekt-motor nede")),
    )
    monkeypatch.setitem(
        st._FORCE_HANDLERS, "_test_ok", lambda _a: {"status": "ok", "resultat": "kørt"}
    )
    with caplog.at_level(logging.WARNING, logger="core.tools.simple_tools"):
        res = st._execute_tool_force_impl("_test_ok", {})

    assert res.get("resultat") == "kørt", "gaten må ikke blokere naar den fejler"
    assert _logget(caplog, "emotional_controls-gate kastede"), "faldet var tavst"


# ── get_tool_definitions ────────────────────────────────────────────────────


def test_rolle_opslag_fejler_logger_og_bevarer_owner_adgang(monkeypatch, caplog):
    """``""`` giver owner-adgang i filteret — et kast UDVIDER altså listen.

    Fail-open er et bevidst availability-valg. Det må bare ikke være usynligt:
    ellers kan ingen se at en medlemssession fik owner-værktøjer.
    """
    monkeypatch.setattr(
        "core.identity.workspace_context.effective_role",
        _kaster(RuntimeError("rolle ukendt")),
    )
    with caplog.at_level(logging.WARNING, logger="core.tools.simple_tools"):
        ud = st.get_tool_definitions()

    assert isinstance(ud, list) and ud, "fail-open skal bevares"
    assert _logget(caplog, "rolle-opslag kastede"), "faldet var tavst"


def test_normal_rolle_stoejer_ikke(caplog):
    """Owner-opslag der virker må ikke skrive en advarsel."""
    with caplog.at_level(logging.WARNING, logger="core.tools.simple_tools"):
        st.get_tool_definitions()

    assert not [r for r in caplog.records if "rolle-opslag" in r.getMessage()]
