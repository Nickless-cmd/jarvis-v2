"""Kompakterings-resuméet er Jarvis' hukommelse om et forløb — det skrives af
primær-modellen, ikke cheap lane.

Bjørn 19. aug 2026: "cheap lane er forkert værktøj til kompaktering." Målt:
cheap-lane-resuméer tog 2-30s pr. kald og faldt jævnligt til mekanisk fallback,
så et helt samtaleforløb blev reduceret til 200-tegns-stubbe i hans hukommelse.
Modelfilosofien (CLAUDE.md): billige modeller må støtte Jarvis, ikke definere ham.

Rækkefølge: primær (visible provider/model) → cheap-no-groq → heartbeat/groq
→ deterministisk fallback-streng. Kill-switch: `compact_summary_primary`.
"""
from __future__ import annotations

import pytest
from unittest.mock import patch

import core.context.compact_llm as cl


def _koersel(monkeypatch, run_id):
    monkeypatch.setattr("core.services.session_context_resolve.aktivt_run_id",
                        lambda *a, **k: run_id)


class TestPrimaryFoerst:
    """14/9: komprimering naar primaer-lanen gennem et UDTRYKKELIGT opt-in og
    inde i en af Bjoerns koersler. Begge betingelser staar i hver test her, saa
    det er tydeligt hvad der faktisk kraeves — standarden er nu gratis."""

    def test_primaer_svar_bruges_og_cheap_roeres_ikke(self, monkeypatch):
        _koersel(monkeypatch, "visible-abc")
        with patch.object(cl, "_call_primary", return_value="## Resumé\nalt vel"), \
             patch.object(cl, "_call_cheap_no_groq") as cheap:
            out = cl.call_compact_llm("opsummér", max_tokens=2500, tillad_betalt=True)
        assert out == "## Resumé\nalt vel"
        cheap.assert_not_called()

    def test_max_tokens_naar_primaerlanen(self, monkeypatch):
        """Summariseren beder om 2500 — den gamle heartbeat-hardcode var 1536."""
        _koersel(monkeypatch, "visible-abc")
        with patch.object(cl, "_call_primary", return_value="x") as prim:
            cl.call_compact_llm("opsummér", max_tokens=2500, tillad_betalt=True)
        assert prim.call_args.kwargs["max_tokens"] == 2500

    def test_primaer_fejl_falder_til_cheap(self):
        with patch.object(cl, "_call_primary", return_value=None), \
             patch.object(cl, "_call_cheap_no_groq", return_value="cheap-resumé"):
            assert cl.call_compact_llm("opsummér") == "cheap-resumé"

    def test_alt_nede_giver_stadig_fallback_streng(self):
        """call_compact_llm må ALDRIG kaste — compaction skal altid kunne skrive marker."""
        with patch.object(cl, "_call_primary", return_value=None), \
             patch.object(cl, "_call_cheap_no_groq", return_value=None), \
             patch.object(cl, "_call_heartbeat_llm_simple", side_effect=RuntimeError("nede")):
            assert cl.call_compact_llm("opsummér") == cl._FALLBACK_SUMMARY


