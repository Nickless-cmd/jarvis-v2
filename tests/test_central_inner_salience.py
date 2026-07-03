"""Verificér Centralens salience-gate for det private indre (spec §6.1b/§9, 3. jul).

FØRSTE ARKETYPE: Centralen BESTEMMER om inner_voice skal genudledes via LLM eller genbruges fra
det holdte selv. Tovejs, flag-styret (off/shadow/on), self-safe. Hermetisk — kv i hukommelsen.
"""
from __future__ import annotations

import pytest

from core.services import central_inner_salience as cis


@pytest.fixture(autouse=True)
def _mem_kv(monkeypatch):
    store: dict[str, object] = {}
    monkeypatch.setattr(cis, "_kv_get", lambda k, d: store.get(k, d))
    monkeypatch.setattr(cis, "_kv_set", lambda k, v: store.__setitem__(k, v))
    # trace/observe → no-op (undgå central_timeseries-afhængighed i unit-test)
    monkeypatch.setattr(cis, "_trace", lambda *a, **k: None)
    yield store


VOICE = {"mood_tone": "let", "self_position": "midt i arbejdet", "current_concern": "",
         "current_pull": "binde lagene"}


def test_key_ignores_volatile_fields():
    k1 = cis.salience_key_for_voice({**VOICE, "run_id": "a", "voice_line": "x"})
    k2 = cis.salience_key_for_voice({**VOICE, "run_id": "b", "voice_line": "y"})
    assert k1 == k2  # kun mood/position/bekymring/retning tæller


def test_off_never_reuses(_mem_kv):
    _mem_kv[cis._FLAG_KEY] = "off"
    key = cis.salience_key_for_voice(VOICE)
    cis.note_enriched_voice(run_id="r1", key=key, value="En rolig linje.")
    d = cis.decide_voice(run_id="r2", key=key)
    assert d["reuse"] is False and d["mode"] == "off"


def test_shadow_measures_but_does_not_reuse(_mem_kv):
    _mem_kv[cis._FLAG_KEY] = "shadow"
    key = cis.salience_key_for_voice(VOICE)
    cis.note_enriched_voice(run_id="r1", key=key, value="En rolig linje.")
    d = cis.decide_voice(run_id="r2", key=key)
    assert d["reuse"] is False          # shadow ændrer ikke adfærd
    assert d["would_reuse"] is True     # men MÅLER at den ville genbruge


def test_on_reuses_when_self_unmoved(_mem_kv):
    _mem_kv[cis._FLAG_KEY] = "on"
    key = cis.salience_key_for_voice(VOICE)
    cis.note_enriched_voice(run_id="r1", key=key, value="En rolig linje.")
    d = cis.decide_voice(run_id="r2", key=key)
    assert d["reuse"] is True
    assert d["held"] == "En rolig linje."   # NED: genbruger det holdte selv


def test_on_reenriches_when_self_moved(_mem_kv):
    _mem_kv[cis._FLAG_KEY] = "on"
    key1 = cis.salience_key_for_voice(VOICE)
    cis.note_enriched_voice(run_id="r1", key=key1, value="En rolig linje.")
    moved = {**VOICE, "mood_tone": "tung", "current_pull": "hvile"}
    key2 = cis.salience_key_for_voice(moved)
    d = cis.decide_voice(run_id="r2", key=key2)
    assert d["reuse"] is False   # bevæget → genudled via LLM


def test_ttl_expiry_forces_reenrich(_mem_kv, monkeypatch):
    _mem_kv[cis._FLAG_KEY] = "on"
    key = cis.salience_key_for_voice(VOICE)
    cis.note_enriched_voice(run_id="r1", key=key, value="En rolig linje.")
    # spol tiden forbi TTL
    held = _mem_kv[cis._STATE_KEY]["voice"]
    held["ts"] = held["ts"] - cis._TTL_SECONDS - 10
    d = cis.decide_voice(run_id="r2", key=key)
    assert d["reuse"] is False   # for gammelt → genudled


def test_self_safe_on_kv_failure(monkeypatch):
    monkeypatch.setattr(cis, "_kv_get", lambda k, d: (_ for _ in ()).throw(RuntimeError("boom")))
    d = cis.decide_voice(run_id="r", key="k")
    assert d["reuse"] is False   # fejl → aldrig genbrug (konservativt: enrich som før)
