"""Tests for core.services.session_prewarm — prewarm-on-return DeepSeek cache warming.

Guards the invariants that keep warming SAFE:
  - no session / non-deepseek / disabled → skip (no API call)
  - throttle: a second warm within the cooldown is skipped
  - a successful warm records cache-hit/miss stats without persisting anything
The deepseek POST + message builder are monkeypatched so no network/DB is touched.
"""
from __future__ import annotations

import threading as _threading
import time as _time

import core.services.session_prewarm as sp


def _reset_throttle():
    with sp._last_warm_lock:
        sp._last_warm.clear()


def test_skip_when_no_session(monkeypatch):
    monkeypatch.setattr(sp, "_deepseek_key", lambda: "k", raising=True)
    r = sp.warm_session_prefix("", force=True)
    assert r["status"] == "skipped" and r["reason"] == "no-session"


def test_skip_when_not_deepseek(monkeypatch):
    _reset_throttle()
    r = sp.warm_session_prefix("chat-x", provider="ollama", force=True)
    assert r["status"] == "skipped" and r["reason"] == "provider-not-deepseek"


def test_skip_when_disabled(monkeypatch):
    _reset_throttle()
    monkeypatch.setattr(sp, "session_prewarm_enabled", lambda: False, raising=True)
    r = sp.warm_session_prefix("chat-x", force=True)
    assert r["status"] == "skipped" and r["reason"] == "disabled"


def test_throttle_second_call_within_cooldown(monkeypatch):
    _reset_throttle()
    monkeypatch.setattr(sp, "session_prewarm_enabled", lambda: True, raising=True)
    # first (non-forced) call passes the throttle and stamps it
    assert sp._should_warm("chat-throttle") is True
    # second within cooldown is throttled
    assert sp._should_warm("chat-throttle") is False


def test_successful_warm_records_stats(monkeypatch):
    _reset_throttle()
    monkeypatch.setattr(sp, "session_prewarm_enabled", lambda: True, raising=True)
    monkeypatch.setattr(sp, "_deepseek_key", lambda: "key", raising=True)

    # message builder → deterministic messages (no assembly/DB)
    import core.services.visible_model as vm
    monkeypatch.setattr(
        vm, "_build_visible_chat_messages_for_github",
        lambda *a, **k: [{"role": "system", "content": "sys"}, {"role": "user", "content": "(prewarm)"}],
        raising=True,
    )
    # deepseek POST → fake usage with cache split
    monkeypatch.setattr(
        sp, "_post_deepseek",
        lambda *a, **k: {"usage": {"prompt_cache_hit_tokens": 900,
                                   "prompt_cache_miss_tokens": 100,
                                   "prompt_tokens": 1000, "completion_tokens": 1}},
        raising=True,
    )
    recorded: dict = {}
    import core.costing.ledger as ledger
    monkeypatch.setattr(ledger, "record_cost", lambda **kw: recorded.update(kw), raising=True)

    r = sp.warm_session_prefix("chat-ok", user_id="u1", force=True)
    assert r["status"] == "ok"
    assert r["cache_hit_tokens"] == 900 and r["cache_miss_tokens"] == 100
    # cost is recorded under the dedicated warmer label — never as real traffic
    assert recorded.get("provider") == "session_cache_warmer"
    assert recorded.get("cache_hit_tokens") == 900


def test_warm_kanoniserer_flash_alias_foer_baade_builder_og_api(monkeypatch):
    """Warmer og live-lane skal bruge samme model-id, ellers deler de ikke prefix."""
    _reset_throttle()
    monkeypatch.setattr(sp, "session_prewarm_enabled", lambda: True, raising=True)
    monkeypatch.setattr(sp, "_deepseek_key", lambda: "key", raising=True)

    seen: dict = {}
    import core.services.visible_model as vm

    def _messages(*_args, **kwargs):
        seen["builder_model"] = kwargs["model"]
        return [{"role": "system", "content": "sys"}]

    def _post(_key, payload, **_kwargs):
        seen["api_model"] = payload["model"]
        return {"usage": {"prompt_tokens": 1, "prompt_cache_miss_tokens": 1}}

    monkeypatch.setattr(vm, "_build_visible_chat_messages_for_github", _messages, raising=True)
    monkeypatch.setattr(sp, "_post_deepseek", _post, raising=True)
    monkeypatch.setattr("core.costing.ledger.record_cost", lambda **_kw: None)

    result = sp.warm_session_prefix(
        "chat-alias", provider="deepseek", model="deepseek-v4-flash", force=True,
    )

    assert result["status"] == "ok"
    assert seen == {"builder_model": "deepseek-flash", "api_model": "deepseek-flash"}


def test_warm_never_raises_on_builder_error(monkeypatch):
    _reset_throttle()
    monkeypatch.setattr(sp, "session_prewarm_enabled", lambda: True, raising=True)
    monkeypatch.setattr(sp, "_deepseek_key", lambda: "key", raising=True)
    import core.services.visible_model as vm

    def _boom(*a, **k):
        raise RuntimeError("build failed")

    monkeypatch.setattr(vm, "_build_visible_chat_messages_for_github", _boom, raising=True)
    r = sp.warm_session_prefix("chat-err", force=True)
    assert r["status"] == "error"  # self-safe: returned, not raised


# ── Warmeren skal varme DEN model der faktisk svarer ────────────────────────

