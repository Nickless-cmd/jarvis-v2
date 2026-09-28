"""Findes den valgte model hos den valgte udbyder?

`ollama/glm-5.2` kørte 162 gange mellem 20. juli og 9. september 2026 og
svarede TOMT hver eneste gang — HTTP 200, nul tokens, ingen fejl, ingen
faktura. Runnet blev markeret `completed`, så fejlen lignede en succes i enhver
optælling.

«Dit valg vinder» er ikke det samme som «dit valg tjekkes aldrig».
"""
from __future__ import annotations

import pytest

from core.services import model_pair_resolver as R
from core.services.model_pair_resolver import UnknownModelPair, kandidater, resolve

NAVNE = ["glm-5.2:cloud", "glm-5.1:cloud", "deepseek-v4-flash:cloud",
         "llama3.1:8b", "nomic-embed-text:latest"]


@pytest.fixture(autouse=True)
def _ren_cache():
    R._nulstil_cache_for_tests()
    yield
    R._nulstil_cache_for_tests()


@pytest.fixture
def liste(monkeypatch):
    def _saet(navne):
        monkeypatch.setattr(R, "_ollama_modeller", lambda *a, **k: navne)
    return _saet


# ── kandidat-udvælgelsen er ren ──────────────────────────────────────────

def test_praecist_match_vinder_alene():
    assert kandidater(NAVNE, "llama3.1:8b") == ["llama3.1:8b"]


def test_bart_navn_finder_sin_cloud_model():
    """Ollama rapporterer selv det bare navn som remote_model — det ER et alias."""
    assert kandidater(NAVNE, "glm-5.2") == ["glm-5.2:cloud"]


def test_ukendt_navn_giver_ingen_kandidater():
    assert kandidater(NAVNE, "findes-ikke") == []


def test_tomt_navn_giver_ingen_kandidater():
    assert kandidater(NAVNE, "") == [] and kandidater(NAVNE, "  ") == []


def test_flere_varianter_giver_flere_kandidater():
    n = ["qwen3.5:9b", "qwen3.5:397b-cloud"]
    assert kandidater(n, "qwen3.5") == ["qwen3.5:397b-cloud", "qwen3.5:9b"]


# ── den fejl der kostede syv uger ────────────────────────────────────────

def test_glm_5_2_oversaettes_i_stedet_for_at_svare_tomt(liste):
    liste(NAVNE)
    assert resolve("ollama", "glm-5.2") == ("ollama", "glm-5.2:cloud")


def test_oversaettelsen_LOGGES(liste, caplog):
    """Et stille fix er stadig et stille system. Man skal kunne se at navnet
    blev lavet om."""
    import logging
    liste(NAVNE)
    with caplog.at_level(logging.INFO):
        resolve("ollama", "glm-5.2")
    assert "oversatte" in caplog.text and "glm-5.2:cloud" in caplog.text


def test_et_gyldigt_par_roeres_ikke(liste):
    liste(NAVNE)
    assert resolve("ollama", "glm-5.2:cloud") == ("ollama", "glm-5.2:cloud")


# ── fejl højt når det ikke er entydigt ───────────────────────────────────

def test_en_model_der_IKKE_findes_fejler_hoejt(liste):
    """Et tomt svar er værre end en fejlbesked, fordi ingen kan se hvad der
    gik galt."""
    liste(NAVNE)
    with pytest.raises(UnknownModelPair, match="findes ikke"):
        resolve("ollama", "gpt-9")


def test_fejlen_siger_hvad_udbyderen_SAA_har(liste):
    liste(NAVNE)
    with pytest.raises(UnknownModelPair, match="glm-5.2:cloud"):
        resolve("ollama", "gpt-9")


def test_et_TVETYDIGT_navn_fejler_hoejt(liste):
    liste(["qwen3.5:9b", "qwen3.5:397b-cloud"])
    with pytest.raises(UnknownModelPair, match="tvetydigt"):
        resolve("ollama", "qwen3.5")


# ── en utilgængelig udbyder er ikke en forkert model ─────────────────────

def test_kan_listen_ikke_hentes_gaar_parret_IGENNEM(liste):
    """At blokere her ville gøre en kortvarig netværksfejl til et afvist svar."""
    liste(None)
    assert resolve("ollama", "hvad-som-helst") == ("ollama", "hvad-som-helst")


def test_en_TOM_liste_blokerer_heller_ikke(liste, caplog):
    import logging
    liste([])
    with caplog.at_level(logging.WARNING):
        assert resolve("ollama", "glm-5.2") == ("ollama", "glm-5.2")
    assert "NUL modeller" in caplog.text


# ── kun ollama slås op ───────────────────────────────────────────────────

@pytest.mark.parametrize("p", ["deepseek", "alibaba", "anthropic", ""])
def test_andre_udbydere_gaar_uroert_igennem(p, liste):
    liste(NAVNE)
    assert resolve(p, "glm-5.2") == (p, "glm-5.2")


def test_tomt_modelnavn_gaar_igennem(liste):
    liste(NAVNE)
    assert resolve("ollama", "") == ("ollama", "")


# ── den kastefri variant ─────────────────────────────────────────────────

def test_resolve_safe_giver_problemet_tilbage_frem_for_at_kaste(liste):
    liste(NAVNE)
    p, m, problem = R.resolve_safe("ollama", "gpt-9")
    assert (p, m) == ("ollama", "gpt-9") and "findes ikke" in problem


def test_resolve_safe_oversaetter_ogsaa(liste):
    liste(NAVNE)
    assert R.resolve_safe("ollama", "glm-5.2") == ("ollama", "glm-5.2:cloud", "")


