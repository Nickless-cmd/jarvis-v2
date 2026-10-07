"""ÉN model pr. session — måltallet og kanterne (3/10-2026).

Bjørn: «stortset alle mine beskeder kolder starter». Målt på CT105: runderne
inde i en tur ligger på 95-96,5 % cache-hit, åbneren på 50-56 %, og hit-tallene
gentager sig (16.512 ×2, 19.584 ×4, 10.112 ×2) på input fra 41k til 126k
tokens. Tre modeller betjente nabo-ture i samme samtale. DeepSeek cacher per
model, så de deler ingen cache uanset hvor byte-stabil prompten er.

Testene pinner de fire ting der skal holde:

1. Låsen afgør efter første tur, så præfikset rammer samme cache.
2. Compaction slipper den — dér er historikken skrevet om alligevel.
3. En død model kan ikke kile sessionen fast (`release`).
4. Begge koblinger i `visible_runs` findes, og et eksplicit valg vinder.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

from core.services import session_model_pin as smp


@pytest.fixture(autouse=True)
def _rent_lager(monkeypatch):
    """Lageret i en dict — ingen DB, og ingen læk mellem tests."""
    lager: dict[str, object] = {}
    monkeypatch.setattr(smp, "_state_get",
                        lambda sid: dict(lager.get(smp._key(sid)) or {}))

    def _saet(sid, payload):
        if payload is None:
            lager.pop(smp._key(sid), None)
        else:
            lager[smp._key(sid)] = dict(payload)
    monkeypatch.setattr(smp, "_state_set", _saet)
    monkeypatch.setattr(smp, "_compact_epoch", lambda _sid: 7)
    return lager


# ── Selve låsen ───────────────────────────────────────────────────────────

def test_foerste_tur_laaser_routerens_valg():
    """Routeren skal vælge FØRSTE gang — ellers kan låsen aldrig sættes."""
    assert smp.resolve("s1", "deepseek", "deepseek-flash") == (
        "deepseek", "deepseek-flash", "router")
    assert smp.get_pinned("s1") == ("deepseek", "deepseek-flash")


def test_naeste_tur_bruger_LAASEN_ikke_routeren():
    """Kernen. Routeren foreslår noget andet; låsen vinder, så præfikset
    rammer samme cache."""
    smp.resolve("s1", "deepseek", "deepseek-flash")
    assert smp.resolve("s1", "deepseek", "deepseek-v4-flash") == (
        "deepseek", "deepseek-flash", "pin")


def test_et_andet_PAR_i_en_anden_session_blandes_ikke():
    smp.resolve("a", "deepseek", "deepseek-flash")
    smp.resolve("b", "ollama", "glm-5.2:cloud")
    assert smp.get_pinned("a") == ("deepseek", "deepseek-flash")
    assert smp.get_pinned("b") == ("ollama", "glm-5.2:cloud")


def test_compaction_slipper_laasen(monkeypatch):
    """Ved compaction skrives historikken om og cachen brydes alligevel — så
    må routeren vælge forfra uden at det koster noget. Samme kilde som
    `session_tool_pin`, så de to låse slipper samtidig."""
    smp.resolve("s1", "deepseek", "deepseek-flash")
    monkeypatch.setattr(smp, "_compact_epoch", lambda _sid: 8)
    assert smp.get_pinned("s1") is None
    assert smp.resolve("s1", "deepseek", "deepseek-v4-flash") == (
        "deepseek", "deepseek-v4-flash", "router")


# ── Kanterne ──────────────────────────────────────────────────────────────

def test_release_forhindrer_at_en_doed_model_kiler_sessionen():
    """Uden `release` ville hver tur vælge den døde model igen, fejle, og
    låsen aldrig ændre sig."""
    smp.resolve("s1", "deepseek", "deepseek-flash")
    smp.release("s1", grund="provider-fejl")
    assert smp.get_pinned("s1") is None
    assert smp.resolve("s1", "ollama", "glm-5.2:cloud")[2] == "router"


def test_release_paa_en_ulaast_session_kaster_ikke():
    smp.release("findes-ikke")
    smp.release("")


def test_tom_session_eller_tomt_par_laaser_intet():
    assert smp.get_pinned("") is None
    assert smp.pin("", "deepseek", "x") is None
    assert smp.pin("s1", "", "") is None
    assert smp.get_pinned("s1") is None


def test_halvt_par_laases_ikke(_rent_lager):
    """En udbyder uden model (eller omvendt) er ikke et brugbart valg."""
    assert smp.resolve("s1", "deepseek", "")[2] == "router"
    assert smp.get_pinned("s1") is None
    assert smp.resolve("s1", "", "deepseek-flash")[2] == "router"
    assert smp.get_pinned("s1") is None


def test_mellemrum_omkring_navnene_er_ikke_et_nyt_par():
    smp.resolve("s1", " deepseek ", " deepseek-flash ")
    assert smp.get_pinned("s1") == ("deepseek", "deepseek-flash")


def test_killswitch_slaar_laasen_HELT_fra(monkeypatch):
    monkeypatch.setattr(smp, "pin_enabled", lambda: False)
    assert smp.resolve("s1", "deepseek", "deepseek-flash")[2] == "router"
    assert smp.get_pinned("s1") is None
    # Og routerens valg gaar uaendret igennem hver tur.
    assert smp.resolve("s1", "ollama", "glm-5.2:cloud")[:2] == ("ollama", "glm-5.2:cloud")


def test_laasen_er_TIL_som_standard_ogsaa_naar_settings_kaster(monkeypatch):
    """Fail-safe mod den NYE adfærd: kan vi ikke læse indstillingen, låser vi.
    Modsat retning ville gøre en konfigurations-fejl til en tavs regression
    tilbage til kolde åbnere."""
    import core.runtime.settings as st
    monkeypatch.setattr(st, "load_settings",
                        lambda: (_ for _ in ()).throw(RuntimeError("i stykker")))
    assert smp.pin_enabled() is True


def test_et_gemt_par_uden_epoke_er_ikke_gyldigt(_rent_lager):
    """Et halvskrevet lager må ikke læses som en lås — fail mod routeren."""
    _rent_lager[smp._key("s1")] = {"provider": "deepseek", "model": "deepseek-flash"}
    assert smp.get_pinned("s1") is None


# ── Koblingen ─────────────────────────────────────────────────────────────

def test_begge_koblinger_i_visible_runs_findes():
    """En lås ingen kalder er død kode — husets hyppigste mønster. Og uden
    `release` kiler en død model sessionen fast, så BEGGE skal sidde."""
    src = pathlib.Path("core/services/visible_runs.py").read_text()
    ast.parse(src)
    assert "session_model_pin as _smp" in src, "laasen er ikke koblet"
    assert "_smp.resolve(" in src, "laasen afgoer ikke modellen"
    assert "_smp_rel.release(" in src, "slip-vejen mangler — en doed model kiler sessionen"
    # Et eksplicit valg skal laases, ikke overskrives.
    assert "if provider_override or model_override:" in src
    assert "_smp.pin(" in src


def test_laasen_sidder_EFTER_par_valideringen():
    """Laases et ugyldigt par, er låsen værre end ingen lås: den ville gentage
    `ollama/glm-5.2`-fejlen (162 tomme svar, HTTP 200) på hver tur i sessionen."""
    src = pathlib.Path("core/services/visible_runs.py").read_text()
    i_valid = src.index("_model_problem = \"\"")
    i_afvis = src.index("logger.warning(\"visible-run afvist: %s\", _model_problem)")
    i_laas = src.index("session_model_pin as _smp")
    assert i_valid < i_afvis < i_laas, (
        "laasen staar foer par-valideringen — et ugyldigt par kunne laases")