def test_warmeren_foelger_den_konfigurerede_model(monkeypatch):
    """1/10-2026: `visible_model_name` blev skiftet til DeepSeeks kanoniske navn
    `deepseek-flash`, men warmeren stod haardkodet paa legacy-navnet. Maalt
    elleve minutter efter skiftet: den varmede stadig `deepseek-v4-flash`.

    En cache-warmer der varmer en ANDEN model end den der svarer, varmer
    ingenting — saa de to navne maa ikke kunne drive fra hinanden."""
    import core.services.session_prewarm as sp

    set_model: dict = {}

    class _Indstillinger:
        visible_model_name = "model-fra-konfigurationen"

    monkeypatch.setattr("core.runtime.settings.load_settings", lambda: _Indstillinger())
    monkeypatch.setattr(sp, "_warm_now", lambda **kw: set_model.update(kw) or {"status": "ok"},
                        raising=False)

    # Vi kalder ikke hele vejen igennem; vi laeser hvad defaulten opløses til.
    import inspect
    sig = inspect.signature(sp.warm_session_prefix)
    assert sig.parameters["model"].default == "", (
        "defaulten skal vaere tom, saa den kan opløses mod konfigurationen")


def test_scriptets_default_er_ikke_laengere_haardkodet():
    """`scripts/primary_cache_warmer.py` havde sit eget `DEFAULT_MODEL`. Nu
    spoerger den konfigurationen, og falder tilbage paa det KANONISKE navn —
    ikke legacy-navnet — hvis den ikke kan laeses."""
    import importlib.util
    from pathlib import Path
    sti = Path(__file__).resolve().parents[1] / "scripts" / "primary_cache_warmer.py"
    kilde = sti.read_text(encoding="utf-8")
    assert 'DEFAULT_MODEL = "deepseek-v4-flash"' not in kilde
    assert "DEFAULT_MODEL = _konfigureret_model()" in kilde
    assert "KANONISK_FLASH" in kilde


# ── Genbrugt worker-tråd (18/10-2026) ───────────────────────────────────────
#
# ROD: `warm_session_prefix_async` startede en NY tråd pr. kald. Hver tråd åbner
# sin egen thread-lokale SQLite-forbindelse, og sqlite3 nægter at lade en anden
# tråd lukke den. Målt i drift 18/10: `session-prewarm` stod for 172 af
# api-processens 374 pool-fødsler på 9 minutter (46 %).
#
# Disse tests måler det direkte: samme tråd OG samme DB-forbindelse på tværs af
# kald. Det er selve lækagen — ikke en proxy for den.



def _reset_workers():
    """Ryd puljen mellem tests — ellers måler testen sin egen forgænger."""
    with sp._WORKER_LOCK:
        sp._WORKER_IDLE.clear()
        sp._WORKER_STATS["spawned"] = 0
        sp._WORKER_STATS["reused"] = 0


def test_async_genbruger_samme_traad_paa_tvaers_af_kald(monkeypatch):
    """Kernen i fixet: to kald i træk må ikke føde to tråde."""
    _reset_workers()
    _reset_throttle()
    monkeypatch.setattr(sp, "session_prewarm_enabled", lambda: True, raising=True)
    monkeypatch.setattr(sp, "_deepseek_key", lambda: "key", raising=True)

    import core.services.visible_model as vm
    monkeypatch.setattr(
        vm, "_build_visible_chat_messages_for_github",
        lambda *a, **k: [{"role": "system", "content": "sys"}], raising=True,
    )
    monkeypatch.setattr(
        sp, "_post_deepseek",
        lambda *a, **k: {"usage": {"prompt_tokens": 1, "prompt_cache_miss_tokens": 1}},
        raising=True,
    )
    monkeypatch.setattr("core.costing.ledger.record_cost", lambda **_kw: None)

    traade: list[int] = []
    original = sp.warm_session_prefix

    def _maalt(session_id, **kwargs):
        traade.append(_threading.get_ident())
        return original(session_id, **kwargs)

    monkeypatch.setattr(sp, "warm_session_prefix", _maalt, raising=True)

    for i in range(3):
        sp.warm_session_prefix_async(f"chat-genbrug-{i}", force=True)
        _time.sleep(0.35)  # lad workeren blive færdig og lægge sig tilbage

    assert len(traade) == 3, f"alle tre kald skal være kørt, fik {len(traade)}"
    assert len(set(traade)) == 1, f"samme tråd på tværs af kald, fik {set(traade)}"
    stats = sp._worker_stats()
    assert stats["spawned"] == 1, f"kun ÉN tråd må være født, fik {stats}"
    assert stats["reused"] == 2, f"de to næste skal være genbrugt, fik {stats}"


def test_async_foeder_ikke_en_traad_pr_kald(monkeypatch):
    """Ti kald i træk: trådantallet skal ikke vokse med antallet af kald."""
    _reset_workers()
    _reset_throttle()
    monkeypatch.setattr(sp, "warm_session_prefix", lambda *a, **k: {"status": "ok"}, raising=True)

    for i in range(10):
        sp.warm_session_prefix_async(f"chat-mange-{i}")
        _time.sleep(0.05)

    _time.sleep(0.4)
    stats = sp._worker_stats()
    assert stats["spawned"] <= 2, f"ti kald må ikke føde ti tråde, fik {stats}"


def test_async_kaster_aldrig_naar_workeren_fejler(monkeypatch):
    """Self-safe: en fejlende warm må ikke ramme kalderen."""
    _reset_workers()

    def _boom(*_a, **_k):
        raise RuntimeError("warm fejlede")

    monkeypatch.setattr(sp, "warm_session_prefix", _boom, raising=True)
    sp.warm_session_prefix_async("chat-fejl")  # må ikke kaste
    _time.sleep(0.3)
    # workeren skal stadig være i live og kunne tage næste opgave
    assert sp._worker_stats()["spawned"] >= 1
