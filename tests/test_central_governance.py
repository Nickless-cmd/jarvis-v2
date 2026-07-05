from __future__ import annotations
import core.services.central_governance as gov


def _store(monkeypatch):
    store = {}
    monkeypatch.setattr(gov, "_kv_get", lambda k, d: store.get(k, d))
    monkeypatch.setattr(gov, "_kv_set", lambda k, v: store.update({k: v}))
    return store


def test_list_flags_returns_all_with_values_and_danger(monkeypatch):
    _store(monkeypatch)
    flags = gov.list_flags()
    keys = {f["key"] for f in flags}
    assert {"lag4_live", "gut_consumer_mode", "generative_autonomy", "self_prompt",
            "healer_enabled", "injection:cognitive_state"} <= keys
    lag4 = next(f for f in flags if f["key"] == "lag4_live")
    assert lag4["dangerous"] is True
    assert "value" in lag4
    sp = next(f for f in flags if f["key"] == "self_prompt")
    assert sp["dangerous"] is False


def test_set_nondangerous_flag_writes(monkeypatch):
    store = _store(monkeypatch)
    res = gov.set_flag("self_prompt", True, confirm=False)
    assert res["ok"] is True
    assert store.get("central_self_prompt_enabled") is True


def test_set_dangerous_flag_requires_confirm(monkeypatch):
    store = _store(monkeypatch)
    res = gov.set_flag("generative_autonomy", False, confirm=False)
    assert res["ok"] is False and res.get("needs_confirm") is True
    assert "generative_autonomy_enabled" not in store   # ikke skrevet
    res2 = gov.set_flag("generative_autonomy", False, confirm=True)
    assert res2["ok"] is True
    assert store.get("generative_autonomy_enabled") is False


def test_set_unknown_flag_errors(monkeypatch):
    _store(monkeypatch)
    res = gov.set_flag("nope", True, confirm=True)
    assert res["ok"] is False and "ukendt" in res.get("error", "").lower()


def test_enum_flag_validates_value(monkeypatch):
    _store(monkeypatch)
    ok = gov.set_flag("gut_consumer_mode", "shadow", confirm=True)
    assert ok["ok"] is True
    bad = gov.set_flag("gut_consumer_mode", "banana", confirm=True)
    assert bad["ok"] is False


def test_successful_write_records_mutation(monkeypatch):
    _store(monkeypatch)
    published = []
    monkeypatch.setattr("core.eventbus.bus.event_bus.publish",
                        lambda kind, payload=None, **kw: published.append((kind, payload)))
    observed = []
    class _C:
        def observe(self, ev): observed.append(ev)
    monkeypatch.setattr("core.services.central_core.central", lambda: _C())

    res = gov.set_flag("self_prompt", False, confirm=False)
    assert res["ok"] is True
    # eventbus-audit fyrede som 'central.mutation' med area/key/value
    assert any(k == "central.mutation" for k, _ in published)
    kind, payload = next((k, p) for k, p in published if k == "central.mutation")
    assert payload.get("area") == "governance"
    assert payload.get("key") == "self_prompt" and payload.get("value") is False
    # central observe fyrede for governance-området
    assert any(e.get("cluster") == "governance" for e in observed)


def test_healer_flag_reads_from_healer_source(monkeypatch):
    # Runtime-state-store forbliver tom → DB-default ville give False.
    _store(monkeypatch)
    # Men healer-registret er reelt tændt via SIN egen kilde (shared_cache).
    import core.services.error_healers as eh
    monkeypatch.setattr(eh, "_flag_on", lambda name, default=False: name == "enabled")
    flags = {f["key"]: f["value"] for f in gov.list_flags()}
    # Governance skal afspejle healer-kilden, ikke den tomme runtime-state-DB.
    assert flags["healer_enabled"] is True
    assert flags["healer_daemon_restart_live"] is False
    assert flags["healer_syslog_restart_live"] is False


def test_failed_write_does_not_record(monkeypatch):
    _store(monkeypatch)
    published = []
    monkeypatch.setattr("core.eventbus.bus.event_bus.publish",
                        lambda kind, payload=None, **kw: published.append((kind, payload)))
    # dangerous uden confirm → ingen write, ingen audit
    res = gov.set_flag("generative_autonomy", False, confirm=False)
    assert res["ok"] is False
    assert published == []
