"""Vagter for daemon-lanens kill switch og regnskab (30/10-2026).

MÅLT (7 dage, ``daemon_output_log``): 13.495 daemon-kald, hvoraf **3.171
(23,5 %) ramte betalt Ollama Cloud**. Synderen var public-safe-lanen, hvis
kandidatpulje KUN indeholdt ollama ``:cloud``-modeller — der fandtes ingen
gratis gren — og som sorterede ``ollama`` bevidst først. ``experiential_memory``
alene stod for 2.063 af kaldene (~295/dag) til at score minder med JSON.
``thought_stream``, der bruger den almindelige balancer, ramte betalt i 4 %.

Disse tests fælder fire tilbagefald:

  1. kill switch TIL  → daemon går på den gratis balancer
  2. kill switch FRA  → daemon går på Ollama-ruten (tilbagevejen virker)
  3. hvert kald skriver en ``costs``-række med ``lane='daemon'``
  4. en streng ``"false"`` betyder FALSE — ``bool("false")`` er ``True``, og
     den fælde gør et flag i runtime.json til det MODSATTE af hvad der står
"""
from __future__ import annotations

import json

import pytest

from core.services import daemon_lane_switch as sw


# ---------------------------------------------------------------------------
# 1+2: kill switchen styrer hvilken vej daemonen går
# ---------------------------------------------------------------------------


def _isolér_daemon(monkeypatch):
    """Slå cache og form-dommer fra, så testen måler RUTEN, ikke cachen."""
    from core.services import daemon_llm

    monkeypatch.setattr(daemon_llm, "_get_cache_ttl", lambda name: 0)
    return daemon_llm


def _fangede_kald(monkeypatch):
    """Erstat begge grene med tællere der returnerer et kendeligt svar."""
    kaldt = {"balanced": 0, "public_safe": 0}

    def fake_balanced(*, prompt, daemon_name=""):
        kaldt["balanced"] += 1
        return {"text": "svar-fra-balancer", "provider": "groq", "model": "llama-3"}

    def fake_public_safe(*, message):
        kaldt["public_safe"] += 1
        return {
            "text": "svar-fra-ollama",
            "provider": "ollama",
            "model": "deepseek-v4.1-flash:cloud",
        }

    monkeypatch.setattr(
        "core.services.cheap_lane_balancer.call_balanced", fake_balanced
    )
    monkeypatch.setattr(
        "core.services.cheap_provider_runtime.execute_public_safe_cheap_lane",
        fake_public_safe,
    )
    return kaldt


def _saet_flag(monkeypatch, tmp_path, *, vaerdi: bool | str | None):
    """Skriv flaget til en MIDLERTIDIG runtime.json — rør aldrig den ægte."""
    cfg = tmp_path / "runtime.json"
    data = {} if vaerdi is None else {sw.RUNTIME_KEY: vaerdi}
    cfg.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr("core.runtime.config.SETTINGS_FILE", cfg)
    monkeypatch.delenv(sw.KILL_SWITCH_ENV, raising=False)
    sw.invalidate_cache()
    return cfg


def test_kill_switch_til_sender_daemon_paa_gratis_balancer(monkeypatch, tmp_path):
    """Flag TIL (default) => balanceren. Det er den nye, billige adfærd."""
    _saet_flag(monkeypatch, tmp_path, vaerdi=True)
    daemon_llm = _isolér_daemon(monkeypatch)
    kaldt = _fangede_kald(monkeypatch)

    out = daemon_llm.daemon_public_safe_llm_call("unik-prompt-alfa", daemon_name="")

    assert out == "svar-fra-balancer"
    assert kaldt["balanced"] == 1, "daemonen gik IKKE på den gratis balancer"
    assert kaldt["public_safe"] == 0, "daemonen ramte stadig den betalte Ollama-rute"


def test_kill_switch_fra_sender_daemon_tilbage_paa_ollama(monkeypatch, tmp_path):
    """Flag FRA => Ollama-ruten. Det er hele pointen: vi kan flippe tilbage."""
    _saet_flag(monkeypatch, tmp_path, vaerdi=False)
    daemon_llm = _isolér_daemon(monkeypatch)
    kaldt = _fangede_kald(monkeypatch)

    out = daemon_llm.daemon_public_safe_llm_call("unik-prompt-beta", daemon_name="")

    assert out == "svar-fra-ollama"
    assert kaldt["public_safe"] == 1, "kill switchen virkede IKKE — gik ikke tilbage"
    assert kaldt["balanced"] == 0


def test_manglende_flag_betyder_gratis(monkeypatch, tmp_path):
    """Ingen nøgle i runtime.json => default er den billige adfærd."""
    _saet_flag(monkeypatch, tmp_path, vaerdi=None)
    daemon_llm = _isolér_daemon(monkeypatch)
    kaldt = _fangede_kald(monkeypatch)

    daemon_llm.daemon_public_safe_llm_call("unik-prompt-gamma", daemon_name="")

    assert kaldt["balanced"] == 1


# ---------------------------------------------------------------------------
# 3: regnskabshullet — hvert kald skal skrive en costs-række
# ---------------------------------------------------------------------------


