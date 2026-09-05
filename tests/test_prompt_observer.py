"""Tests for Prompt-cluster Phase 1 (prompt_observer).

Verificerer paritet (blacklistede sektioner default OFF, resten ON), at en override vinder
(live on/off), at default-tilfældet ikke koster opslag, og at observe_build er self-safe.
"""
from __future__ import annotations

from core.services import prompt_observer as po


# ── section_enabled: paritet + override ──────────────────────────────────
def test_blacklisted_default_off():
    assert po.section_enabled("R2 gate telemetry", blacklisted=True, overrides={}) is False


def test_non_blacklisted_default_on():
    assert po.section_enabled("brain facts", blacklisted=False, overrides={}) is True


def test_override_reenables_blacklisted():
    ov = {"R2 gate telemetry": True}
    assert po.section_enabled("R2 gate telemetry", blacklisted=True, overrides=ov) is True


def test_override_disables_active_section():
    ov = {"brain facts": False}
    assert po.section_enabled("brain facts", blacklisted=False, overrides=ov) is False


def test_override_wins_over_default_both_directions():
    # eksplicit True på en ikke-blacklistet (no-op men eksplicit) og False på blacklistet
    assert po.section_enabled("x", blacklisted=False, overrides={"x": True}) is True
    assert po.section_enabled("y", blacklisted=True, overrides={"y": False}) is False


# ── load_overrides: round-trip via central_switches ──────────────────────
def test_set_section_then_load_roundtrip():
    label = "test-section-roundtrip-xyz"
    try:
        po.set_section(label, False)
        ov = po.load_overrides()
        assert ov.get(label) is False
        po.set_section(label, True)
        ov2 = po.load_overrides()
        assert ov2.get(label) is True
    finally:
        from core.services import shared_cache
        shared_cache.delete("flag:central.switch.prompt_section." + label)


def test_load_overrides_returns_dict():
    assert isinstance(po.load_overrides(), dict)


# ── observe_build: self-safe ─────────────────────────────────────────────
def test_observe_build_never_raises():
    # må aldrig kaste uanset input
    po.observe_build(lane="visible", included=12,
                     dropped_disabled=["a", "b"], dropped_budget=["c"])
    po.observe_build(lane="", included=0, dropped_disabled=[], dropped_budget=[])


# ── katalog ──────────────────────────────────────────────────────────────
def test_catalog_validates_with_prompt():
    from core.services import central_catalog as cc
    assert cc.validate() == []
    assert "prompt" in cc.clusters()


# ── Fejl-kanal (2026-06-23): sektion-builder der kaster bliver synlig ─────
def test_noise_labels_extracted_to_observer():
    """Boy Scout: noise-policy bor nu her (udskilt fra prompt_contract).

    Stikprøven var «R2 gate telemetry» indtil 2026-09-05, hvor den blev taget af
    listen (den bar beskeden om at 71 af 90 advarsler blev ignoreret). Testen
    handler om HVOR politikken bor, ikke om et bestemt label — så den bruger nu
    et der stadig er slukket.
    """
    assert "causal alerts" in po.DIAGNOSTIC_NOISE_LABELS
    assert "room entities" in po.TAIL_NOISE_LABELS
    assert len(po.DIAGNOSTIC_NOISE_LABELS) > 0


def test_observe_section_error_self_safe(monkeypatch):
    import core.services.central_core as cc
    monkeypatch.setattr(cc, "central", lambda: (_ for _ in ()).throw(RuntimeError("nede")))
    po.observe_section_error("indre liv", RuntimeError("boom"))  # må ikke kaste


def test_observe_build_emits_error_channel(monkeypatch):
    seen = {}
    class _C:
        def observe(self, ev): seen.update(ev)
    import core.services.central_core as cc
    monkeypatch.setattr(cc, "central", lambda: _C())
    po.observe_build(lane="visible", included=5, dropped_disabled=[], dropped_budget=[],
                     dropped_error=[("indre liv", "RuntimeError: boom")])
    assert seen["error_count"] == 1
    assert seen["dropped_error"][0]["section"] == "indre liv"


# ---------------------------------------------------------------------------
# Adfærds-gates er ikke diagnostik-støj
#
# 2026-09-05: "decision adherence gate" lå på den hardkodede blacklist og blev
# derfor kastet væk FØR indholdet blev vurderet. Hele kæden bagved virkede —
# review skrev domme, adherence_score blev opdateret, gaten valgte korrekt bånd
# og producerede 1.993 tegn eskaleret tekst med fem beslutninger under 25%. Og
# så nåede beskeden aldrig frem til prompten. En advarsel Jarvis ikke ser, er
# ikke en advarsel.
# ---------------------------------------------------------------------------


# Sektioner der bevidst er TAGET AF listen efter måling. Hver post har kostet en
# undersøgelse; de må ikke kunne slukkes igen uden at nogen tager stilling.
_BEVIDST_TAENDT = {
    # 2026-09-05: adfærdsinstruks, ikke diagnostik. Eskalerer til «DU SKAL...».
    "decision adherence gate",
    # 2026-09-05: begrundelsen «already in guidance rules» var FALSK — hverken
    # «linjeskift», «EGNE ord» eller «Gentag ALDRIG» fandtes i den byggede prompt.
    "markdown formatting",
    "no tool-result echo",
    # 2026-09-05: begrundelsen «merged into brain facts» var FALSK — der findes
    # ingen «brain facts»-sektion. 1.171 tegn af hans vidensresumé, tabt.
    "jarvis brain summary",
    # 2026-09-05: bærer nu emne OG udfald, ikke «Ny samtale ×5» som i juni.
    "conversation continuity (always-on)",
    "cross-session arc",
    "rule engine conclusions",
    # 2026-09-05: diagnostik, ja — men de bærer beskeden om at 71 af 90
    # advarsler blev ignoreret. Systemet vidste det; beskeden var slukket.
    "R2 gate telemetry",
    "loop-compliance self-check",
}


def test_bevidst_taendte_sektioner_er_ikke_blacklistet():
    from core.services.prompt_observer import DIAGNOSTIC_NOISE_LABELS, TAIL_NOISE_LABELS

    slukket_igen = sorted(
        _BEVIDST_TAENDT & (set(DIAGNOSTIC_NOISE_LABELS) | set(TAIL_NOISE_LABELS))
    )
    assert not slukket_igen, (
        "sektioner der bevidst blev tændt efter måling er slukket igen: %s — "
        "hver af dem kostede en undersøgelse, så tag stilling i stedet for at "
        "føje dem tilbage" % ", ".join(slukket_igen)
    )


def test_blacklisten_indeholder_kun_labels_der_findes():
    """En label der er stavet forkert slukker ingenting og skjuler sin egen fejl."""
    import re
    from pathlib import Path

    from core.services.prompt_observer import DIAGNOSTIC_NOISE_LABELS, TAIL_NOISE_LABELS

    kilde = Path("core/services/prompt_contract.py")
    if not kilde.exists():  # kørt uden for repoet
        return
    tekst = kilde.read_text(encoding="utf-8")
    brugte = set(re.findall(r'_(?:awareness|tail)_add\(\s*(?:\d+,\s*)?"([^"]+)"', tekst))
    ukendte = sorted(
        (DIAGNOSTIC_NOISE_LABELS | TAIL_NOISE_LABELS) - brugte
    )
    assert not ukendte, (
        "blacklistede labels som ingen sektion bruger (stavefejl slukker intet): %s"
        % ", ".join(ukendte)
    )
