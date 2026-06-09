"""Tests for runtime settings — pinner jarvis_brain default-tunings.

Disse defaults blev bumpet 2026-06-09 sammen med auto_remember_subscriber.
Hvis de ved et uheld bliver sat tilbage, fanger denne test det.
"""
from __future__ import annotations


def test_jarvis_brain_auto_inject_defaults_for_1m_context() -> None:
    """Defaults reflekterer 1M-context-vinduet + aktiv auto-remember pipe."""
    from core.runtime.settings import load_settings
    s = load_settings()
    # top_k bumpet 3 → 8 så nye auto-remembered fakta faktisk dukker op
    assert s.jarvis_brain_auto_inject_top_k >= 8
    # threshold sænket 0.55 → 0.45 for at lade svag-relevante fakta komme med
    assert s.jarvis_brain_auto_inject_threshold <= 0.50
    # summary-budget bumpet 350 → 900 tokens (stadig <0.1% af 1M context)
    assert s.jarvis_brain_summary_token_budget >= 900


def test_jarvis_brain_remember_caps_allow_auto_remember_pipe() -> None:
    """Per-day cap bumpet 20 → 40 så auto-remember-pipen ikke kvæles."""
    from core.runtime.settings import load_settings
    s = load_settings()
    assert s.jarvis_brain_remember_per_day_cap >= 40
    assert s.jarvis_brain_remember_per_turn_cap >= 5


def test_jarvis_brain_enabled_by_default() -> None:
    """Feature-flag skal være på — ellers no-op'er hele pipelinen."""
    from core.runtime.settings import load_settings
    s = load_settings()
    assert s.jarvis_brain_enabled is True


def test_context_compact_threshold_uses_1m_context() -> None:
    """Auto-compact tærskel skal stå højt — premature compaction var en bug."""
    from core.runtime.settings import load_settings
    s = load_settings()
    # 200k tokens — bumpet fra 40k/60k da visible kører deepseek-v4-flash (1M)
    assert s.context_compact_threshold_tokens >= 200_000
    assert s.context_keep_recent >= 20
