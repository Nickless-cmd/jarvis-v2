"""Anmodningen skal kunne BYGGES igen, ikke bare genkendes.

Fase 2: «prepared requests can be reconstructed with route, prompt, ordered
tool schemas, derived-history watermark, profile hash, and compaction
generation». Og §514: «a hash without retrievable content is insufficient.»
"""
from __future__ import annotations

import pytest

from core.services.prepared_request import (
    Component, IncompleteRequest, PreparedRequest, digest, forget_content,
)

VAERKTOEJER = [{"name": "grep", "schema": {}}, {"name": "read", "schema": {}}]


def _p(**kw):
    kw.setdefault("request_series_id", "rs-1")
    kw.setdefault("provider_id", "anthropic")
    kw.setdefault("model", "claude-opus-5")
    kw.setdefault("params", {"temperature": 0.7})
    kw.setdefault("prompt", Component(value="du er Jarvis"))
    kw.setdefault("tool_schemas", Component(value=VAERKTOEJER))
    kw.setdefault("derived_history_watermark", 42)
    kw.setdefault("compaction_generation", 3)
    kw.setdefault("profile_hash", "sha256:profil")
    return PreparedRequest(**kw)


# ── genskabelse ──────────────────────────────────────────────────────────

def test_anmodningen_kan_bygges_igen(): 
    k = _p().reconstruct()
    assert k["model"] == "claude-opus-5" and k["prompt"] == "du er Jarvis"
    assert k["tools"] == VAERKTOEJER and k["params"]["temperature"] == 0.7


def test_indhold_bag_en_REFERENCE_hentes():
    lager = {"prompt-7": "du er Jarvis"}
    p = _p(prompt=Component(ref="prompt-7"))
    assert p.reconstruct(lager.get)["prompt"] == "du er Jarvis"


def test_en_reference_uden_opslagsfunktion_er_en_FEJL():
    with pytest.raises(IncompleteRequest, match="opslagsfunktion"):
        _p(prompt=Component(ref="prompt-7")).reconstruct()


def test_en_reference_der_ikke_kan_hentes_er_en_FEJL():
    with pytest.raises(IncompleteRequest, match="kunne ikke hentes"):
        _p(prompt=Component(ref="findes-ikke")).reconstruct(lambda r: None)


# ── kravet der ikke kan snydes ───────────────────────────────────────────

def test_et_HASH_uden_indhold_er_ikke_nok():
    """Et hash beviser at to ting ER ens. Det kan ikke bygge nogen af dem.
    Og det er netop når indholdet er væk, man har brug for det."""
    with pytest.raises(IncompleteRequest, match="kan ikke bygge indholdet"):
        forget_content(_p()).reconstruct()


def test_fejlen_siger_HVAD_der_mangler():
    p = _p()
    d = digest(p.prompt.value)
    with pytest.raises(IncompleteRequest, match=d[:20]):
        forget_content(p).reconstruct()


def test_det_er_en_FEJL_og_ikke_en_advarsel():
    """Alternativet er en anmodning der ser komplet ud og mangler noget."""
    glemt = forget_content(_p())
    with pytest.raises(IncompleteRequest):
        glemt.body_digest()


# ── rækkefølgen af værktøjer er en del af anmodningen ────────────────────

def test_en_anden_RAEKKEFOELGE_er_en_anden_anmodning():
    """Modellerne er følsomme over for det, og cachen brydes."""
    a = _p().body_digest()
    b = _p(tool_schemas=Component(value=list(reversed(VAERKTOEJER)))).body_digest()
    assert a != b


def test_samme_anmodning_giver_samme_digest():
    assert _p().body_digest() == _p().body_digest()


def test_digesten_er_uafhaengig_af_noeglernes_orden():
    a = digest({"a": 1, "b": 2})
    b = digest({"b": 2, "a": 1})
    assert a == b


@pytest.mark.parametrize("felt,vaerdi", [
    ("model", "en-anden-model"),
    ("provider_id", "openai"),
    ("params", {"temperature": 0.1}),
    ("derived_history_watermark", 43),
    ("compaction_generation", 4),
    ("profile_hash", "sha256:andet"),
])
def test_hver_komponent_paavirker_digesten(felt, vaerdi):
    assert _p().body_digest() != _p(**{felt: vaerdi}).body_digest()


def test_prompten_paavirker_digesten():
    assert _p().body_digest() != _p(prompt=Component(value="noget andet")).body_digest()


# ── er det stadig samme anmodningsserie? ─────────────────────────────────

def test_samme_serie_naar_intet_er_flyttet():
    assert _p().same_series_as(_p())


def test_en_RUTE_aendring_bryder_ikke_serien():
    """Spec en tillader route_override og kræver kun at skiftet er logget."""
    assert _p().same_series_as(_p(provider_id="openai", model="gpt-5"))


@pytest.mark.parametrize("felt,vaerdi", [
    ("compaction_generation", 4),
    ("derived_history_watermark", 43),
    ("profile_hash", "sha256:andet"),
    ("request_series_id", "rs-2"),
])
def test_disse_aendringer_BRYDER_serien(felt, vaerdi):
    """Dér ser modellen noget andet, og så er det ikke et genforsøg længere."""
    assert not _p().same_series_as(_p(**{felt: vaerdi}))


# ── historik-vandmærket ──────────────────────────────────────────────────

def test_vandmaerket_gemmes_saa_man_kan_se_om_et_genforsoeg_ser_MERE():
    p = _p(derived_history_watermark=42)
    assert p.derived_history_watermark == 42
    assert not p.same_series_as(_p(derived_history_watermark=99))


# ── uforanderlighed ──────────────────────────────────────────────────────

def test_anmodningen_kan_ikke_aendres_efter_den_er_lavet():
    p = _p()
    with pytest.raises(Exception):
        p.model = "noget andet"


def test_genskabelsen_aendrer_ikke_anmodningen():
    p = _p()
    foer = p.body_digest()
    p.reconstruct()
    assert p.body_digest() == foer