class TestPrimaryLanens_egne_vaern:
    def _settings(self, provider="deepseek", model="deepseek-v4-flash"):
        class _S:
            visible_model_provider = provider
            visible_model_name = model
        return _S()

    def test_pytest_vaern_blokerer_som_default(self):
        """Uden patch af _in_pytest må _call_primary ALDRIG nå en provider —
        det er værnet mod betalte kald fra testmiljøet (40s deepseek-HTTPS
        fundet via test_context_compact 19. aug 2026)."""
        assert cl._call_primary("p", max_tokens=100) is None

    def test_kill_switch_slukker(self):
        with patch.object(cl, "_in_pytest", return_value=False), \
             patch("core.runtime.db_core.get_runtime_state_bool", return_value=False):
            assert cl._call_primary("p", max_tokens=100) is None

    def test_ukendt_provider_giver_none_ikke_kald(self):
        """En ikke-openai-kompatibel visible-provider må ikke sprænge — bare falde igennem."""
        with patch.object(cl, "_in_pytest", return_value=False), \
             patch("core.runtime.db_core.get_runtime_state_bool", return_value=True), \
             patch("core.runtime.settings.load_settings",
                   return_value=self._settings(provider="anthropic-lignende-ukendt")):
            assert cl._call_primary("p", max_tokens=100) is None

    def test_provider_fejl_sluges_og_giver_none(self):
        with patch.object(cl, "_in_pytest", return_value=False), \
             patch("core.runtime.db_core.get_runtime_state_bool", return_value=True), \
             patch("core.runtime.settings.load_settings", return_value=self._settings()), \
             patch("core.services.heartbeat_provider_fallback.execute_openai_compat_heartbeat_prompt",
                   side_effect=RuntimeError("http-error:429")):
            assert cl._call_primary("p", max_tokens=100) is None

    def test_lav_temperatur_for_resume(self):
        with patch.object(cl, "_in_pytest", return_value=False), \
             patch("core.runtime.db_core.get_runtime_state_bool", return_value=True), \
             patch("core.runtime.settings.load_settings", return_value=self._settings()), \
             patch("core.services.heartbeat_provider_fallback.execute_openai_compat_heartbeat_prompt",
                   return_value={"text": "resumé"}) as ex:
            out = cl._call_primary("p", max_tokens=2500)
        assert out == "resumé"
        assert ex.call_args.kwargs["temperature"] <= 0.5, "resumé skal være trofast, ikke kreativt"
        assert ex.call_args.kwargs["max_tokens"] == 2500

    def test_tom_visible_auth_profile_bliver_default_for_primary(self):
        with patch.object(cl, "_in_pytest", return_value=False), \
             patch("core.runtime.db_core.get_runtime_state_bool", return_value=True), \
             patch("core.runtime.settings.load_settings", return_value=self._settings()), \
             patch("core.services.heartbeat_provider_fallback.execute_openai_compat_heartbeat_prompt",
                   return_value={"text": "resumé"}) as ex:
            assert cl._call_primary("p", max_tokens=2500) == "resumé"

        assert ex.call_args.kwargs["target"]["auth_profile"] == "default"


# ─────────────────────────────────────────────────────────────────────────
# Kalderen troede den var på den billige lane (14/9-2026)
#
# `truth_gate_v2._llm_judge` siger i sin EGEN docstring «Spørg billig lane».
# Den kalder `call_compact_llm`, hvis rute-prioritet sætter den BETALTE
# primær-lane først — og gaten kører på hvert svar der påstår en handling.
# Målt: ~540 kald i timen mod api.deepseek.com, den største enkeltforbruger
# uden for Bjørns egne ture.
#
# Rute-prioriteten er RIGTIG for komprimering: Bjørn satte den dér 19. august
# med en begrundelse — et compact-resumé ER Jarvis' hukommelse om et helt
# forløb. Den beslutning står urørt. Det der manglede var en måde at sige
# «jeg er ikke komprimering» på.
# ─────────────────────────────────────────────────────────────────────────

def test_tillad_betalt_False_springer_primaer_lanen_over(monkeypatch):
    """Kernen: en kalder skal kunne sige fra over for den betalte lane."""
    kaldt: list[str] = []
    monkeypatch.setattr(cl, "_call_primary",
                        lambda p, **k: kaldt.append("primary") or "betalt svar")
    monkeypatch.setattr(cl, "_call_cheap_no_groq",
                        lambda p: kaldt.append("cheap") or "gratis svar")
    ud = cl.call_compact_llm("x", tillad_betalt=False)
    assert "primary" not in kaldt, "den betalte lane blev spurgt alligevel"
    assert ud == "gratis svar"


def test_standarden_er_GRATIS(monkeypatch):
    """Retningen er vendt (14/9). Elleve af femten kaldere er baggrundsarbejde;
    de betalte for de fires beslutning. Nu arver en ny kalder den gratis vej,
    og den der vil bruge penge skal sige det."""
    kaldt: list[str] = []
    _koersel(monkeypatch, "visible-abc")
    monkeypatch.setattr(cl, "_call_primary",
                        lambda p, **k: kaldt.append("primary") or "betalt svar")
    monkeypatch.setattr(cl, "_call_cheap_no_groq", lambda p: "gratis svar")
    assert cl.call_compact_llm("x") == "gratis svar"
    assert kaldt == [], "standarden betalte stadig"


def test_komprimerings_kaldestederne_melder_sig_TIL(monkeypatch):
    """Bjørns beslutning fra 19. august, nu skrevet hvor den gælder.

    Kilde-vagt: forsvinder `tillad_betalt=True` fra et komprimerings-kaldested,
    falder resuméet stille ned på den billige lane — præcis det han afviste,
    fordi et helt samtaleforløb så blev til 200-tegns-stubbe i hans hukommelse.
    """
    import pathlib
    for fil, antal in [("core/context/auto_compact.py", 1),
                       ("core/context/compact_ground_truth.py", 1),
                       ("core/services/visible_runs.py", 2)]:
        n = pathlib.Path(fil).read_text().count("tillad_betalt=True")
        assert n == antal, f"{fil}: {n} opt-ins, ventede {antal}"


