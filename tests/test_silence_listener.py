"""Tests for silence_listener.py"""

import pytest
from core.services.silence_listener import (
    experience_silence,
    describe_silence,
    format_silence_for_prompt,
    reset_silence_listener,
    build_silence_listener_surface,
)


def setup_function():
    reset_silence_listener()


def test_experience_silence_short():
    experience_silence(30)
    surface = build_silence_listener_surface()
    assert surface["experience_count"] == 0


def test_experience_silence_long():
    experience_silence(120)
    surface = build_silence_listener_surface()
    assert surface["experience_count"] == 1
    assert surface["active"] is True


def test_describe_silence():
    experience_silence(90)
    desc = describe_silence()
    assert "stilhed" in desc


def test_format_silence_for_prompt():
    experience_silence(100)
    result = format_silence_for_prompt()
    assert "STILHED:" in result


def test_build_silence_listener_surface():
    experience_silence(70)
    surface = build_silence_listener_surface()
    assert "experience_count" in surface
    assert "latest" in surface


def test_reset_silence_listener():
    experience_silence(90)
    reset_silence_listener()
    surface = build_silence_listener_surface()
    assert surface["experience_count"] == 0


def test_en_tom_lytter_er_LEVENDE_ikke_doed():
    """Testen pinnede før `active is False` når listen var tom.

    Det var selve fejlen. `cognitive_architecture_surface` læser `active` som
    «systemet lever»; et modul der korrekt melder «ingen stilhed endnu» er
    ikke dødt, det er tomt. Skellet står i `liveness_registry`: en manglende
    eller falsk nøgle blev læst som en påstand om død.
    """
    reset_silence_listener()
    surface = build_silence_listener_surface()
    assert surface["active"] is True
    assert surface["experience_count"] == 0
    assert "endnu" in surface["summary"]


# ── Den fejl der gjorde modulet stumt (25/9-2026) ───────────────────────────


def test_tredive_sekunder_er_IKKE_stilhed():
    """Daemon-blokken kaldte med `duration_seconds=30`, hårdkodet.

    Tærsklen er 60, så kaldet blev gjort ved hvert tik og kunne ALDRIG optage
    noget. Målt: nul oplevelser nogensinde.
    """
    reset_silence_listener()
    assert experience_silence(30) is None
    assert build_silence_listener_surface()["experience_count"] == 0


def test_det_maalte_mellemrum_passerer_taersklen():
    """Første målte mellemrum mellem daemon-blokkens kørsler var 551 s."""
    reset_silence_listener()
    post = experience_silence(551.2)
    assert post is not None
    assert build_silence_listener_surface()["experience_count"] == 1


def test_stilheden_overlever_at_modulet_indlaeses_forfra():
    import importlib

    import core.services.silence_listener as S

    reset_silence_listener()
    experience_silence(600)

    frisk = importlib.reload(S)
    try:
        assert frisk.build_silence_listener_surface()["experience_count"] == 1
    finally:
        frisk.reset_silence_listener()
        importlib.reload(S)


def test_teksturen_er_udledt_og_baerer_sit_grundlag(monkeypatch):
    """Ordet var `random.choice` af fire. Nu skal det kunne føres tilbage."""
    import core.services.silence_listener as S

    reset_silence_listener()
    monkeypatch.setattr(S, "_tekstur", S._tekstur)  # ingen mock — mål den ægte

    # Ingen kø: ordet kommer fra længden alene.
    monkeypatch.setitem(
        __import__("sys").modules, "core.services.initiative_queue",
        type("M", (), {"build_initiative_queue_surface": staticmethod(
            lambda: {"pending_count": 0})})())

    kort = S.experience_silence(120)
    lang = S.experience_silence(2000)

    assert kort["texture"] == "tom" and "120s" in kort["grundlag"]
    assert lang["texture"] == "dyb" and "2000s" in lang["grundlag"]


def test_noget_der_venter_goer_stilheden_ventende(monkeypatch):
    import sys

    import core.services.silence_listener as S

    reset_silence_listener()
    monkeypatch.setitem(
        sys.modules, "core.services.initiative_queue",
        type("M", (), {"build_initiative_queue_surface": staticmethod(
            lambda: {"pending_count": 3})})())

    post = S.experience_silence(120)
    assert post["texture"] == "ventende"
    assert "3 i køen" in post["grundlag"]
