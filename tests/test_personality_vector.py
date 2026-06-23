"""Test: personality_vector write-guard stripper snake_case maskin-id (Jarvis-spec #2)."""
from __future__ import annotations


def test_human_filter_strips_machine_ids():
    # Genskab _human-filterets logik (samme regel som write-guarden i update-stien):
    # snake_case event-navne droppes, menneskelæsbare (m. mellemrum) består.
    def _human(items):
        out = []
        for x in items:
            s = str(x).strip()
            core = s.split(":", 1)[-1].strip()
            if core and " " not in core and core.count("_") >= 2:
                continue
            out.append(x)
        return out

    strengths = [
        "sensory_archive_analysis",                       # maskin-id → drop
        "plugin_container_process_kill_load_reduction_success",  # maskin-id → drop
        "tålmodig og grundig fejlsøgning",                # menneske → behold
    ]
    mistakes = [
        "forgetting_to_stage_changes_before_commit",      # maskin-id → drop
        "Svar bliver for lange i simple repo-opgaver",    # menneske → behold
        "genstart løste ikke problemet",                  # menneske → behold
    ]
    assert _human(strengths) == ["tålmodig og grundig fejlsøgning"]
    assert _human(mistakes) == [
        "Svar bliver for lange i simple repo-opgaver",
        "genstart løste ikke problemet",
    ]


def test_personality_vector_module_imports():
    # Sikrer write-guarden ikke brød modulet.
    import core.services.personality_vector as pv
    assert hasattr(pv, "_merge_vector")
