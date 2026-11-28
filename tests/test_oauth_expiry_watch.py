"""OAuth-udloebsvagten skal have en kadence, en handler OG kunne se et doende token.

28/11-2026: Google-forbindelsen doede 25/11 og gav 14.724 fejllinjer over knap
tre doegn, foer nogen opdagede det. `refresh_token_expires_in` laa i tokenet
hele tiden (604798 s = 7,0 doegn — Googles loft i «Testing»), men nul steder i
`core/` eller `apps/` laeste det.

Testen her vogter de tre led der hver for sig kan gaa i stykker uden at nogen
ser det: kadencen (ellers kaldes den aldrig), handleren (ellers sover
kadencen), og selve regnestykket (ellers advarer den forkert eller slet ikke).
"""

from __future__ import annotations

import time

from core.services.oauth_expiry_watch import (
    _ADVARSEL_DAGE,
    _levetid_resterende,
    check_oauth_expiry,
)
from core.services.periodic_jobs_scheduler import _SCHEDULE

_JOB = "oauth_expiry_watch"


def test_vagten_har_en_kadence():
    """Uden en kadence i _SCHEDULE bliver jobbet aldrig sat i koe."""
    assert _JOB in _SCHEDULE, (
        f"{_JOB} mangler i _SCHEDULE — saa kaldes den aldrig, praecis som "
        "daemon_health_alert gjorde i ni maaneder"
    )
    assert _SCHEDULE[_JOB].total_seconds() <= 86400, (
        "levetiden er syv doegn; en kadence over et doegn kan misse vinduet"
    )


def test_vagten_har_en_handler():
    """En kadence uden handler sover lige saa stille som en handler uden kadence."""
    from core.services.governance_bootstrap import ensure_default_job_handlers

    registrerede = ensure_default_job_handlers()
    assert _JOB in registrerede, f"{_JOB} er ikke registreret som job-handler"


def test_levetid_regnes_fra_udstedelsestidspunkt():
    """Restlevetiden er levetid minus forloebet tid — ikke levetiden selv."""
    nu = 1_800_000_000.0
    tok = {"refresh_token_expires_in": 604798, "obtained_at": nu - 86400}
    rest = _levetid_resterende(tok, now=nu)
    assert rest is not None
    assert abs(rest - (604798 - 86400)) < 1.0


def test_levetid_er_ukendt_uden_udstedelsestidspunkt():
    """Uden obtained_at kan restlevetiden ikke regnes — og vi gaetter ikke.

    At antage «lige udstedt» er den mest optimistiske af alle antagelser, og
    den forkerte retning at falde i: den skjuler praecis det vi leder efter.
    """
    assert _levetid_resterende({"refresh_token_expires_in": 604798}) is None
    assert _levetid_resterende({"obtained_at": time.time()}) is None
    assert _levetid_resterende({"refresh_token_expires_in": 0, "obtained_at": 1.0}) is None


def test_advarsel_fyrer_inden_for_taersklen():
    """Et token med 4 doegn tilbage skal give advarsel; et med 6 skal ikke."""
    nu = 1_800_000_000.0
    levetid = 7 * 86400

    doende = {"refresh_token_expires_in": levetid, "obtained_at": nu - 3 * 86400}
    sund = {"refresh_token_expires_in": levetid, "obtained_at": nu - 1 * 86400}

    assert _levetid_resterende(doende, now=nu) < _ADVARSEL_DAGE * 86400
    assert _levetid_resterende(sund, now=nu) > _ADVARSEL_DAGE * 86400


def test_check_laeser_butikken_og_rapporterer_uden_at_skrive(monkeypatch):
    """Checken skal kunne se et doende token i den rigtige butik — read-only."""
    from core.services import oauth_store

    nu = 1_800_000_000.0
    levetid = 7 * 86400
    tokens = {
        "u1": {
            "google": {
                "access_token": "a",
                "refresh_token": "r",
                "refresh_token_expires_in": levetid,
                "obtained_at": nu - 6 * 86400,  # 1 doegn tilbage
            }
        }
    }

    monkeypatch.setattr(oauth_store, "get_runtime_state_value", lambda key, default=None: tokens)
    monkeypatch.setattr(oauth_store, "list_providers", lambda uid: sorted(tokens.get(uid, {})))
    monkeypatch.setattr(oauth_store, "get_token", lambda uid, prov: tokens.get(uid, {}).get(prov))

    resultat = check_oauth_expiry(now=nu)

    assert resultat["status"] == "ok"
    assert len(resultat["advarsler"]) == 1
    advarsel = resultat["advarsler"][0]
    assert advarsel["provider"] == "google"
    assert advarsel["dage_tilbage"] < 1.5
    assert resultat["sunde"] == 0


def test_check_taeller_sunde_og_ukendte_hver_for_sig(monkeypatch):
    """Et sundt token og et token uden levetidsoplysning er ikke det samme."""
    from core.services import oauth_store

    nu = 1_800_000_000.0
    tokens = {
        "u1": {
            "google": {
                "access_token": "a",
                "refresh_token": "r",
                "refresh_token_expires_in": 7 * 86400,
                "obtained_at": nu - 3600,  # frisk
            },
            "github": {"access_token": "b", "refresh_token": "r2"},  # ingen levetid
        }
    }

    monkeypatch.setattr(oauth_store, "get_runtime_state_value", lambda key, default=None: tokens)
    monkeypatch.setattr(oauth_store, "list_providers", lambda uid: sorted(tokens.get(uid, {})))
    monkeypatch.setattr(oauth_store, "get_token", lambda uid, prov: tokens.get(uid, {}).get(prov))

    resultat = check_oauth_expiry(now=nu)

    assert resultat["advarsler"] == []
    assert resultat["sunde"] == 1
    grunde = {u["grund"] for u in resultat["ukendte"]}
    assert "levetid-ukendt" in grunde
