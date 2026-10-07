"""A/B'ens arm: stabil, respektfuld over for composeren, og nul som fallback.

Knappen er binaer, og det er maalt: probet mod API'en 5/10 giver
`reasoning_effort` high/medium/low alle 296-317 raeson-tokens, mens
spredningen inden for `high` alene er 290-358. Havde armen vaeret bygget paa
«medium», ville A/B'en have vist «ingen forskel» — ikke fordi raesonnering er
gratis, men fordi knappen aldrig blev drejet.
"""
from __future__ import annotations

import subprocess
import sys

from core.services.raesonnering_eksperiment import (
    ARM_DAEMPET,
    ARM_FULD,
    arm_for_run,
    daemp_krop,
)

_KROP = {"reasoning_effort": "high", "thinking": {"type": "enabled"}}


def test_armen_er_stabil_paa_tvaers_af_PROCESSER():
    """Den fael de hele modulet findes for.

    `hash()` paa en streng er saltet pr. proces (PYTHONHASHSEED), og prompten
    bygges i BAADE jarvis-api og jarvis-runtime. Med `hash()` ville samme run
    kunne havne i hver sin arm i de to processer og blande forsoeget.
    Derfor maales det i en FREMMED proces med et andet salt — en maaling i
    denne proces kan ikke se fejlen.
    """
    nøgler = [f"visible-{i:04d}" for i in range(40)]
    her = [arm_for_run(k, procent=50) for k in nøgler]
    kode = (
        "import sys; sys.path.insert(0, '.');"
        "from core.services.raesonnering_eksperiment import arm_for_run;"
        f"print(','.join(arm_for_run(k, procent=50) for k in {nøgler!r}))"
    )
    ude = subprocess.run(
        [sys.executable, "-c", kode],
        capture_output=True, text=True, check=True,
        env={"PYTHONHASHSEED": "12345", "PATH": "/usr/bin:/bin"},
    )
    assert ude.stdout.strip().split(",") == her


def test_nul_procent_er_nul_eksponering():
    assert all(arm_for_run(f"r{i}", procent=0) == ARM_FULD for i in range(50))


def test_hundrede_procent_rammer_alle():
    assert all(arm_for_run(f"r{i}", procent=100) == ARM_DAEMPET for i in range(50))


def test_tomt_run_id_er_altid_fuld():
    """Uden en stabil noegle kunne runnet skifte arm mellem runder, og en tur
    med halvdelen af runderne i hver arm maaler ingenting."""
    for tom in ("", "   ", None):
        assert arm_for_run(tom or "", procent=100) == ARM_FULD


def test_andelen_rammer_omtrent_det_bestilte():
    n = 2000
    ramt = sum(arm_for_run(f"visible-{i}", procent=20) == ARM_DAEMPET for i in range(n))
    assert 0.15 * n < ramt < 0.25 * n, f"20 % bad om ~400, fik {ramt}"


def test_fuld_arm_lader_kroppen_vaere_BIT_identisk():
    """Arm «fuld» skal vaere dagens adfaerd, ikke en ny vej der ligner den."""
    krop, daempet = daemp_krop(dict(_KROP), "visible-x", procent=0)
    assert daempet is False
    assert krop == _KROP


def test_daempet_arm_slaar_thinking_fra_og_fjerner_den_doede_knap():
    krop, daempet = daemp_krop(dict(_KROP), "visible-x", procent=100)
    assert daempet is True
    assert krop == {"thinking": {"type": "disabled"}}
    assert "reasoning_effort" not in krop, "et modsat signal maa ikke staa tilbage"


def test_et_eksplicit_valg_i_composeren_overskrives_IKKE():
    """Vaelger Bjoern «deep», er det hans valg. Vaelger han «fast», er der
    intet at daempe."""
    for tilstand in ("deep", "fast", "DEEP"):
        krop, daempet = daemp_krop(dict(_KROP), "visible-x",
                                   thinking_mode=tilstand, procent=100)
        assert daempet is False, tilstand
        assert krop == _KROP


def test_en_fejlende_config_giver_NUL_eksponering(monkeypatch):
    """En maaling der tager en andel fordi en config-laesning fejlede, er en
    aendring ingen har besluttet."""
    import core.services.raesonnering_eksperiment as R

    def _braek():
        raise RuntimeError("config utilgaengelig")
    monkeypatch.setattr("core.runtime.settings.load_settings", _braek)
    assert R._procent() == 0
    assert arm_for_run("visible-x") == ARM_FULD


def test_en_vanvittig_config_vaerdi_klemmes_ikke_kastes(monkeypatch):
    import core.services.raesonnering_eksperiment as R

    class _S:
        raesonnering_daempet_procent = 9999
    monkeypatch.setattr("core.runtime.settings.load_settings", lambda: _S())
    assert R._procent() == 100

    class _T:
        raesonnering_daempet_procent = "ikke-et-tal"
    monkeypatch.setattr("core.runtime.settings.load_settings", lambda: _T())
    assert R._procent() == 0
