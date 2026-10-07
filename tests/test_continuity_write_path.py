"""Skrive-vejen til kontinuitets-capsulen — 4/10-2026.

Baggrunden er en målefejl jeg selv lavede, og den er værd at skrive ned, fordi
testene her er formet efter den:

Jeg målte om capsulen blev skrevet efter hver tur, og konkluderede «nej, den
staar stille». Journalen var tavs. Problemet var at den tavse journal IKKE
kunne skelne de to tilstande jeg skulle skelne mellem:

    (a) kaldet sker ikke          → journalen er tom
    (b) kaldet fejler             → journalen er OGSAA tom, fordi det yderste
                                    `except Exception: pass` slugte sporet

Skrive-vejen viste sig at virke hele tiden. Men hullet var aegte: hvis
forberedelsen fejlede (mood-sync, attention, seneste aktivitet), forsvandt
beviset. Test 1 laaser at fejlen nu efterlader et spor. Test 2 laaser at vejen
faktisk skriver — den positive paastand, som hele diagnosen hvilede paa.
"""
from __future__ import annotations

import importlib
import json
import logging

import pytest


@pytest.fixture()
def capsule_paths(tmp_path, monkeypatch):
    """Flyt capsulen til tmp_path — testene maa ikke roere den rigtige fil."""
    continuity = importlib.import_module("core.services.continuity")
    current = tmp_path / "session_capsule.json"
    prev = tmp_path / "session_capsule.prev.json"
    older = tmp_path / "session_capsule.older.json"
    monkeypatch.setattr(continuity, "CAPSULE_DIR", tmp_path)
    monkeypatch.setattr(continuity, "CAPSULE_CURRENT", current)
    monkeypatch.setattr(continuity, "CAPSULE_PREV", prev)
    monkeypatch.setattr(continuity, "CAPSULE_OLDER", older)
    return current


def _run(visible_runs):
    return visible_runs.VisibleRun(
        run_id="visible-continuity-write-path",
        lane="visible",
        provider="ollama",
        model="qwen3.5:9b",
        user_message="Skriv capsulen.",
        session_id="continuity-write-path-session",
    )


def test_fejl_i_skrive_vejen_efterlader_et_spor(isolated_runtime, monkeypatch, caplog):
    """Det yderste except maa ikke laengere vaere et bart `pass`.

    Uden dette kunne «blev ikke kaldt» og «fejlede tavst» ikke skelnes — og det
    var praecis den forskel jeg konkluderede forkert paa.
    """
    visible_runs = importlib.import_module("core.services.visible_runs")
    visible_runs = importlib.reload(visible_runs)
    continuity = importlib.import_module("core.services.continuity")

    def _boom(**kwargs):
        raise RuntimeError("capsule write broke")

    monkeypatch.setattr(continuity, "live_update_after_turn", _boom)

    with caplog.at_level(logging.WARNING, logger="core.services.visible_runs_memory"):
        # Self-safe: en fejl i skrive-vejen maa ALDRIG braekke turen.
        visible_runs._run_memory_postprocess(_run(visible_runs), "Svar.")

    spor = [r for r in caplog.records if "live_update-forberedelse" in r.message]
    assert spor, "fejlen forsvandt igen — sporet skal staa i loggen"
    assert spor[0].levelno == logging.WARNING


def test_skrive_vejen_skriver_capsulen(isolated_runtime, monkeypatch, capsule_paths):
    """Den positive paastand: efter en tur ligger capsulen paa disken.

    Uden denne test ville test 1 kunne bestaa paa et system hvor intet nogensinde
    skrives — den maaler kun at fejl er synlige, ikke at vejen virker.
    """
    visible_runs = importlib.import_module("core.services.visible_runs")
    visible_runs = importlib.reload(visible_runs)

    assert not capsule_paths.exists()

    visible_runs._run_memory_postprocess(_run(visible_runs), "Jeg har skrevet det ned.")

    assert capsule_paths.exists(), "skrive-vejen skrev ingenting"
    data = json.loads(capsule_paths.read_text(encoding="utf-8"))
    assert data.get("captured_at"), "capsulen mangler tidsstempel"
    assert data["recent_activity"]["last_tool_result_summary"].startswith(
        "Jeg har skrevet det ned."
    ), "turens svar landede ikke i capsulen"
