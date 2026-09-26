"""Kataloget udskilt fra cheap_provider_runtime_adapters 7/9-2026.

Testene holder to ting fast: at symbolerne stadig kan hentes fra det gamle
modul (kaldere og ældre tests importerer dem derfra), og at nye poster bygger
på MÅLINGER — ikke på hvad udbyderens /v1/models påstår.
"""
from core.services import cheap_provider_catalogue as kat
from core.services import cheap_provider_runtime_adapters as ad


def test_kataloget_kan_stadig_hentes_fra_adapters():
    assert ad.CHEAP_PROVIDER_DEFAULTS is kat.CHEAP_PROVIDER_DEFAULTS
    assert ad._OPENAI_COMPATIBLE_PROVIDERS is kat._OPENAI_COMPATIBLE_PROVIDERS


def test_breaker_symbolerne_overlevede_flytningen():
    # De blev revet med ud i første forsøg og væltede 73 test-moduler ved
    # collection. De hører til i adapters, ikke i kataloget.
    for navn in ("_ARKO_PROVIDER_ID", "_OFA_PROVIDER_ID", "_arko_circuit_open"):
        assert hasattr(ad, navn), navn


def test_llm7_har_kun_de_maalte_modeller():
    e = kat.CHEAP_PROVIDER_DEFAULTS["llm7"]
    assert e["base_url"] == "https://api.llm7.io/v1"
    assert e["auth_kind"] == "bearer"
    assert set(e["static_models"]) == {
        "codestral-latest", "minimax-m2.7", "mistral-Nemo-Instruct-2407",
    }


def test_gpt_oss_er_udeladt_med_vilje():
    """Den svarer 200 med TOM tekst. I en lane ligner det succes — værre end
    en fejl, fordi ingen opdager det."""
    assert "gpt-oss" not in kat.CHEAP_PROVIDER_DEFAULTS["llm7"]["static_models"]


def test_de_betalte_llm7_modeller_er_ikke_med():
    """31 af 36 gav 402 «Insufficient balance», selvom de står på /v1/models."""
    m = kat.CHEAP_PROVIDER_DEFAULTS["llm7"]["static_models"]
    for betalt in ("claude-opus-5", "gpt-6-astra", "deepseek-v4-flash", "glm-5.3-flash"):
        assert betalt not in m


def test_alle_udbydere_har_de_felter_puljen_bruger():
    # `runtime-key` sad ikke i min første liste — jeg gættede på lovlige
    # værdier i stedet for at læse dem. Værdierne kommer nu fra kataloget selv.
    lovlige = {"bearer", "none", "oauth", "runtime-key"}
    for navn, e in kat.CHEAP_PROVIDER_DEFAULTS.items():
        assert isinstance(e.get("priority"), int), navn
        assert e.get("auth_kind") in lovlige, f"{navn}: {e.get('auth_kind')}"


def test_runtime_key_etiketten_er_ikke_mekanismen():
    """`auth_kind: "runtime-key"` står på arko og læses af INGEN kode — arkos
    nøgle går gennem et hårdkodet særtilfælde. Mekanismen er
    RUNTIME_KEY_PROVIDERS. Testen findes så den næste ikke tror etiketten
    virker."""
    from core.services.cheap_provider_runtime_keys import RUNTIME_KEY_PROVIDERS
    etiket = {n for n, e in kat.CHEAP_PROVIDER_DEFAULTS.items()
              if e.get("auth_kind") == "runtime-key"}
    assert etiket == {"arko"}
    assert "arko" not in RUNTIME_KEY_PROVIDERS


def test_dahl_og_tokenharbor_er_koblet_til_noeglerne():
    """Nøglen skal kendes TRE steder (readiness, dispatch, profil-scan), og de
    to sidste læser dette kort — uden en post her kom udbyderen aldrig i puljen
    (xkiro 7/9-2026)."""
    from core.services.cheap_provider_runtime_keys import RUNTIME_KEY_PROVIDERS
    assert RUNTIME_KEY_PROVIDERS["dahl"][0] == "dahl_api_key"
    assert RUNTIME_KEY_PROVIDERS["tokenharbor"][0] == "tokenharbor_api_key"
    for p in ("dahl", "tokenharbor"):
        assert p in kat._OPENAI_COMPATIBLE_PROVIDERS


def test_dahl_har_kun_de_maalte_modeller():
    e = kat.CHEAP_PROVIDER_DEFAULTS["dahl"]
    assert e["base_url"] == "https://inference.dahl.global/v1"
    assert set(e["static_models"]) == {
        "zai-org/GLM-5.3-Flash", "MiniMaxAI/MiniMax-M2.7", "deepseek-ai/DeepSeek-V4-Flash-0731",
    }


