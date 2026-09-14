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


class TestPrimaryFoerst:
    def test_primaer_svar_bruges_og_cheap_roeres_ikke(self):
        with patch.object(cl, "_call_primary", return_value="## Resumé\nalt vel"), \
             patch.object(cl, "_call_cheap_no_groq") as cheap:
            out = cl.call_compact_llm("opsummér", max_tokens=2500)
        assert out == "## Resumé\nalt vel"
        cheap.assert_not_called()

    def test_max_tokens_naar_primaerlanen(self):
        """Summariseren beder om 2500 — den gamle heartbeat-hardcode var 1536."""
        with patch.object(cl, "_call_primary", return_value="x") as prim:
            cl.call_compact_llm("opsummér", max_tokens=2500)
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


def test_standarden_er_UAENDRET(monkeypatch):
    """Komprimering skal stadig ramme primær-lanen. Et default-skifte ville
    stiltiende vende Bjørns beslutning fra 19. august."""
    kaldt: list[str] = []
    monkeypatch.setattr(cl, "_call_primary",
                        lambda p, **k: kaldt.append("primary") or "betalt svar")
    monkeypatch.setattr(cl, "_call_cheap_no_groq", lambda p: "gratis svar")
    assert cl.call_compact_llm("x") == "betalt svar"
    assert kaldt == ["primary"]


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
