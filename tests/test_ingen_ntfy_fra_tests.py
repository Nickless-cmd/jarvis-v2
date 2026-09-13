"""Testmiljøet maa ALDRIG ringe paa hans telefon — heller ikke via ntfy.

MAALT 12/9-2026 i `jarvis-heartbeat`, kl. 23:31 og 23:40:

    ⚠ Central greb ALVORLIG fejl: skill/skill_scan — RuntimeError: scanner exploded
    ⚠ Central greb ALVORLIG fejl: auth/tool_access — RuntimeError: boom
    ⚠ Central greb ALVORLIG fejl: privacy/cross_user_share — RuntimeError: boom

Ingen af dem var aegte. `scanner exploded` rejses i `tests/test_gate_skill.py:55`,
og `boom` er testfixturens standardfejl overalt i suiten. En testkoersel ringede
paa hans telefon midt om natten med ordet ALVORLIG paa.

Discord-porten fik samme spaerre tidligere samme dag. Den daekkede ikke denne —
det er en anden vej ud, og derfor er der to vagter, én pr. port.
"""
import os

import core.services.ntfy_gateway as ng


def test_ntfy_sender_intet_under_pytest():
    """Denne test KOERER under pytest og maaler derfor sig selv."""
    assert "PYTEST_CURRENT_TEST" in os.environ, "markoeren mangler — vagten er blind"
    svar = ng.send_notification("denne besked maa ALDRIG naa en telefon", title="prøve")
    assert svar.get("status") == "skipped"
    assert svar.get("reason") == "pytest"


def test_vagten_staar_FOER_enhver_udsendelse():
    """Ligger den efter hook-kaldet eller konfigurations-opslaget, kan en fejl
    undervejs stadig sende."""
    import inspect
    k = inspect.getsource(ng.send_notification)
    krop = k[k.index('"""', k.index('"""') + 3) + 3:]
    assert "PYTEST_CURRENT_TEST" in krop
    for senere in ("requests", "urlopen", "_post", "hook"):
        if senere in krop:
            assert krop.index("PYTEST_CURRENT_TEST") < krop.index(senere), \
                f"vagten staar efter «{senere}»"
