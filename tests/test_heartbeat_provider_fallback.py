"""Tests for heartbeat provider fallback load-spreading (2026-06-22)."""
import time
from unittest.mock import MagicMock, patch

import pytest

import core.services.cheap_provider_runtime as cpr
from core.services import heartbeat_provider_fallback as hpf


def _cand(provider, model="m"):
    return {
        "provider": provider,
        "model": model,
        "credentials_ready": True,
        "auth_profile": "",
        "base_url": "http://x/v1",
    }


def test_skips_blocked_and_rotates_among_usable():
    cands = [_cand("deepseek"), _cand("mistral"), _cand("opencode")]
    used: list[str] = []

    def _quota(c):
        return {"blocked": c["provider"] == "deepseek"}

    def _exec(*, prompt, target, **kwargs):
        used.append(target["provider"])
        return {"text": "ok"}

    with patch.object(cpr, "_configured_cheap_candidates", return_value=cands), \
         patch.object(cpr, "_candidate_quota_snapshot", side_effect=_quota), \
         patch.object(hpf, "execute_openai_compat_heartbeat_prompt", side_effect=_exec):
        for _ in range(4):
            hpf.try_heartbeat_cheap_fallback("hi")

    # blocked (dry) provider never used; load spread across both usable lanes
    assert "deepseek" not in used
    assert set(used) == {"mistral", "opencode"}


def test_returns_none_when_no_usable():
    cands = [_cand("deepseek")]
    with patch.object(cpr, "_configured_cheap_candidates", return_value=cands), \
         patch.object(cpr, "_candidate_quota_snapshot", return_value={"blocked": True}):
        assert hpf.try_heartbeat_cheap_fallback("hi") is None


def test_falls_through_on_provider_error():
    cands = [_cand("mistral"), _cand("opencode")]

    def _exec(*, prompt, target, **kwargs):
        if target["provider"] == "mistral":
            raise RuntimeError("mistral down")
        return {"text": "ok"}

    with patch.object(cpr, "_configured_cheap_candidates", return_value=cands), \
         patch.object(cpr, "_candidate_quota_snapshot", return_value={"blocked": False}), \
         patch.object(hpf, "execute_openai_compat_heartbeat_prompt", side_effect=_exec):
        # may start on mistral (fails) but must fall through to opencode
        results = [hpf.try_heartbeat_cheap_fallback("hi") for _ in range(2)]
    assert any(r == {"text": "ok"} for r in results)


# ─────────────────────────────────────────────────────────────────────────
# Hullet i hovedbogen (14/9-2026)
#
# `execute_openai_compat_heartbeat_prompt` er et ÆGTE betalt kald — den taler
# HTTPS mod bl.a. api.deepseek.com — og den returnerede `"cost_usd": 0.0` som
# et hardkodet tal. Ingen af dens tre kaldere bogførte: `compact_llm`
# (komprimering, identitets-skitse, truth-gate), `try_heartbeat_cheap_fallback`
# og `heartbeat_runtime`. Pengene blev brugt og stod ingen steder.
#
# Bogføringen ligger derfor i HELPEREN, hvor kaldet faktisk sker, og ikke hos
# kalderne. Det er husets hyppigste fejl vendt om: en mekanisme placeret så
# ingen fremtidig kalder KAN glemme at kalde den.
# ─────────────────────────────────────────────────────────────────────────

import json  # noqa: E402
from unittest.mock import MagicMock  # noqa: E402


def _svar(usage: dict | None = None, indhold: str = "resume"):
    """Et minimalt OpenAI-kompatibelt svar som en falsk urlopen kan give."""
    krop = {"choices": [{"message": {"content": indhold}}]}
    if usage is not None:
        krop["usage"] = usage
    r = MagicMock()
    r.read.return_value = json.dumps(krop).encode()
    r.__enter__ = lambda s: s
    r.__exit__ = lambda s, *a: False
    return r


