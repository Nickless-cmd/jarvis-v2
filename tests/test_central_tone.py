"""tests/test_central_tone.py — Centralens sproglige TONE-PROFIL (rådets #5).

J.A.R.V.I.S har en karakteristisk stemme — præcis, køligt-varm, human, kortfattet.
Den KERNE er konstant; system-/valens-tilstanden MODULERER den (mere skarp ved uro,
mere varm ved varme, mere vågen ved tryk) uden at overskrive den.

Testene mocker valens (integrate_valence) + affekt (build_affect_surface) og verificerer
at build_tone_profile afleder det rigtige register + bevarer J.A.R.V.I.S-kernen i ALLE
tilstande + kalder absorb + er self-safe når kilderne mangler.
"""
from __future__ import annotations

import core.services.central_tone as ct

# J.A.R.V.I.S-kerne-ord der SKAL være til stede uanset tilstand.
_CORE_TOKENS = ("præcis", "køligt-varm")


def _mock(monkeypatch, *, valence=None, affect=None, record=True):
    calls = {"absorb": []}

    def fake_valence():
        if valence is None:
            raise RuntimeError("no valence")
        return dict(valence)

    def fake_affect():
        if affect is None:
            raise RuntimeError("no affect")
        return dict(affect)

    def fake_absorb(cluster, nerve, value, **kw):
        calls["absorb"].append((cluster, nerve, value, kw))

    monkeypatch.setattr(ct, "_read_valence", fake_valence)
    monkeypatch.setattr(ct, "_read_affect", fake_affect)
    monkeypatch.setattr(ct, "_absorb", fake_absorb)
    # Default: intet system-pres, så affekt-stien testes rent. Tests der vil
    # verificere pres-tvang overrider dette selv.
    monkeypatch.setattr(ct, "_read_pressure_signals", lambda: {})
    return calls


def _core_present(profile):
    """J.A.R.V.I.S-kernen skal kunne læses ud af descriptors ELLER guidance."""
    blob = " ".join(profile.get("descriptors") or []) + " " + str(profile.get("guidance") or "")
    blob = blob.lower()
    return all(tok in blob for tok in _CORE_TOKENS)


def test_ro_gives_rolig_praecis(monkeypatch):
    _mock(monkeypatch,
          valence={"tone": "neutral", "intensity": 0.0, "score": 0.0},
          affect={"dominant": "ro", "total": 10})
    p = ct.build_tone_profile()
    assert p["register"] == "rolig-præcis"
    assert _core_present(p)
    assert p["dominant_affect"] == "ro"


def test_uro_gives_skarp_komprimeret(monkeypatch):
    _mock(monkeypatch,
          valence={"tone": "belastet", "intensity": 0.7, "score": -0.3},
          affect={"dominant": "uro", "total": 12})
    p = ct.build_tone_profile()
    assert p["register"] == "skarp-komprimeret"
    assert _core_present(p)


def test_incidents_force_skarp_even_without_uro_affect(monkeypatch):
    """Åbne incidents/breakers skal trække tonen skarp, selv uden uro-affekt."""
    _mock(monkeypatch,
          valence={"tone": "neutral", "intensity": 0.1, "score": 0.0},
          affect={"dominant": "ro", "total": 8})
    monkeypatch.setattr(ct, "_read_pressure_signals", lambda: {"incidents": 3, "breakers": 1})
    p = ct.build_tone_profile()
    assert p["register"] == "skarp-komprimeret"
    assert _core_present(p)


def test_varme_gives_varm_naer(monkeypatch):
    _mock(monkeypatch,
          valence={"tone": "blomstrende", "intensity": 0.3, "score": 0.4},
          affect={"dominant": "varme", "total": 9})
    p = ct.build_tone_profile()
    assert p["register"] == "varm-nær"
    assert _core_present(p)


def test_tryk_gives_vaagen_taet(monkeypatch):
    _mock(monkeypatch,
          valence={"tone": "let", "intensity": 0.5, "score": 0.1},
          affect={"dominant": "tryk", "total": 11})
    p = ct.build_tone_profile()
    assert p["register"] == "vågen-tæt"
    assert _core_present(p)


def test_core_present_in_all_states(monkeypatch):
    """J.A.R.V.I.S-kernen (præcis / køligt-varm) er til stede i ALLE tilstande."""
    for aff in ("ro", "uro", "varme", "tryk"):
        _mock(monkeypatch,
              valence={"tone": "neutral", "intensity": 0.2, "score": 0.0},
              affect={"dominant": aff, "total": 5})
        p = ct.build_tone_profile()
        assert _core_present(p), f"kerne mangler ved affekt={aff}"


def test_self_safe_missing_sources_gives_neutral(monkeypatch):
    """Manglende valens/affekt → neutral profil, ingen crash, absorb stadig kaldt."""
    calls = _mock(monkeypatch, valence=None, affect=None)
    # ingen pressure-signaler heller
    monkeypatch.setattr(ct, "_read_pressure_signals", lambda: {})
    p = ct.build_tone_profile()
    assert p["register"] == "rolig-præcis"  # neutral default
    assert _core_present(p)
    assert p["dominant_affect"] == "ro"
    assert p["intensity"] == 0.0
    assert calls["absorb"], "absorb skal være kaldt selv ved tom kilde"
    cluster, nerve, value, _ = calls["absorb"][0]
    assert cluster == "tone"
    assert nerve == "profile"
    assert "register" in value


def test_absorb_called_with_learn_key(monkeypatch):
    calls = _mock(monkeypatch,
                  valence={"tone": "neutral", "intensity": 0.0, "score": 0.0},
                  affect={"dominant": "ro", "total": 3})
    monkeypatch.setattr(ct, "_read_pressure_signals", lambda: {})
    ct.build_tone_profile()
    assert calls["absorb"]
    _, _, _, kw = calls["absorb"][0]
    assert kw.get("learn_key") == "tone:profile"


def test_guidance_is_short_string(monkeypatch):
    _mock(monkeypatch,
          valence={"tone": "neutral", "intensity": 0.0, "score": 0.0},
          affect={"dominant": "ro", "total": 3})
    monkeypatch.setattr(ct, "_read_pressure_signals", lambda: {})
    p = ct.build_tone_profile()
    assert isinstance(p["guidance"], str)
    assert 0 < len(p["guidance"]) <= 160


def test_descriptors_are_2_to_3(monkeypatch):
    _mock(monkeypatch,
          valence={"tone": "belastet", "intensity": 0.6, "score": -0.3},
          affect={"dominant": "uro", "total": 3})
    monkeypatch.setattr(ct, "_read_pressure_signals", lambda: {})
    p = ct.build_tone_profile()
    assert 2 <= len(p["descriptors"]) <= 3