def test_resolve_safe_melder_intet_problem_naar_alt_er_godt(liste):
    liste(NAVNE)
    assert R.resolve_safe("ollama", "llama3.1:8b")[2] == ""


# ── cachen ───────────────────────────────────────────────────────────────

def test_listen_hentes_ikke_ved_HVERT_kald(monkeypatch):
    """Det her sidder på den varme sti."""
    kald = []
    import httpx

    class _Svar:
        @staticmethod
        def json(): return {"models": [{"name": n} for n in NAVNE]}

    def _get(url, **kw):
        kald.append(url)
        return _Svar()

    monkeypatch.setattr(httpx, "get", _get)
    monkeypatch.setattr("core.services.semantic_memory._ollama_base_url",
                        lambda: "http://x:11434")
    for _ in range(5):
        resolve("ollama", "glm-5.2")
    assert len(kald) == 1


# ── Hvilken ollama spoerges? (28/9-2026) ─────────────────────────────────
#
# Bjoern skrev til Jarvis med ollama/deepseek-v4.1-flash:cloud og fik INTET
# svar. Journalen kl. 18:43:
#
#     visible-run afvist: ollama/deepseek-v4.1-flash:cloud findes ikke.
#     ollama har: nomic-embed-text:latest
#
# Tjekket spurgte `semantic_memory._ollama_base_url()`, som med vilje peger paa
# den DEDIKEREDE EMBED-vaert — den har kun nomic-embed-text og skal ikke have
# andet. Saa var svaret paa «findes den her chat-model?» altid nej, for ALLE
# ollama-modeller. Fejlen laa der i forvejen og blev synlig da embed-instansen
# blev opgraderet og begyndte at svare rent i stedet for at fejle (og en fejl
# lod parret gaa).

def test_spoerger_CHAT_ollamaen_og_ikke_embed_vaerten(monkeypatch):
    """Adressen skal komme fra provider-registrets ollama-post — samme kilde
    som `visible_model` bruger naar den faktisk kalder modellen."""
    from core.services import model_pair_resolver as r
    monkeypatch.setattr(
        "core.runtime.provider_router._provider_base_url",
        lambda **kw: "http://chat-ollama:11434",
    )
    monkeypatch.setattr(
        "core.runtime.provider_router.load_provider_router_registry", lambda: {})
    assert r._chat_ollama_base_url() == "http://chat-ollama:11434"


def test_falder_tilbage_til_11434_og_ikke_til_embed(monkeypatch):
    """Uden en post i registret er 11434 det rigtige gaet. 11435 ER embed —
    det ville vaere den samme fejl igen, bare hardkodet."""
    from core.services import model_pair_resolver as r
    monkeypatch.setattr(
        "core.runtime.provider_router._provider_base_url",
        lambda **kw: None)
    monkeypatch.setattr(
        "core.runtime.provider_router.load_provider_router_registry", lambda: {})
    adresse = r._chat_ollama_base_url()
    assert adresse == "http://127.0.0.1:11434"
    assert "11435" not in adresse


def test_embed_vaertens_liste_afviser_ikke_en_chat_model(monkeypatch):
    """Selve symptomet: embed-vaerten har KUN nomic-embed-text. Spurgte vi den,
    blev hver eneste ollama-chat-model afvist."""
    from core.services import model_pair_resolver as r
    r._nulstil_cache_for_tests()
    monkeypatch.setattr(r, "_chat_ollama_base_url",
                        lambda: "http://127.0.0.1:11434")
    monkeypatch.setattr(r, "_ollama_modeller",
                        lambda base_url=None: ["deepseek-v4.1-flash:cloud", "glm-5.2:cloud"])
    for model in ("deepseek-v4.1-flash:cloud", "glm-5.2:cloud"):
        _, _, problem = r.resolve_safe("ollama", model)
        assert problem == "", f"{model}: {problem}"


def test_en_model_der_VIRKELIG_mangler_afvises_stadig(monkeypatch):
    """Rettelsen maa ikke sloeve tjekket. Den fandtes fordi `ollama/glm-5.2`
    koerte 162 gange og svarede tomt hver gang."""
    from core.services import model_pair_resolver as r
    r._nulstil_cache_for_tests()
    monkeypatch.setattr(r, "_ollama_modeller",
                        lambda base_url=None: ["glm-5.3:cloud"])
    _, _, problem = r.resolve_safe("ollama", "findes-slet-ikke")
    assert "findes ikke" in problem


def test_selve_HENTNINGEN_gaar_til_chat_ollamaen(monkeypatch):
    """Den afgoerende test: hvilken URL bliver der FAKTISK kaldt?

    De andre tests her stubber enten listen eller adressen, og saa kan de ikke
    se om `_ollama_modeller` vaelger den rigtige vaert. En mutation der satte
    embed-vaerten tilbage slap forbi dem alle. Her optages den url httpx faar.
    """
    import httpx
    from core.services import model_pair_resolver as r
    r._nulstil_cache_for_tests()

    kaldt: list[str] = []

    class Svar:
        @staticmethod
        def json():
            return {"models": [{"name": "glm-5.2:cloud"}]}

    def falsk_get(url, **kw):
        kaldt.append(url)
        return Svar()

    monkeypatch.setattr(httpx, "get", falsk_get)
    monkeypatch.setattr(
        "core.runtime.provider_router._provider_base_url",
        lambda **kw: "http://chat-ollama:11434")
    monkeypatch.setattr(
        "core.runtime.provider_router.load_provider_router_registry", lambda: {})

    assert r._ollama_modeller() == ["glm-5.2:cloud"]
    assert kaldt == ["http://chat-ollama:11434/api/tags"]
    # Embed-vaerten maa ALDRIG vaere den der spoerges om chat-modeller.
    assert all("11435" not in u for u in kaldt), kaldt
