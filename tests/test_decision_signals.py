"""Cooldown-tilstanden skal kunne skrives — ellers fyrer triggeren hver runde.

## Hvorfor testen findes

Målt 22/10-2026: `decision_signals` skrev til `runtime_state_kv(value, ...)`,
men tabellen har kolonnen `value_json`. Skrivningen fejlede derfor HVER gang,
blev fanget af en bred `except` og logget som en warning:

    decision_signals: cannot write last_fired: table runtime_state_kv has no
    column named value

Konsekvensen var ikke en manglende log-linje. Uden skrevet tilstand kan
`_cooldown_active` aldrig se at triggeren lige har fyret — så ALLE triggere
fyrede i hver eneste runde. En påmindelse der kommer hver runde er ikke en
påmindelse, den er støj, og den drukner i præfikset.

Fejlen var usynlig fordi begge sider af kontrakten fejlede ens: læsningen
spurgte også efter `value`, så et tomt svar så ud som «aldrig fyret».
"""
from __future__ import annotations

from core.services.decision_signals import _read_last_fired, _write_last_fired


def test_skrevet_tid_staar_der_naar_vi_laeser_igen():
    """Den ægte søm: skriv og læs tilbage gennem de rigtige funktioner."""
    did = "dec_test_cooldown_skrivning"
    ts = "2026-10-22T12:00:00+00:00"

    _write_last_fired(did, ts)
    tilbage = _read_last_fired(did)

    assert tilbage is not None, (
        "last_fired kunne ikke læses tilbage efter skrivning — så kan cooldown "
        "aldrig se at triggeren har fyret, og den fyrer i hver runde"
    )
    assert str(tilbage).startswith("2026-10-22T12:00:00"), (
        f"forkert værdi læst tilbage: {tilbage!r} — peger på kolonne-mismatch "
        "mellem koden (value) og skemaet (value_json)"
    )


def test_ukendt_noegle_giver_none():
    assert _read_last_fired("dec_findes_slet_ikke_12345") is None
