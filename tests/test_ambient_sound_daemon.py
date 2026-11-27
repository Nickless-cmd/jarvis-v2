"""Tests for core.services.ambient_sound_daemon — coarse age via shared helper."""

from core.services.visual_memory import _coarse_age_label


def test_ambient_sound_uses_shared_bucket_helper():
    """ambient_sound_daemon.get_latest_ambient_sound_for_prompt() reuses the
    same _coarse_age_label() from visual_memory so both sensorial sections
    roll on identical bucket boundaries — keeping the prompt-cache prefix
    stable across both. Regression-guard against future drift."""
    import core.services.ambient_sound_daemon as asd
    src = open(asd.__file__).read()
    assert "_coarse_age_label" in src, (
        "ambient_sound_daemon must import _coarse_age_label from visual_memory; "
        "without it, per-minute/per-hour rolls invalidate ~10k tokens of "
        "cacheable prefix every time."
    )


def test_coarse_label_round_trip():
    # Sanity: helper is callable and gives stable strings
    assert _coarse_age_label(30).startswith("(")
    assert _coarse_age_label(500) == "(tidligere i dag)"


def test_audio_llm_prompt_reaches_archive_metadata(monkeypatch):
    """Ambient-svaret skal arkiveres sammen med præcis den sendte prompt."""
    from core.services import ambient_sound_daemon as asd
    import core.services.sensory_archive as archive

    monkeypatch.setattr(asd, "_experiment_enabled", lambda: True)
    monkeypatch.setattr(asd, "_state", lambda: {})
    monkeypatch.setattr(
        asd, "_capture_sample", lambda: ("talk", 0.02, 0.01, None)
    )
    monkeypatch.setattr(asd, "set_runtime_state_value", lambda *_a, **_k: None)
    monkeypatch.setattr(asd, "_store_sample", lambda *_a, **_k: None)
    sent: list[str] = []

    def fake_llm(prompt, **_kwargs):
        sent.append(prompt)
        return "En dæmpet samtale giver rummet en rolig, vågen energi."

    monkeypatch.setattr("core.services.daemon_llm.daemon_llm_call", fake_llm)
    archived: list[dict] = []
    monkeypatch.setattr(
        archive,
        "record_audio",
        lambda _content, **kwargs: archived.append(dict(kwargs["metadata"])) or {"id": "x"},
    )

    result = asd.tick_ambient_sound_daemon()

    assert result["generated"] is True
    assert sent
    assert archived[0]["question"] == sent[0], (
        "ambient_sound arkiverede ikke prompten som gav LLM-svaret"
    )
