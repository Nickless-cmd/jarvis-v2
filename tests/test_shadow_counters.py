"""Skygge-taellere der overlever en genstart.

Set 9/9-2026: kontrakt-skyggen viste 35 maalte kald, jeg deployede, og naeste
aflaesning viste 1. Alle tre skygger skrev ABSOLUTTE tal — saa en genstart
nulstillede hukommelsen, og foerste observation bagefter overskrev det
akkumulerede i cachen.

Det betyder at «skyggen har maalt X over flere dage» ikke kunne siges — og
det er praecis den saetning en beslutning om at HAANDHAEVE skal hvile paa.
"""
from __future__ import annotations

import pytest

from core.services.shadow_counters import flet


@pytest.fixture
def cache(isolated_runtime):
    from core.services import shared_cache
    return shared_cache


def test_foerste_gemning_skriver_tallene(cache):
    sidst: dict[str, int] = {}
    flet("t:1", {"maalt": 3, "fejl": 0}, sidst)
    assert cache.get("t:1")["maalt"] == 3
    assert sidst == {"maalt": 3, "fejl": 0}


def test_kun_TILVAEKSTEN_laegges_til(cache):
    sidst: dict[str, int] = {}
    flet("t:2", {"maalt": 3}, sidst)
    flet("t:2", {"maalt": 5}, sidst)
    assert cache.get("t:2")["maalt"] == 5


def test_en_GENSTART_nulstiller_ikke_det_akkumulerede(cache):
    """Selve fejlen: hukommelsen starter forfra, cachen maa ikke."""
    sidst: dict[str, int] = {}
    flet("t:3", {"maalt": 35}, sidst)

    # genstart: ny proces, tom hukommelse, tom sidst-gemt
    ny_sidst: dict[str, int] = {}
    flet("t:3", {"maalt": 1}, ny_sidst)

    assert cache.get("t:3")["maalt"] == 36, "genstarten aad 35 maalinger"


def test_TO_processer_laegger_sammen_frem_for_at_overskrive(cache):
    """`jarvis-api` og `jarvis-runtime` skriver samme noegle. Foer lagde den
    sidste sig oveni den anden."""
    api: dict[str, int] = {}
    runtime: dict[str, int] = {}
    flet("t:4", {"maalt": 10}, api)
    flet("t:4", {"maalt": 4}, runtime)
    flet("t:4", {"maalt": 12}, api)
    assert cache.get("t:4")["maalt"] == 16


def test_ekstra_felter_erstattes_frem_for_at_summeres(cache):
    """`_top` er et oejebliksbillede, ikke en taeller."""
    sidst: dict[str, int] = {}
    flet("t:5", {"maalt": 1}, sidst, ekstra={"_top": {"a": 1}})
    flet("t:5", {"maalt": 2}, sidst, ekstra={"_top": {"b": 9}})
    v = cache.get("t:5")
    assert v["_top"] == {"b": 9} and v["maalt"] == 2


def test_den_kaster_aldrig(monkeypatch):
    """En taeller maa ikke kunne vaelte det den taeller."""
    import core.services.shared_cache as SC
    monkeypatch.setattr(SC, "get",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("nede")))
    flet("t:6", {"maalt": 1}, {})


def test_skyggerne_bruger_den(isolated_runtime, monkeypatch):
    """Koblingen: hvis ingen kalder den, er fixet kun en fil."""
    import inspect
    from core.services import (approval_bridge_shadow, settlement_shadow,
                               tool_contract_shadow)
    for m in (approval_bridge_shadow, settlement_shadow, tool_contract_shadow):
        kilde = inspect.getsource(m)
        assert "shadow_counters" in kilde, m.__name__
        assert "_sidst_gemt" in kilde, m.__name__
