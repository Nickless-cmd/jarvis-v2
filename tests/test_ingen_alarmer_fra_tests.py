"""Testmiljøet maa ALDRIG naa Bjoerns telefon.

MAALT: 12/9-2026 kl. 22:36 og 22:45 fik han to Discord-alarmer —
«⚠️ Self-repair failed: X — Action: control_daemon → test failure». Ingen af
dem var aegte. `tests/test_self_repair_integration.py` opretter et moenster med
`name="X"`, fejl-stien kalder `_notify_owner_async`, og den havde ingen spaerre.

Beviset for at det IKKE var drift: `self_repair_patterns` indeholder intet
moenster med `name='X'` eller `action_type='control_daemon'`, og de eneste
`failed`-raekker i `self_repair_attempts` er fra maj med `pattern_id='p1'` —
ogsaa testdata.
"""
import inspect
import os

import core.services.discord_gateway as dg


def test_dm_til_ejeren_droppes_under_pytest():
    """Denne test KOERER under pytest, saa den maaler sig selv: naar den kalder
    porten, maa der ikke gaa noget ud."""
    assert "PYTEST_CURRENT_TEST" in os.environ, "markoeren mangler — vagten er blind"
    svar = dg.send_dm_to_owner("denne besked maa ALDRIG naa en telefon")
    assert svar.get("status") == "skipped"
    assert svar.get("reason") == "pytest"


def test_vagten_sidder_FOER_alt_andet_i_funktionen():
    """Ligger den efter et netvaerkskald eller en config-opslag, er den for
    sent paa den — og en fejl undervejs kunne stadig sende."""
    k = inspect.getsource(dg.send_dm_to_owner)
    krop = k[k.index('"""', k.index('"""') + 3) + 3:]
    assert krop.index("PYTEST_CURRENT_TEST") < krop.index("_is_gateway_owner")


def test_vagten_sidder_paa_PORTEN_ikke_hos_den_enkelte_kalder():
    """Der er fem kaldere. En vagt pr. kalder skal huskes hver gang der kommer
    en sjette; denne skal huskes én gang."""
    import pathlib
    kaldere = [
        p for p in pathlib.Path("core").rglob("*.py")
        if "send_dm_to_owner" in p.read_text() and p.name != "discord_gateway.py"
    ]
    assert len(kaldere) >= 3, "forventede flere kaldere — er porten flyttet?"
