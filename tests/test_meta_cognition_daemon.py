"""Bölge 2 routing-dækning for core/services/meta_cognition_daemon.py (form-dommer choke-point).

Verificerer at daemonens LLM-kald nu går gennem daemon_llm-choke-pointet (daemon_llm_call),
så form-dommeren + TTL-cachen fanger gentagne kald. Import-smoke + kilde-assertion.
"""
from __future__ import annotations

import importlib
from pathlib import Path


def test_module_imports():
    assert importlib.import_module("core.services.meta_cognition_daemon") is not None


def test_routes_through_form_judge_chokepoint():
    src = Path("core/services/meta_cognition_daemon.py").read_text(encoding="utf-8")
    assert "daemon_llm_call" in src, "Bölge 2: meta_cognition_daemon skal rute LLM-kald gennem daemon_llm_call"
