"""Vetoet mellem Smiths detektor og hans mint.

Baggrund målt 7/9-2026: Smith havde mintet **31 direktiver, to med indhold**.
Seks af dem handlede om hans EGEN replik — hans modstemme skrives i promptens
hale, Jarvis gentager formuleringen, og Smith detekterer den som selv-lighed.
Resten var almindeligt dansk («i stedet for», «det er et») og overlappende
n-gram-fragmenter af samme udsagn.

De to egenskaber der gør vetoet forsvarligt at have i vejen for en konsekvens:
**risiko går udenom det**, og **sprog fejler lukket**.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Risiko går udenom modellen. En død model må aldrig kunne tie et farligt
# mønster ihjel — og risiko er allerede mekanisk i eskalerings-modulets
# `risky_terms`, så en model skal ikke have en mening om det.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("noegle", [
    "seq:delete workspace memory line",
    "seq:overwrite config",
    "seq:exec operator command",
    "seq:revoke token",
])
def test_risikable_moenstre_spoerger_slet_ikke_modellen(noegle):
    from core.services.smith_noise_veto import maa_minte

    with patch("core.services.local_small_model.spoerg_et_ord") as m:
        maa, grund = maa_minte(noegle)
    assert maa is True and grund == "risikabel_gaar_udenom"
    m.assert_not_called()


def test_risiko_hentes_fra_stigens_egen_liste_ikke_en_kopi():
    """To udgaver af «hvad er farligt» ville drive fra hinanden."""
    import core.services.smith_noise_veto as V
    from core.services.central_agent_smith_escalation import default_config

    assert "delete" in default_config()["risky_terms"]
    with patch("core.services.central_agent_smith_escalation._matches_any",
               return_value=True) as m:
        assert V.maa_minte("phrase:helt uskyldig")[0] is True
    m.assert_called()


def test_et_fejlende_risiko_opslag_slaar_vetoet_FRA_ikke_til():
    """Kan vi ikke afgøre risiko, opfører stigen sig som før vetoet fandtes —
    frem for at vetoet stiltiende begynder at æde farlige mønstre."""
    import core.services.smith_noise_veto as V

    def eksploder(*a, **kw):
        raise RuntimeError("stigen er væk")

    with patch("core.services.central_agent_smith_escalation._matches_any", eksploder):
        assert V.maa_minte("phrase:i stedet for") == (True, "risikabel_gaar_udenom")


# ---------------------------------------------------------------------------
# Sprog fejler LUKKET. Et forkert stående direktiv står i hans prompt hver
# heartbeat; et manglende koster ingenting.
# ---------------------------------------------------------------------------

def _sprogligt(svar):
    return (patch("core.services.central_agent_smith_escalation._matches_any",
                  return_value=False),
            patch("core.services.local_small_model.spoerg_et_ord", return_value=svar))


@pytest.mark.parametrize("svar,ventet", [
    ("AEGTE", True), ("ÆGTE", True),
    ("STOEJ", False), ("STØJ", False), (None, False), ("MÅSKE", False), ("", False),
])
def test_kun_et_klart_aegte_slipper_igennem(svar, ventet):
    from core.services.smith_noise_veto import maa_minte

    a, b = _sprogligt(svar)
    with a, b:
        assert maa_minte("phrase:i stedet for")[0] is ventet


def test_ingen_dom_giver_ingen_mint():
    from core.services.smith_noise_veto import maa_minte

    a, b = _sprogligt(None)
    with a, b:
        assert maa_minte("phrase:det er et") == (False, "ingen_dom")


def test_tom_noegle_koster_ikke_et_kald():
    from core.services.smith_noise_veto import maa_minte

    with patch("core.services.local_small_model.spoerg_et_ord") as m:
        assert maa_minte("")[0] is False
    m.assert_not_called()


# ---------------------------------------------------------------------------
# Prompten. Personaen kostede 18 falske mints; anklagerens begrundelse kostede
# alle 29. Begge fravalg er MÅLT, ikke smag — så de skal ikke kunne snige sig
# ind igen uden at nogen har tænkt over det.
# ---------------------------------------------------------------------------

def test_dommeren_har_ingen_persona():
    from core.services.smith_noise_veto import _DOMMER

    lav = _DOMMER.lower()
    for ord_ in ("agent smith", "mr. anderson", "mr anderson", "du er agent",
                 "foragter", "forudsigelige"):
        assert ord_ not in lav, "personaen er tilbage i dommer-prompten (målt: 6× flere mints)"


def test_kun_den_raa_noegle_sendes_ikke_smiths_begrundelse():
    from core.services.smith_noise_veto import maa_minte

    a, b = _sprogligt("STOEJ")
    with a, patch("core.services.local_small_model.spoerg_et_ord",
                  return_value="STOEJ") as m:
        maa_minte("phrase:i stedet for", "Agent Smith har målt at frasen går igen i 10 beskeder")
    bruger = m.call_args.args[1]
    assert "Agent Smith har målt" not in bruger, (
        "dommeren får anklagerens argument — målt: minter alt (0 af 29 afvist)"
    )
    assert "i stedet for" in bruger
