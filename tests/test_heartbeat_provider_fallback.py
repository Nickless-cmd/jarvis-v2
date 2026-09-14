"""Tests for heartbeat provider fallback load-spreading (2026-06-22)."""
from unittest.mock import patch

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

    def _exec(*, prompt, target):
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

    def _exec(*, prompt, target):
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