def test_tokenharbor_kun_gratis_og_uden_mimo():
    e = kat.CHEAP_PROVIDER_DEFAULTS["tokenharbor"]
    assert e["base_url"] == "https://tokenharbor.ai/v1"
    assert all(m.endswith(":free") for m in e["static_models"])
    # mimo-v2.5:free kaldte ikke værktøjet i målingen.
    assert "mimo-v2.5:free" not in e["static_models"]
    # Langsom (7-54 s): skal ligge bag de hurtige gratis-udbydere.
    assert e["priority"] > kat.CHEAP_PROVIDER_DEFAULTS["dahl"]["priority"]


def test_de_fem_nye_udbydere_er_koblet_til_noeglerne():
    """17/9-2026: nøgle i runtime.json + post i kortet + openai-compat, ellers når
    de aldrig puljen (samme fælde som xkiro)."""
    from core.services.cheap_provider_runtime_keys import RUNTIME_KEY_PROVIDERS
    for p in ("inception", "poolside", "chatanywhere", "internlm", "agnes"):
        assert RUNTIME_KEY_PROVIDERS[p][0] == f"{p}_api_key"
        assert p in kat._OPENAI_COMPATIBLE_PROVIDERS
        assert kat.CHEAP_PROVIDER_DEFAULTS[p]["cost_class"] == "free"
    # orcarouter kom med samme dag, da GitHub-kontoen var koblet.
    assert RUNTIME_KEY_PROVIDERS["orcarouter"][0] == "orcarouter_api_key"
    orca = kat.CHEAP_PROVIDER_DEFAULTS["orcarouter"]["static_models"]
    assert all(m.endswith("-free") for m in orca)
    assert not any(m.startswith("stealth/") or "orcaverify" in m for m in orca)


def test_modeller_der_ikke_kaldte_vaerktoejet_er_udeladt():
    assert "poolside/laguna-s-2.1" not in kat.CHEAP_PROVIDER_DEFAULTS["poolside"]["static_models"]
    assert "intern-latest" not in kat.CHEAP_PROVIDER_DEFAULTS["internlm"]["static_models"]


def test_kilo_har_de_maalte_gratis_modeller_og_ikke_stealth():
    ms = kat.CHEAP_PROVIDER_DEFAULTS["kilo"]["static_models"]
    assert all(m.endswith(":free") or m == "openrouter/free" for m in ms)
    assert "nex-agi/nex-n2.5-mini:free" in ms
    assert not any(m.startswith("stealth/") for m in ms)


def test_meganova_kun_modellen_der_kaldte_vaerktoejet():
    from core.services.cheap_provider_runtime_keys import RUNTIME_KEY_PROVIDERS
    assert RUNTIME_KEY_PROVIDERS["meganova"][0] == "meganova_api_key"
    e = kat.CHEAP_PROVIDER_DEFAULTS["meganova"]
    assert e["static_models"] == ["mistralai/Mistral-Small-3.2-24B-Instruct-2506"]
    assert "meganova" in kat._OPENAI_COMPATIBLE_PROVIDERS


# ── Tre udbydere tilføjet 26/9-2026 ─────────────────────────────────────


def test_de_tre_nye_udbydere_staar_i_kataloget():
    for navn, url in (("nscale", "inference.api.nscale.com"),
                      ("airforce", "api.airforce"),
                      ("chinaapi", "api.chinaapi.ai")):
        post = kat.CHEAP_PROVIDER_DEFAULTS[navn]
        assert url in str(post["base_url"]), navn
        assert post["static_models"], f"{navn} uden målte modeller"


def test_airforce_baerer_sit_AEGTE_loft_paa_ét_kald_i_minuttet():
    """Målt konkret: 65 s ventetid → 200, kald igen straks →
    `rate_limit_exceeded, limit: 1, retry_after 59s`.

    Mod ~440 kald/minut i puljen ville et optimistisk loft betyde at
    balanceren brændte forsøg på den i næsten hvert forsøg. Tallet er ikke
    forsigtighed — det er målingen.
    """
    assert kat.CHEAP_PROVIDER_DEFAULTS["airforce"]["rpm_limit"] == 1


def test_nscale_er_PAID_for_den_har_ingen_gratis_modeller():
    """23 modeller, alle med pris. «Free» er $5 engangskredit, og der er
    ingen /credits-flade at læse resten på — den løber tør uden varsel.
    Den skal derfor gennem den samme port som de øvrige betalte."""
    assert kat.CHEAP_PROVIDER_DEFAULTS["nscale"]["cost_class"] == "paid"


def test_chinaapi_lister_KUN_de_modeller_hvor_forbruget_blev_maalt_til_nul():
    """45 af de 167 modeller står med `model_ratio: 0`, men 38 af dem har
    `quota_type: 1` — fast pris pr. kald, hvor ratio-feltet intet betyder.
    Kun de tre hvor `total_usage` er målt til IKKE at flytte sig hører til
    her. Frontiermodellerne svarer også, men de koster."""
    m = set(kat.CHEAP_PROVIDER_DEFAULTS["chinaapi"]["static_models"])
    assert m == {"agnes-2.5-flash", "agnes-3.0-flash", "stepaudio-3-chat-preview"}
    assert not any(k in " ".join(m) for k in ("opus", "gpt-5", "kimi", "gemini"))