def test_INGEN_andre_end_komprimering_melder_sig_til():
    """Vagten mod at opt-in'et spreder sig. De elleve baggrundskaldere skal
    BLIVE paa den gratis vej — ellers er standard-skiftet uden virkning."""
    import pathlib
    tilladt = {"core/context/auto_compact.py", "core/context/compact_ground_truth.py",
               "core/services/visible_runs.py", "core/context/compact_llm.py"}
    fundet = set()
    for p in pathlib.Path(".").rglob("*.py"):
        s = str(p)
        if s.startswith("tests/") or "/__pycache__/" in s or s.startswith(".worktrees"):
            continue
        try:
            if "tillad_betalt=True" in p.read_text():
                fundet.add(s)
        except Exception:
            continue
    assert fundet <= tilladt, f"nye betalte kaldere: {sorted(fundet - tilladt)}"


def test_gratis_vejen_har_stadig_sin_SIDSTE_udvej(monkeypatch):
    """Fejler den billige lane, må dommeren ikke falde tilbage på den BETALTE.
    Ellers ville afkaldet kun gælde når alt virkede."""
    monkeypatch.setattr(cl, "_call_primary",
                        lambda p, **k: pytest.fail("betalt lane brugt som fallback"))
    monkeypatch.setattr(cl, "_call_cheap_no_groq", lambda p: None)
    monkeypatch.setattr(cl, "_call_heartbeat_llm_simple", lambda p, m: "hjerteslag")
    assert cl.call_compact_llm("x", tillad_betalt=False) == "hjerteslag"


def test_truth_gaten_BEDER_om_den_gratis_vej():
    """Kilde-vagt på kalderen. AST: `tillad_betalt=False` skal staa som
    nøgleord i det faktiske kald, ikke i en kommentar."""
    import ast
    import inspect
    import textwrap
    from core.services import truth_gate_v2 as tg
    træ = ast.parse(textwrap.dedent(inspect.getsource(tg._llm_judge)))
    for k in ast.walk(træ):
        if isinstance(k, ast.Call) and getattr(k.func, "id", "") == "call_compact_llm":
            nøgler = {kw.arg: kw.value for kw in k.keywords}
            assert "tillad_betalt" in nøgler, "dommeren beder ikke om den gratis vej"
            assert nøgler["tillad_betalt"].value is False
            break
    else:
        raise AssertionError("call_compact_llm kaldes ikke laengere i _llm_judge")


# ─────────────────────────────────────────────────────────────────────────
# Femten kaldere, én standard (14/9-2026)
#
# `tillad_betalt=False` rettede truth-gaten, og forbruget faldt fra ~540 til
# ~150 kald i timen — men ikke til nul. Målingen viste klynger af fem kald i
# samme sekund med identisk form. Årsagen: `call_compact_llm` har FEMTEN
# kaldere, og standarden er den betalte lane. `daily_journal`,
# `session_milestones`, `cognitive_state_narrativizer`, `identity_sketch`,
# `auto_remember_subscriber`, `semantic_search_tools`, `memory_tools` — næsten
# alt sammen baggrundsarbejde.
#
# At sætte `tillad_betalt=False` femten steder ville være præcis den fejl den
# gamle betalt-lane-vagt lavede: at vedligeholde en liste. Lister forfalder, og
# kalder nummer seksten ville arve den forkerte standard.
#
# Bjørns regel siger det selv: DeepSeek kun i visible lane AF HAM. Er der ingen
# synlig kørsel, er der ingen ham — så er der heller ikke noget at betale for.
# Ejerskab, ikke en liste over navne. Samme invariant som betalt-lane-vagten.
#
# Komprimering sker INDE i hans kørsel og beholder derfor primær-lanen:
# beslutningen fra 19. august står urørt, nu af en grund koden selv kan tjekke.
# ─────────────────────────────────────────────────────────────────────────


