"""Heartbeat-slagenes FORMÅL — feltet der gør «hvad laver heartbeat?» besvarligt.

Rod (Bjørn 17/11-2026): spørgsmålet kunne ikke besvares ud af data, fordi
`heartbeat_runtime_ticks` kun bar `action_type`. Overlevelse og arbejde havde
samme kadence og samme tabel, så arbejdet betalte for overlevelsens ure.

Disse tests bevogter tre ting:
1. klassificeringen selv (de fire formål + de tre «mangler et formål»)
2. at feltet faktisk SKRIVES og LÆSES gennem persistence-laget
3. at en ny gren i koden ikke kan snige sig ind uklassificeret
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from core.services.heartbeat_purpose import (
    ALL_PURPOSES,
    DISPATCH,
    IDLE,
    INNER_LIFE,
    REAL_PURPOSES,
    SESSION,
    SURVIVAL,
    UNKNOWN,
    WORK,
    action_types_in,
    describe,
    is_real_purpose,
    known_action_types,
    purpose_for_action,
)

_REPO = Path(__file__).resolve().parents[1]
_HEARTBEAT_RUNTIME = _REPO / "core" / "services" / "heartbeat_runtime.py"


# ── 1. Klassificeringen ─────────────────────────────────────────────────────


def test_de_fire_formaal_er_de_eneste_der_taeller():
    """Bogføring, tomgang og ukendt er mangel på formål — ikke formål."""
    assert set(REAL_PURPOSES) == {SURVIVAL, SESSION, INNER_LIFE, WORK}
    for p in (DISPATCH, IDLE, UNKNOWN):
        assert p in ALL_PURPOSES
        assert not is_real_purpose(p)
    for p in REAL_PURPOSES:
        assert is_real_purpose(p)


@pytest.mark.parametrize(
    "action_type,forventet",
    [
        # overlevelse: systemets egen tilstand
        ("progress_lifecycles", SURVIVAL),
        ("decay_forgotten_signals", SURVIVAL),
        ("cleanup_stale_signals", SURVIVAL),
        # session: den ENESTE der leverer til en samtale
        ("webchat-heartbeat-proposal", SESSION),
        # indre liv: filer og tilstande jeg selv læser senere
        ("run_sleep_batch", INNER_LIFE),
        ("write_chronicle_entry", INNER_LIFE),
        ("autonomous_daily_note", INNER_LIFE),
        # arbejde: forsøger at gøre noget i verden
        ("act_on_initiative", WORK),
        ("follow_open_loop", WORK),
        ("process_contract_writes", WORK),
        # bogføring og tomgang
        ("tick_dispatched", DISPATCH),
        ("productive_idle", IDLE),
    ],
)
def test_klassificering_paa_observeret_grundlag(action_type, forventet):
    assert purpose_for_action(action_type) == forventet


def test_kun_webchat_er_session():
    """`act_on_initiative` og `refresh_memory_context` bærer også et
    `session_id` i deres artefakt — men de skriver til task/flow og hukommelse.
    Reglen er «leverer TIL en samtale», ikke «kender en session»."""
    assert action_types_in(SESSION) == frozenset({"webchat-heartbeat-proposal"})


def test_ukendt_type_bliver_ukendt_ikke_gaettet():
    assert purpose_for_action("en_gren_der_ikke_findes") == UNKNOWN
    assert purpose_for_action("") == UNKNOWN
    assert purpose_for_action(None) == UNKNOWN  # type: ignore[arg-type]


def test_describe_taeller_alle_klasser():
    d = describe()
    assert d["counts"][UNKNOWN] == 0, "ukendt skal være tom — ellers er noget uklassificeret"
    assert sum(d["counts"].values()) == len(known_action_types())


# ── 2. VAGTEN: en ny gren må ikke kunne snige sig ind uklassificeret ────────


def test_alle_action_types_i_koden_er_klassificeret():
    """Læser KILDEN, ikke en kopi. En ny `action_type == "..."`-gren i
    heartbeat_runtime.py uden en klasse fælder denne test — ellers ville
    feltet tavst blive forældet, hvilket er præcis fejlformen fra
    `productive_idle` (2.876 kald, ingen opdagede det)."""
    assert _HEARTBEAT_RUNTIME.exists(), f"mangler {_HEARTBEAT_RUNTIME}"
    kilde = _HEARTBEAT_RUNTIME.read_text(encoding="utf-8")
    i_koden = set(re.findall(r'action_type\s*==\s*"([a-z_\-]+)"', kilde))
    assert i_koden, "fandt ingen action_type-grene — er regexen holdt op med at matche?"
    uklassificerede = sorted(i_koden - known_action_types())
    assert not uklassificerede, (
        "nye heartbeat-grene uden formål: "
        f"{uklassificerede} — tilføj dem i core/services/heartbeat_purpose.py"
    )