def _koer(monkeypatch, bogfoert: list, usage=None, provider="deepseek"):
    monkeypatch.setattr("core.services.heartbeat_runtime._load_provider_api_key",
                        lambda **k: "noegle")
    monkeypatch.setattr(hpf.urllib_request, "urlopen", lambda *a, **k: _svar(usage))
    monkeypatch.setattr("core.costing.ledger.record_cost",
                        lambda **k: bogfoert.append(k))
    return hpf.execute_openai_compat_heartbeat_prompt(
        prompt="sammenfat det her", target={"provider": provider, "model": "deepseek-v4-flash"})


def test_kaldet_BOGFOERES(monkeypatch):
    """Selve hullet. Uden den her raekke er pengene brugt og usynlige."""
    bogfoert: list = []
    _koer(monkeypatch, bogfoert, usage={"prompt_tokens": 120_000, "completion_tokens": 400})
    assert len(bogfoert) == 1, "kaldet blev ikke bogfoert"
    r = bogfoert[0]
    assert r["provider"] == "deepseek" and r["model"] == "deepseek-v4-flash"
    assert r["input_tokens"] == 120_000 and r["output_tokens"] == 400


def test_cache_splittet_baeres_MED(monkeypatch):
    """DeepSeek sender `prompt_cache_hit_tokens`. Uden dem prises AL input som
    miss — 50x for dyrt paa praecis den slags gentagne prompts komprimering
    laver. Et regnskab der er forkert opad er stadig forkert."""
    bogfoert: list = []
    _koer(monkeypatch, bogfoert, usage={"prompt_tokens": 100_000,
                                        "prompt_cache_hit_tokens": 90_000,
                                        "prompt_cache_miss_tokens": 10_000,
                                        "completion_tokens": 300})
    r = bogfoert[0]
    assert r["cache_hit_tokens"] == 90_000
    assert r["cache_miss_tokens"] == 10_000


def test_cache_splittet_OPFINDES_ikke(monkeypatch):
    """En udbyder der ikke sender splittet skal give NUL, ikke et gaet.
    `record_cost` behandler saa al input som miss — konservativt og aerligt."""
    bogfoert: list = []
    _koer(monkeypatch, bogfoert, usage={"prompt_tokens": 100_000, "completion_tokens": 300},
          provider="mistral")
    r = bogfoert[0]
    assert r["cache_hit_tokens"] == 0 and r["cache_miss_tokens"] == 0


def test_lanen_siger_HVOR_pengene_gik(monkeypatch):
    """«$62 brugt» kunne ikke besvares fordi ingen lane pegede paa den her vej.
    En bogfoert raekke uden et navn flytter bare hullet."""
    bogfoert: list = []
    _koer(monkeypatch, bogfoert, usage={"prompt_tokens": 10, "completion_tokens": 1})
    assert bogfoert[0]["lane"] == "compat_oneshot"


def test_bogfoeringen_VAELTER_ikke_kaldet(monkeypatch):
    """Et hjerteslag eller en komprimering maa ikke kunne braekke fordi
    hovedbogen er nede. Arbejdet er vigtigere end sporet til det — samme regel
    som dispatch-ophavet."""
    bogfoert: list = []
    monkeypatch.setattr("core.services.heartbeat_runtime._load_provider_api_key",
                        lambda **k: "noegle")
    monkeypatch.setattr(hpf.urllib_request, "urlopen",
                        lambda *a, **k: _svar({"prompt_tokens": 5, "completion_tokens": 1}))
    monkeypatch.setattr("core.costing.ledger.record_cost",
                        lambda **k: (_ for _ in ()).throw(RuntimeError("db nede")))
    ud = hpf.execute_openai_compat_heartbeat_prompt(
        prompt="x", target={"provider": "deepseek", "model": "deepseek-v4-flash"})
    assert ud["text"] == "resume"
    assert bogfoert == []


def test_et_FEJLET_kald_bogfoeres_ikke(monkeypatch):
    """Et kald der ikke naaede igennem har ingen tokens at bogfoere. En raekke
    paa nul ville stoeje i regnskabet uden at tilfoeje noget."""
    import pytest
    bogfoert: list = []
    monkeypatch.setattr("core.services.heartbeat_runtime._load_provider_api_key",
                        lambda **k: "noegle")
    monkeypatch.setattr(hpf.urllib_request, "urlopen",
                        lambda *a, **k: (_ for _ in ()).throw(OSError("nede")))
    monkeypatch.setattr("core.costing.ledger.record_cost", lambda **k: bogfoert.append(k))
    with pytest.raises(RuntimeError):
        hpf.execute_openai_compat_heartbeat_prompt(
            prompt="x", target={"provider": "deepseek", "model": "m"})
    assert bogfoert == []


