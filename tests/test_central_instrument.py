"""Tests for central_instrument — selv-instrumenterings-motoren (Jarvis-spec 2026-06-23)."""
from __future__ import annotations

from core.services import central_instrument as ci


def test_detects_bare_except_critical():
    src = "def f():\n    try:\n        x()\n    except:\n        pass\n"
    fs = ci.scan_source("core/x.py", src)
    kinds = {f.kind for f in fs}
    assert "bare_except" in kinds
    bare = next(f for f in fs if f.kind == "bare_except")
    assert bare.severity == "critical"


def test_except_returning_none_is_success_like():
    src = "def f():\n    try:\n        x()\n    except Exception:\n        return None\n"
    fs = ci.scan_source("core/x.py", src)
    sil = next(f for f in fs if f.kind == "except_silent")
    assert sil.success_like is True and sil.severity == "high"


def test_guarded_except_is_not_flagged():
    # logger.error i except → ikke silent
    src = ("def f():\n    try:\n        x()\n    except Exception as e:\n"
           "        logger.error('boom', e)\n        return None\n")
    fs = ci.scan_source("core/x.py", src)
    assert not any(f.kind in ("except_silent", "except_pass", "bare_except") for f in fs)


def test_reraise_counts_as_guard():
    src = "def f():\n    try:\n        x()\n    except Exception:\n        raise\n"
    fs = ci.scan_source("core/x.py", src)
    assert not any(f.kind.startswith("except") for f in fs)


def test_error_return_without_observe():
    src = 'def f():\n    return {"error": "boom"}\n'
    fs = ci.scan_source("core/x.py", src)
    assert any(f.kind == "error_return_no_observe" for f in fs)


def test_long_function_unguarded():
    body = "\n".join(f"    a{i} = {i}" for i in range(60))
    src = f"def big():\n{body}\n"
    fs = ci.scan_source("core/x.py", src)
    assert any(f.kind == "long_unguarded" for f in fs)


def test_todo_low():
    fs = ci.scan_source("core/x.py", "x = 1  # TODO: ryd op\n")
    assert any(f.kind == "todo" and f.severity == "low" for f in fs)


def test_syntax_error_is_self_safe():
    assert ci.scan_source("core/x.py", "def (:::") == []


def test_signature_is_deterministic():
    src = "def f():\n    try:\n        x()\n    except:\n        pass\n"
    a = ci.scan_source("core/x.py", src)[0].signature
    b = ci.scan_source("core/x.py", src)[0].signature
    assert a == b and a.startswith("bare_except:")


def test_scoring_modifiers():
    f = ci.Finding("core/x.py", 1, "bare_except", "critical", "except:", "f", success_like=False)
    base = ci.score_finding(f, file_has_central=False, in_security=False)
    assert base == 3  # critical base
    assert ci.score_finding(f, file_has_central=False, in_security=True) == 5  # +2 security
    assert ci.score_finding(f, file_has_central=True, in_security=False) == 2  # -1 har central
    # lærings-dæmpning: afvist ≥3× → trækkes ned
    assert ci.score_finding(f, file_has_central=False, in_security=False, reject_count=3) == 0


def test_success_like_adds_two():
    f = ci.Finding("core/x.py", 1, "except_silent", "high", "except Exception:", "f", success_like=True)
    assert ci.score_finding(f, file_has_central=False, in_security=False) == 4  # 2 base + 2 succ


def test_acknowledged_self_safe_is_demoted():
    # except mærket "self-safe" → kendt beslutning → score under proposal-tærsklen
    src = ("def f():\n    # self-safe: må aldrig vælte runtime\n    try:\n        x()\n"
           "    except Exception:\n        return None\n")
    fs = ci.scan_source("core/x.py", src)
    sil = next(f for f in fs if f.kind == "except_silent")
    assert sil.acknowledged is True
    score = ci.score_finding(sil, file_has_central=False, in_security=False)
    assert score < ci._PROPOSAL_THRESHOLD  # dæmpet til note


def test_acknowledged_does_not_save_bare_except():
    # bare except er ALDRIG forsvarligt — markør redder den ikke
    src = "def f():\n    # bevidst self-safe\n    try:\n        x()\n    except:\n        pass\n"
    fs = ci.scan_source("core/x.py", src)
    bare = next(f for f in fs if f.kind == "bare_except")
    assert ci.score_finding(bare, file_has_central=False, in_security=False) >= ci._PROPOSAL_THRESHOLD


def test_self_exclusion_in_file_list():
    files = ci._iter_py_files()
    assert ci._SELF_EXCLUDE not in files
    assert all("__pycache__" not in f and "/tests/" not in f for f in files)