def test_UDEN_synlig_koersel_bruges_den_betalte_lane_IKKE(monkeypatch):
    """Baggrundsarbejde: dagbog, milepaele, skitse. Han sidder der ikke."""
    kaldt: list[str] = []
    _koersel(monkeypatch, "")
    monkeypatch.setattr(cl, "_call_primary", lambda p, **k: kaldt.append("primary") or "betalt")
    monkeypatch.setattr(cl, "_call_cheap_no_groq", lambda p: "gratis")
    assert cl.call_compact_llm("x", tillad_betalt=True) == "gratis"
    assert kaldt == [], "baggrundsarbejde ramte den betalte lane"


def test_INDE_i_hans_koersel_beholdes_primaer_lanen(monkeypatch):
    """Komprimering sker under hans tur. Beslutningen fra 19. august staar."""
    _koersel(monkeypatch, "visible-abc")
    monkeypatch.setattr(cl, "_call_primary", lambda p, **k: "betalt")
    monkeypatch.setattr(cl, "_call_cheap_no_groq", lambda p: "gratis")
    assert cl.call_compact_llm("x", tillad_betalt=True) == "betalt"


def test_en_AUTONOM_koersel_betaler_ikke(monkeypatch):
    """Et run-id alene er ikke nok — det skal vaere HANS."""
    kaldt: list[str] = []
    _koersel(monkeypatch, "autonomous-xyz")
    monkeypatch.setattr(cl, "_call_primary", lambda p, **k: kaldt.append("p") or "betalt")
    monkeypatch.setattr(cl, "_call_cheap_no_groq", lambda p: "gratis")
    assert cl.call_compact_llm("x", tillad_betalt=True) == "gratis"
    assert kaldt == []


def test_et_UKENDT_run_opslag_betaler_ikke(monkeypatch):
    """Kan vi ikke afgoere hvem kaldet tilhoerer, koster det ikke penge.
    Den sikre retning er den gratis — modsat hovedbogens ukendt-regler, fordi
    det her er en UDGIFT og ikke en maaling af en udgift."""
    monkeypatch.setattr("core.services.session_context_resolve.aktivt_run_id",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("nede")))
    monkeypatch.setattr(cl, "_call_primary", lambda p, **k: pytest.fail("betalte alligevel"))
    monkeypatch.setattr(cl, "_call_cheap_no_groq", lambda p: "gratis")
    assert cl.call_compact_llm("x", tillad_betalt=True) == "gratis"


def test_tillad_betalt_False_vinder_OGSAA_inde_i_hans_koersel(monkeypatch):
    """Truth-gaten koerer inde i hans tur, men er en intern vagt og ikke hans
    samtale. Et udtrykkeligt afkald skal stadig gaelde."""
    _koersel(monkeypatch, "visible-abc")
    monkeypatch.setattr(cl, "_call_primary", lambda p, **k: pytest.fail("afkaldet blev ignoreret"))
    monkeypatch.setattr(cl, "_call_cheap_no_groq", lambda p: "gratis")
    assert cl.call_compact_llm("x", tillad_betalt=False) == "gratis"


def test_en_komprimering_der_MISTER_primaer_lanen_raaber_op(monkeypatch, caplog):
    """Sidste værn om beslutningen fra 19. august.

    De fire komprimerings-kaldesteder nås alle fra en synlig kørsel — men det
    er en ANTAGELSE om kaldekæder, ikke en måling. Holder den ikke, falder
    resuméet til den billige lane, og resultatet er nøjagtig det Bjørn afviste:
    et helt samtaleforløb reduceret til en 200-tegns-stub i hans hukommelse.

    Det ville være TAVST. En stub ligner et resumé. Så den siger fra i stedet.
    """
    import logging
    _koersel(monkeypatch, "")            # ingen synlig koersel
    monkeypatch.setattr(cl, "_call_cheap_no_groq", lambda p: "gratis")
    with caplog.at_level(logging.WARNING, logger=cl.logger.name):
        cl.call_compact_llm("x", tillad_betalt=True)
    assert any("komprimering" in r.message.lower() for r in caplog.records), \
        "faldet til den billige lane var tavst"


def test_almindeligt_baggrundsarbejde_raaber_IKKE_op(monkeypatch, caplog):
    """De elleve baggrundskaldere SKAL være på den gratis vej. Advarede vi om
    dem, ville loggen fyldes med den normale tilstand, og advarslen der betyder
    noget ville drukne."""
    import logging
    _koersel(monkeypatch, "")
    monkeypatch.setattr(cl, "_call_cheap_no_groq", lambda p: "gratis")
    with caplog.at_level(logging.WARNING, logger=cl.logger.name):
        cl.call_compact_llm("x")
    assert not [r for r in caplog.records if "komprimering" in r.message.lower()]