def test_returen_paastaar_ikke_en_PRIS():
    """Kilde-vagt paa den returnerede ORDBOG, ikke paa filens tekst.

    Et hardkodet `cost_usd: 0.0` i returen var det ene tal der gjorde hele
    vejen gratis paa papiret. Foerste udgave af vagten soegte efter den streng
    i kilden — og gik roed paa MIN EGEN kommentar der naevner den. Samme faelde
    som tidligere i dag: en streng kan staa fire steder i en fil. AST ser paa
    hvad koden GOER.

    Prisen hoerer hjemme i hovedbogen, som beregner den fra tabellen. En
    helper der ogsaa paastaar en pris, ville give to sandheder om samme kald.
    """
    import ast
    import inspect
    import textwrap
    træ = ast.parse(textwrap.dedent(
        inspect.getsource(hpf.execute_openai_compat_heartbeat_prompt)))
    for knude in ast.walk(træ):
        if isinstance(knude, ast.Return) and isinstance(knude.value, ast.Dict):
            nøgler = {k.value for k in knude.value.keys
                      if isinstance(k, ast.Constant)}
            assert "cost_usd" not in nøgler, \
                "returen paastaar en pris — hovedbogen er det ene sted den hoerer hjemme"


def test_bogfoeringen_baerer_KOERSLEN(monkeypatch):
    """Uden run-id'et lyver hovedbogen om EJERSKAB.

    `truth_gate_v2` kaldes fra `visible_runs` — altsaa inde i en af Bjoerns egne
    ture. Bogfoerte vi uden run-id, ville betalt-lane-vagten melde hans eget
    arbejde som et brud, og en vagt der raaber op om hans egne ture bliver
    slaaet fra. Ejerskab skal MAALES, ikke gaettes.

    Samme fejlform som incident 8839/6798: feltet fandtes, kalderen sendte det
    bare ikke.
    """
    bogfoert: list = []
    monkeypatch.setattr("core.services.session_context_resolve.aktivt_run_id",
                        lambda *a, **k: "visible-abc")
    _koer(monkeypatch, bogfoert, usage={"prompt_tokens": 800, "completion_tokens": 60})
    assert bogfoert[0]["run_id"] == "visible-abc"


def test_ukendt_koersel_bogfoeres_TOMT_ikke_gaettet(monkeypatch):
    """Et gaettet run-id ville frikende et aegte brud. Tomt er aerligt: vagten
    behandler det som «hoerer ikke til en tur», hvilket er den sikre retning."""
    bogfoert: list = []
    monkeypatch.setattr("core.services.session_context_resolve.aktivt_run_id",
                        lambda *a, **k: "")
    _koer(monkeypatch, bogfoert, usage={"prompt_tokens": 5, "completion_tokens": 1})
    assert bogfoert[0]["run_id"] == ""


def test_run_opslag_der_KASTER_vaelter_ikke_kaldet(monkeypatch):
    bogfoert: list = []
    monkeypatch.setattr("core.services.session_context_resolve.aktivt_run_id",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("nede")))
    ud = _koer(monkeypatch, bogfoert, usage={"prompt_tokens": 5, "completion_tokens": 1})
    assert ud["text"] == "resume"
    assert bogfoert and bogfoert[0]["run_id"] == ""


# ─────────────────────────────────────────────────────────────────────────
# Kædens samlede budget (målt 3/11-2026)
#
# Hver kandidat havde sin egen 45 s-grænse, men kæden havde INTET samlet loft.
# 34 kandidater (kun 18 unikke) kunne i værste fald bruge 25 minutter inde i en
# cadence-producer, hvis hårde grænse er 75 s. To fejlende kandidater var nok
# til at sprænge den — `inner_voice_daemon` timede ud 9 gange i døgnet på det.
# ─────────────────────────────────────────────────────────────────────────