def test_hvert_daemon_kald_skriver_en_costs_raekke(monkeypatch, tmp_path):
    """MÅLT: nul lane='daemon'-rækker. 13.495 kald var usynlige i hovedbogen."""
    _saet_flag(monkeypatch, tmp_path, vaerdi=True)
    daemon_llm = _isolér_daemon(monkeypatch)
    _fangede_kald(monkeypatch)

    skrevne: list[dict] = []

    def fake_record_cost(**kwargs):
        skrevne.append(kwargs)

    monkeypatch.setattr("core.costing.ledger.record_cost", fake_record_cost)

    daemon_llm.daemon_public_safe_llm_call("unik-prompt-delta", daemon_name="")

    assert len(skrevne) == 1, "daemon-kaldet skrev ingen costs-række — hullet er åbent"
    row = skrevne[0]
    assert row["lane"] == "daemon"
    assert row["provider"] == "groq"
    assert row["model"] == "llama-3"
    assert row["input_tokens"] > 0, "input_tokens=0 kan ikke prissættes"
    assert row["output_tokens"] > 0


def test_intet_svar_skriver_ingen_raekke(monkeypatch, tmp_path):
    """Tomt svar = intet forbrug. En række uden kald ville forurene regnskabet."""
    _saet_flag(monkeypatch, tmp_path, vaerdi=True)
    daemon_llm = _isolér_daemon(monkeypatch)

    monkeypatch.setattr(
        "core.services.cheap_lane_balancer.call_balanced",
        lambda *, prompt, daemon_name="": {"text": "", "provider": "groq", "model": "x"},
    )
    monkeypatch.setattr(
        "core.services.cheap_provider_runtime.execute_public_safe_cheap_lane",
        lambda *, message: {"text": "", "provider": "ollama", "model": "y"},
    )
    # heartbeat-fallbacken må heller ikke give tekst
    monkeypatch.setattr(
        "core.services.heartbeat_runtime._execute_heartbeat_model",
        lambda **kw: {"text": ""},
    )
    monkeypatch.setattr(
        "core.services.heartbeat_runtime._select_heartbeat_target",
        lambda: {"provider": "ollama", "model": "z"},
    )
    monkeypatch.setattr(
        "core.services.heartbeat_runtime.load_heartbeat_policy", lambda: {}
    )

    skrevne: list[dict] = []
    monkeypatch.setattr(
        "core.costing.ledger.record_cost", lambda **kw: skrevne.append(kw)
    )

    out = daemon_llm.daemon_public_safe_llm_call(
        "unik-prompt-epsilon", fallback="tom", daemon_name=""
    )

    assert out == "tom"
    assert skrevne == [], "et kald uden svar skrev en costs-række"


# ---------------------------------------------------------------------------
# 4: bool-fælden — "false" i runtime.json skal betyde FALSE
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,forventet",
    [
        ("false", False),
        ("FALSE", False),
        ("0", False),
        ("off", False),
        ("no", False),
        ("nej", False),
        ("true", True),
        ("1", True),
        ("on", True),
        (False, False),
        (True, True),
        (0, False),
        (1, True),
    ],
)
def test_streng_false_betyder_false(raw, forventet):
    """``bool("false")`` er True. Uden denne gren gør flaget det MODSATTE."""
    assert sw._som_bool(raw, default=True) is forventet


def test_streng_false_i_runtime_json_slaar_kill_switchen_til(monkeypatch, tmp_path):
    """Ende-til-ende: en STRENG "false" i filen skal engagere kill switchen."""
    _saet_flag(monkeypatch, tmp_path, vaerdi="false")

    assert sw.public_safe_free_first() is False, (
        "strengen 'false' blev læst som True — bool-fælden"
    )


def test_env_override_vinder_over_filen(monkeypatch, tmp_path):
    """Env-varen er den hurtigste vej ud, så den skal vinde."""
    _saet_flag(monkeypatch, tmp_path, vaerdi=True)
    monkeypatch.setenv(sw.KILL_SWITCH_ENV, "0")
    sw.invalidate_cache()

    assert sw.public_safe_free_first() is False


# ---------------------------------------------------------------------------
# 5: flip-funktionen skriver og kan læses tilbage
# ---------------------------------------------------------------------------


def test_flip_skriver_noeglen_og_læses_tilbage(monkeypatch, tmp_path):
    """Et flip der ikke kan læses tilbage er ikke et flip."""
    cfg = _saet_flag(monkeypatch, tmp_path, vaerdi=True)
    assert sw.public_safe_free_first() is True

    def fake_write(updates):
        data = json.loads(cfg.read_text(encoding="utf-8"))
        data.update(updates)
        cfg.write_text(json.dumps(data), encoding="utf-8")
        return data

    monkeypatch.setattr(
        "core.runtime.runtime_json_io.write_runtime_merged", fake_write
    )

    result = sw.set_public_safe_free_first(False)

    assert result["written"] is False
    assert result["runtime_key"] == sw.RUNTIME_KEY
    data = json.loads(cfg.read_text(encoding="utf-8"))
    assert data[sw.RUNTIME_KEY] is False, "flaget landede ikke i runtime.json"
    assert sw.public_safe_free_first() is False, "flippet blev ikke læst tilbage"
