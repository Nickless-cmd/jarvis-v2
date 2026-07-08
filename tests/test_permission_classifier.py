# tests/test_permission_classifier.py
import core.services.permission_classifier as pc


def _reset_db():
    from core.runtime.db_core import connect
    with connect() as conn:
        conn.execute("DROP TABLE IF EXISTS permission_classifier_stats")
    pc._pred_cache.clear()
    pc._stash.clear()


def test_is_mutating():
    assert pc.is_mutating("write_file") and pc.is_mutating("operator_bash")
    assert not pc.is_mutating("read_file") and not pc.is_mutating("search_memory")


def test_mode_defaults_shadow(monkeypatch):
    monkeypatch.delenv("JARVIS_PERMISSION_CLASSIFIER_MODE", raising=False)
    monkeypatch.setattr("core.runtime.settings.load_settings", lambda: type("S", (), {"extra": {}})())
    assert pc.permission_classifier_mode() == "shadow"


def test_mode_env_wins(monkeypatch):
    monkeypatch.setenv("JARVIS_PERMISSION_CLASSIFIER_MODE", "off")
    assert pc.permission_classifier_mode() == "off"


def test_classify_parses_llm_json(monkeypatch):
    _reset_db()
    monkeypatch.setattr("core.services.daemon_llm.daemon_llm_call",
                        lambda *a, **k: '{"verdict":"approve","confidence":0.92,"reason":"safe workspace write"}')
    p = pc.classify_action("write_file", {"path": "/tmp/x"}, {})
    assert p.verdict == "approve" and p.confidence == 0.92


def test_classify_caches_by_signature(monkeypatch):
    _reset_db()
    calls = []
    monkeypatch.setattr("core.services.daemon_llm.daemon_llm_call",
                        lambda *a, **k: calls.append(1) or '{"verdict":"deny","confidence":0.8,"reason":"x"}')
    pc.classify_action("write_file", {"path": "/etc/x"}, {})
    pc.classify_action("write_file", {"path": "/etc/x"}, {})
    assert len(calls) == 1  # second served from cache


def test_classify_error_is_uncertain(monkeypatch):
    _reset_db()
    def _boom(*a, **k):
        raise RuntimeError("llm down")
    monkeypatch.setattr("core.services.daemon_llm.daemon_llm_call", _boom)
    p = pc.classify_action("write_file", {"path": "/tmp/y"}, {})
    assert p.verdict == "uncertain" and p.confidence == 0.0


def test_trust_earned_after_threshold():
    _reset_db()
    for _ in range(pc._TRUST_MIN_PREDICTIONS):
        pc.record_prediction_outcome("write_file", predicted="approve", actual="approve", is_owner_gold=False)
    assert pc.classifier_trust("write_file") == "trusted"


def test_trust_not_earned_below_threshold():
    _reset_db()
    for _ in range(pc._TRUST_MIN_PREDICTIONS - 1):
        pc.record_prediction_outcome("operator_bash", predicted="approve", actual="approve", is_owner_gold=False)
    assert pc.classifier_trust("operator_bash") == "untrusted"


def test_gold_miss_resets_trust():
    _reset_db()
    for _ in range(pc._TRUST_MIN_PREDICTIONS):
        pc.record_prediction_outcome("write_file", predicted="approve", actual="approve", is_owner_gold=False)
    assert pc.classifier_trust("write_file") == "trusted"
    # a real owner disagreement wipes the earned trust
    pc.record_prediction_outcome("write_file", predicted="approve", actual="deny", is_owner_gold=True)
    assert pc.classifier_trust("write_file") == "untrusted"


def test_unknown_tool_untrusted():
    _reset_db()
    assert pc.classifier_trust("never_seen") == "untrusted"


def test_should_auto_allow_all_conditions():
    _reset_db()
    for _ in range(pc._TRUST_MIN_PREDICTIONS):
        pc.record_prediction_outcome("write_file", predicted="approve", actual="approve", is_owner_gold=False)
    approve = pc.PermissionPrediction("approve", 0.95, "ok")
    assert pc.should_auto_allow("write_file", approve, gates_green=True, role="owner") is True
    # each missing condition → False
    assert pc.should_auto_allow("write_file", approve, gates_green=False, role="owner") is False
    assert pc.should_auto_allow("write_file", approve, gates_green=True, role="member") is False
    assert pc.should_auto_allow("write_file", pc.PermissionPrediction("deny", 0.95, "x"),
                                gates_green=True, role="owner") is False
    assert pc.should_auto_allow("write_file", pc.PermissionPrediction("approve", 0.5, "x"),
                                gates_green=True, role="owner") is False
    assert pc.should_auto_allow("operator_bash", approve, gates_green=True, role="owner") is False  # untrusted tool


def test_stash_and_pop():
    _reset_db()
    pc.stash_prediction("appr-1", "write_file", "approve")
    d = pc.pop_prediction("appr-1")
    assert d == {"tool": "write_file", "predicted": "approve"}
    assert pc.pop_prediction("appr-1") is None  # popped once


def test_surface_shape():
    _reset_db()
    pc.record_prediction_outcome("write_file", predicted="approve", actual="approve", is_owner_gold=False)
    surf = pc.build_permission_classifier_surface()
    assert surf["active"] is True and surf["mode"] in ("off", "shadow", "active")
    assert any(t["tool"] == "write_file" for t in surf["tools"])
