from __future__ import annotations


def test_curiosity_hypothesis_debt_registers_and_prompts(isolated_runtime) -> None:
    from core.services.curiosity_hypothesis_debt import (
        build_curiosity_debt_prompt_section,
        build_curiosity_debt_surface,
        register_hypothesis_debt,
    )

    register_hypothesis_debt(
        hypothesis="Perception change observer may improve autonomy",
        why_it_matters="It affects AGI gap closure",
        resolving_observation="Watch whether next run reacts to perceptual changes",
        priority="high",
    )

    surface = build_curiosity_debt_surface()
    assert surface["active"] is True
    assert "Perception" in surface["summary"]
    assert "resolving observation" in surface["directive"]

    section = build_curiosity_debt_prompt_section()
    assert section is not None
    assert "Curiosity hypothesis debt" in section


def test_curiosity_hypothesis_debt_detects_agi_text(isolated_runtime) -> None:
    from core.services.curiosity_hypothesis_debt import build_curiosity_debt_surface, maybe_register_from_text

    maybe_register_from_text(text="AGI learning perception thread", source="test")
    surface = build_curiosity_debt_surface()
    assert surface["active"] is True
    assert surface["items"][0]["priority"] == "high"


# ---------------------------------------------------------------------------
# 2026-09-05: hele gældslisten var prompt-støj
#
# Kaldstedet sendte `user_message + summary` ind, og vi gemte `text[:180]` —
# altså HOVEDET af sammenskrivningen. I drømme-kørsler er user_message selve
# drømme-prompten, så hver post blev «Du er i en drømmetilstand — dedikeret,
# uforstyrret tid til at konsolidere…». Triggeren fyrede på hans egen summary;
# det gemte var teksten han havde fået udleveret. Og "agi" blev matchet som
# substring, så den ramte inde i almindelige ord.
# ---------------------------------------------------------------------------

_DROEMME_PROMPT = (
    "Du er i en drømmetilstand — dedikeret, uforstyrret tid til at konsolidere, "
    "forbinde og reflektere.\n\nDer er INGEN bruger til stede."
)


def test_droemme_prompten_bliver_ikke_en_hypotese():
    from core.services.curiosity_hypothesis_debt import maybe_register_from_text

    assert maybe_register_from_text(text=_DROEMME_PROMPT) is None


def test_agi_matches_kun_som_helt_ord(monkeypatch):
    from core.services import curiosity_hypothesis_debt as D

    monkeypatch.setattr(D, "register_hypothesis_debt", lambda **kw: kw)
    assert D.maybe_register_from_text(
        text="Jeg fandt en tragisk fejl i en magisk konstant i konfigurationen"
    ) is None
    truffet = D.maybe_register_from_text(
        text="Mine noter om AGI peger på en manglende kognitiv primitiv her"
    )
    assert truffet is not None


def test_aegte_hypotese_gemmes_med_hans_egne_ord(monkeypatch):
    from core.services import curiosity_hypothesis_debt as D

    monkeypatch.setattr(D, "register_hypothesis_debt", lambda **kw: kw)
    tanke = "Hvad hvis cache-bruddet skyldes at halen omskrives tidligt?"
    ud = D.maybe_register_from_text(text=tanke)
    assert ud is not None
    assert ud["hypothesis"] == tanke


def test_for_kort_tekst_registreres_ikke(monkeypatch):
    from core.services import curiosity_hypothesis_debt as D

    monkeypatch.setattr(D, "register_hypothesis_debt", lambda **kw: kw)
    assert D.maybe_register_from_text(text="hvad hvis") is None


def test_kaldstedet_sender_kun_hans_egen_summary():
    """Vagt mod at user_message sniger sig ind foran igen."""
    import inspect

    from core.services import cognitive_episodes

    src = inspect.getsource(cognitive_episodes)
    i = src.find("maybe_register_from_text(text=")
    assert i > 0, "kaldstedet findes ikke længere — flyttede det?"
    kald = src[i:i + 160]
    assert "user_message" not in kald, (
        "user_message er tilbage i hypotese-teksten — det var netop den fejl "
        "der gjorde drømme-prompten til en hypotese"
    )