def test_kaeden_respekterer_sit_samlede_budget(monkeypatch):
    cands = [_cand("mistral", f"m{i}") for i in range(8)]
    tried: list[str] = []

    def _exec(*, prompt, target, **kwargs):
        tried.append(target["model"])
        time.sleep(0.2)
        raise RuntimeError("down")

    monkeypatch.setattr(hpf, "_MIN_ATTEMPT_S", 0.05)
    with patch.object(cpr, "_configured_cheap_candidates", return_value=cands), \
         patch.object(cpr, "_candidate_quota_snapshot", return_value={"blocked": False}), \
         patch.object(hpf, "execute_openai_compat_heartbeat_prompt", side_effect=_exec):
        t0 = time.monotonic()
        assert hpf.try_heartbeat_cheap_fallback("hi", budget_s=0.5) is None
        elapsed = time.monotonic() - t0

    # Otte kandidater à 0,2 s ville tage 1,6 s. Budgettet skal stoppe den.
    assert elapsed < 1.5, elapsed
    assert len(tried) < len(cands), tried


def test_samme_model_forsoeges_kun_en_gang():
    cands = [
        _cand("mistral", "m"),
        _cand("mistral", "m"),
        _cand("opencode", "o"),
        _cand("opencode", "o"),
    ]
    tried: list[tuple[str, str]] = []

    def _exec(*, prompt, target, **kwargs):
        tried.append((target["provider"], target["model"]))
        raise RuntimeError("down")

    with patch.object(cpr, "_configured_cheap_candidates", return_value=cands), \
         patch.object(cpr, "_candidate_quota_snapshot", return_value={"blocked": False}), \
         patch.object(hpf, "execute_openai_compat_heartbeat_prompt", side_effect=_exec):
        assert hpf.try_heartbeat_cheap_fallback("hi") is None

    assert tried.count(("mistral", "m")) == 1, tried
    assert tried.count(("opencode", "o")) == 1, tried


# ── Modellens TANKE maa aldrig blive dens svar ───────────────────────────
# Maalt 4/11-2026: outreach_composer brugte denne kalder, og naar modellen
# brugte alle tokens paa at taenke, faldt svaret tilbage paa
# `reasoning_content`. Resultatet var 3 af 3 outreach-tekster der var
# PROMPT-TRACES ("We need to produce a short message to Bjoern...") gemt
# som brugervendte beskeder. En tanke er ikke et svar.

def _svar_med(monkeypatch, krop: dict):
    monkeypatch.setattr("core.services.heartbeat_runtime._load_provider_api_key",
                        lambda **k: "noegle")
    r = MagicMock()
    r.read.return_value = json.dumps(krop).encode()
    r.__enter__ = lambda s: s
    r.__exit__ = lambda s, *a: False
    monkeypatch.setattr(hpf.urllib_request, "urlopen", lambda *a, **k: r)
    monkeypatch.setattr("core.costing.ledger.record_cost", lambda **k: None)


def test_reasoning_content_er_IKKE_et_svar(monkeypatch):
    """Tomt content + fyldt reasoning_content skal FEJLE, ikke levere tanken."""
    _svar_med(monkeypatch, {"choices": [{"message": {
        "content": "",
        "reasoning_content": "We need to produce a short message to Bjoern. The context: ...",
    }}]})
    with pytest.raises(RuntimeError):
        hpf.execute_openai_compat_heartbeat_prompt(
            prompt="skriv en besked", target={"provider": "deepseek", "model": "deepseek-v4-flash"})


def test_content_med_tanke_ved_siden_af_bruges(monkeypatch):
    """Har modellen BAADE tanke og svar, er det svaret der vinder."""
    _svar_med(monkeypatch, {"choices": [{"message": {
        "content": "Jeg taenkte paa i nat at det hele hang sammen.",
        "reasoning_content": "We need to produce a short message...",
    }}]})
    ud = hpf.execute_openai_compat_heartbeat_prompt(
        prompt="skriv en besked", target={"provider": "deepseek", "model": "deepseek-v4-flash"})
    assert ud["text"] == "Jeg taenkte paa i nat at det hele hang sammen."
    assert "We need to produce" not in ud["text"]