def test_tuzi_er_IKKE_wired_for_kontoen_er_tom():
    """Registreret, deployet, og så svarede det første kald i drift:

        预扣费额度失败, 用户剩余额度: ＄0.075

    «forhåndsreservation mislykkedes, resterende saldo: $0,075». En udbyder
    der fejler hvert kald må ikke stå i puljen — balanceren ville bruge et
    forsøg på den hver gang. Den står som dokumenteret kommentar, som
    SiliconFlow, så den kan wires igen med én blok hvis kontoen fyldes.

    Gateway-softwarens fejltekst røber i øvrigt den ægte saldo. Det er den
    eneste pålidelige vej: `/v1/dashboard/billing/subscription` svarer med
    NewAPI's attrap (`hard_limit_usd: 100000000`), og `total_usage` er et
    rullende vindue der kan FALDE mellem to målinger.
    """
    assert "tuzi" not in kat.CHEAP_PROVIDER_DEFAULTS
    import inspect
    src = inspect.getsource(kat)
    assert "api.tu-zi.com" in src, "viden om udbyderen må ikke forsvinde"


def test_frontiermodellerne_ligger_i_deres_EGEN_post():
    """«lad os nu bruge det ordentligt» — de store modeller skal kunne vælges
    MED VILJE, ikke rammes af en daemon der ledte efter noget billigt.

    Samme mønster som `copilot-premium`: egen post, `cost_class: paid`, høj
    prioritet så den vælges først NÅR betalt er tilladt. Den gratis
    chinaapi-post må ikke indeholde dem.
    """
    prem = kat.CHEAP_PROVIDER_DEFAULTS["chinaapi-premium"]
    gratis = kat.CHEAP_PROVIDER_DEFAULTS["chinaapi"]
    assert prem["cost_class"] == "paid"
    assert prem["priority"] < 10, "premium skal vælges før de billige"
    assert "claude-opus-5" in prem["static_models"]
    assert not any("opus" in m for m in gratis["static_models"])
    # Samme base_url — det er ÉN konto, kun routing-niveauet er forskelligt.
    assert prem["base_url"] == gratis["base_url"]


def test_udeladte_modeller_er_dem_der_ikke_svarede():
    """Kataloget lister kun det der HAR svaret. `deepseek-v4-pro` giver
    `model_requires_topup`, `gpt-5.5` svarede tomt, og på tu-zi gjorde
    `deepseek-v3` og `kimi-k2.6` det samme."""
    prem = kat.CHEAP_PROVIDER_DEFAULTS["chinaapi-premium"]["static_models"]
    assert "deepseek-v4-pro" not in prem, "den afviser aegte: available after topup"
    # gpt-5.5 blev foerst udeladt paa et FORKERT grundlag: proben brugte
    # `max_tokens: 16`, og paa en thinking-model gaar hele budgettet til
    # `reasoning_content`. Med 800 tokens svarer den. En probe der er for lille
    # kan ikke skelne «virker ikke» fra «taenker».
    assert "gpt-5.5" in prem
    # tu-zi er ikke wired (tom konto), men dens målinger står i kommentaren —
    # netop de to der gav tomt svar, så ingen wirer dem igen i god tro.
    import inspect
    src = inspect.getsource(kat)
    assert "deepseek-v3 og kimi-k2.6 gav tomt" in src


def test_fujcloud_er_registreret_som_betalt_mellemhandler():
    """Fjerde NewAPI-gateway. Ingen gratis flade: 20 modeller, 14 med fast
    pris pr. kald og 6 token-prisede — ingen med pris nul."""
    f = kat.CHEAP_PROVIDER_DEFAULTS["fujcloud"]
    assert "ai.fujcloud.com" in str(f["base_url"])
    assert f["cost_class"] == "paid"
    assert "mercury-2.5" not in f["static_models"], "den gav tomt svar"


def test_en_for_lille_probe_kan_ikke_skelne_doed_fra_taenkende():
    """Den fejl jeg selv begik 26/9-2026, skrevet ind så den ikke gentages.

    Jeg udelod `gpt-5.5` fra chinaapi med begrundelsen «svarede tomt». Proben
    brugte `max_tokens: 16`, og på en thinking-model går hele budgettet til
    `reasoning_content` — `content` bliver tom, og modellen ser død ud. Med
    800 tokens svarer den «ok».

    Tre af fujclouds modeller gør præcis det samme (76-514 tegn reasoning før
    svaret), så fælden er ikke teoretisk her.
    """
    import inspect
    src = inspect.getsource(kat)
    assert "kan ikke skelne «virker ikke» fra «taenker»" in src
    assert "reasoning_content" in src
