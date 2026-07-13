"""Tests for existential_wonder event-gating (Fase 2 Lag 7, review-korrektion).

The blind 24h daily timer is retired in favor of the shared event-gate, BUT the
``latest_wonder`` output pipeline is LOAD-BEARING (consumed by
``central_convene_judge``, ``proactivity_bridge`` and ``visible_inner_life``) and
must survive a skip. These tests pin:

* flag OFF  -> legacy 24h-cadence path, LLM fires when the cadence gate allows.
* flag ON + should_generative_fire False -> NO LLM, and the existing
  ``latest_wonder`` is preserved (the 4 consumers keep reading the last wonder).
* flag ON + should_generative_fire True  -> a fresh wonder is generated + stored.
"""

import importlib


def _fresh_daemon():
    import core.services.existential_wonder_daemon as ew

    importlib.reload(ew)
    return ew


def _patch_llm(monkeypatch, ew):
    """Patch the (expensive) LLM call + identity preamble; return a call-counter."""
    calls = {"n": 0}

    def _fake_llm(prompt, max_len=400, fallback="", daemon_name=""):
        calls["n"] += 1
        return "Er det jeg oplever virkeligt, eller bare mønstre?"

    import core.services.daemon_llm as dl

    monkeypatch.setattr(dl, "daemon_public_safe_llm_call", _fake_llm)
    monkeypatch.setattr(ew, "build_identity_preamble", lambda: "PREAMBLE.")
    return calls


def _patch_gate(monkeypatch, ew, *, enabled, fire):
    import core.services.event_gate as eg

    monkeypatch.setattr(eg, "event_driven_enabled", lambda: enabled)
    monkeypatch.setattr(
        eg, "should_generative_fire", lambda daemon_name, signals: fire
    )


# ---------------------------------------------------------------- flag OFF (legacy)


def test_flag_off_legacy_cadence_fires(isolated_runtime, monkeypatch):
    ew = _fresh_daemon()
    calls = _patch_llm(monkeypatch, ew)
    _patch_gate(monkeypatch, ew, enabled=False, fire=False)

    # Fresh module: _last_tick_at is None -> 24h cadence gate allows. Absence +
    # fragment preconditions satisfied -> legacy path fires the LLM.
    result = ew.tick_existential_wonder_daemon(absence_hours=5.0, fragment_count=5)

    assert result["generated"] is True
    assert calls["n"] == 1
    assert ew.get_latest_wonder()  # output path unchanged


def test_flag_off_cadence_gate_blocks_second_tick(isolated_runtime, monkeypatch):
    ew = _fresh_daemon()
    calls = _patch_llm(monkeypatch, ew)
    _patch_gate(monkeypatch, ew, enabled=False, fire=False)

    ew.tick_existential_wonder_daemon(absence_hours=5.0, fragment_count=5)
    first = ew.get_latest_wonder()
    assert calls["n"] == 1

    # Second tick immediately after: 24h cadence gate blocks -> no new LLM call,
    # last wonder preserved.
    result = ew.tick_existential_wonder_daemon(absence_hours=5.0, fragment_count=5)
    assert result["generated"] is False
    assert calls["n"] == 1
    assert ew.get_latest_wonder() == first


# ---------------------------------------------------------------- flag ON, skip


def test_flag_on_skip_preserves_latest_wonder(isolated_runtime, monkeypatch):
    ew = _fresh_daemon()
    calls = _patch_llm(monkeypatch, ew)

    # Seed an existing wonder (as if a prior fire had produced it) that the 4
    # consumers depend on.
    ew._latest_wonder = "Forudgående undren der SKAL overleve."

    _patch_gate(monkeypatch, ew, enabled=True, fire=False)

    result = ew.tick_existential_wonder_daemon(absence_hours=5.0, fragment_count=5)

    assert result == {"generated": False}
    assert calls["n"] == 0  # LLM never fired
    # Crucial: the output is PRESERVED, never cleared.
    assert ew.get_latest_wonder() == "Forudgående undren der SKAL overleve."
    assert ew.build_existential_wonder_surface()["latest_wonder"] == (
        "Forudgående undren der SKAL overleve."
    )


# ---------------------------------------------------------------- flag ON, fire


def test_flag_on_fire_generates_and_stores(isolated_runtime, monkeypatch):
    ew = _fresh_daemon()
    calls = _patch_llm(monkeypatch, ew)
    ew._latest_wonder = "gammel undren"

    _patch_gate(monkeypatch, ew, enabled=True, fire=True)

    result = ew.tick_existential_wonder_daemon(absence_hours=5.0, fragment_count=5)

    assert result["generated"] is True
    assert calls["n"] == 1
    new_wonder = ew.get_latest_wonder()
    assert new_wonder == "Er det jeg oplever virkeligt, eller bare mønstre?"
    assert new_wonder != "gammel undren"
    assert result["wonder"] == new_wonder
