"""Tests for diagnosis_gate (spec 2026-06-14 §3.4)."""
from __future__ import annotations

from core.services.diagnosis_gate import analyze_diagnosis, diagnosis_gate_enforce


# ── Detektion: diagnostiske konklusioner skal fanges ──

def test_diagnosis_pattern_orphaned() -> None:
    r = analyze_diagnosis("Filen er orphaned — ikke integreret i main.ts.")
    assert r.detected and not r.verified


def test_diagnosis_pattern_zombie() -> None:
    r = analyze_diagnosis("Broen er zombie og svarer ikke.")
    assert r.detected and not r.verified


def test_diagnosis_pattern_commits_behind() -> None:
    r = analyze_diagnosis("Containeren er 3124 commits bagud.")
    assert r.detected and not r.verified


def test_diagnosis_pattern_not_fired() -> None:
    r = analyze_diagnosis("Wakeup'en fyrede ikke i nat.")
    assert r.detected and not r.verified


def test_diagnosis_pattern_not_found() -> None:
    r = analyze_diagnosis("Scheduled_events.json findes ikke.")
    assert r.detected and not r.verified


# ── Undtagelser: må IKKE fanges som uverificeret ──

def test_diagnosis_exempt_uncertainty() -> None:
    r = analyze_diagnosis("Jeg tror filen er orphaned, men er ikke sikker.")
    assert r.detected is False  # usikkerheds-signal → ikke selvsikker diagnose


def test_diagnosis_exempt_verification_reference() -> None:
    r = analyze_diagnosis("Jeg grep'ede main.ts og broen er ikke integreret.")
    assert r.detected and r.verified  # eksplicit verificerings-reference


def test_diagnosis_exempt_source_reference() -> None:
    r = analyze_diagnosis("Containeren er 78 commits foran (se §3 i loggen).")
    assert r.verified  # §-kilde tæller som verificering


def test_diagnosis_exempt_meaning() -> None:
    r = analyze_diagnosis("Det var en god dag, tak for hjælpen.")
    assert r.detected is False


# ── Verifikation via tool-brug ──

def test_verified_when_grep_tool_used() -> None:
    r = analyze_diagnosis("Broen er ikke integreret i main.ts.", tools_used=["grep"])
    assert r.detected and r.verified


def test_unverified_when_unrelated_tool_used() -> None:
    r = analyze_diagnosis("Broen er zombie.", tools_used=["get_weather"])
    assert r.detected and not r.verified


# ── Enforce er advisory: returnerer tekst uændret ──

def test_enforce_advisory_returns_unchanged() -> None:
    txt = "Containeren er 99 commits bagud."
    out = diagnosis_gate_enforce(txt, session_id="s1", run_id="r1")
    assert out == txt  # FASE 1: logger men blokerer/ændrer ikke


def test_enforce_never_raises_on_garbage() -> None:
    assert diagnosis_gate_enforce("", run_id="r") == ""
    assert diagnosis_gate_enforce("normal besked uden diagnose") == "normal besked uden diagnose"


# ── Promise-ledger §8: uverificerede completion-claims ──

from core.services.diagnosis_gate import analyze_completion_claim  # noqa: E402


def test_completion_claim_unverified_without_tool() -> None:
    r = analyze_completion_claim("Jeg har committet ændringen til main.")
    assert r.detected and not r.verified


def test_completion_claim_verified_with_bash() -> None:
    r = analyze_completion_claim("Jeg har committet ændringen.", tools_used=["bash"])
    assert r.detected and r.verified


def test_completion_claim_verified_with_reference() -> None:
    r = analyze_completion_claim("Det er deployet — jeg kørte systemctl og loggen viser active.")
    assert r.verified


def test_completion_claim_exempt_uncertainty() -> None:
    r = analyze_completion_claim("Jeg tror det er committet, men er ikke sikker.")
    assert r.detected is False


def test_completion_claim_ignores_normal_text() -> None:
    r = analyze_completion_claim("Det var en god snak, tak.")
    assert r.detected is False


# ── Promise-ledger §8 FODNOTE (16. jun lie-crisis → 06. jul fodnote-redesign) ──
def test_enforce_footnotes_unverified_completion_claim() -> None:
    """2026-07-06: en uverificeret completion-claim BLOKERER ikke længere —
    Jarvis' besked BEVARES og en ⚠️-fodnote appenderes i bunden. Detektionen er
    uændret (den fyrer stadig)."""
    txt = "Færdig! Jeg har committet ændringen til main."
    out = diagnosis_gate_enforce(txt, session_id="s1", run_id="r1", tools_used=[])
    assert out != txt  # ændret (fodnote tilføjet)
    assert txt in out  # men den ORIGINALE besked er BEVARET
    assert "committet ændringen" in out  # teksten er IKKE fjernet
    assert "⚠️" in out  # fodnote i bunden
    assert out.index("⚠️") > out.index("committet ændringen")  # fodnoten er i bunden


def test_enforce_allows_verified_completion_claim() -> None:
    """Med ægte tool-evidens (bash) passerer claim'en uændret."""
    txt = "Jeg har committet ændringen til main."
    out = diagnosis_gate_enforce(txt, session_id="s1", run_id="r1", tools_used=["bash"])
    assert out == txt


def test_enforce_completion_killswitch(monkeypatch) -> None:
    """Killswitch: _PROMISE_ENFORCE=False → tilbage til ren advisory (uændret)."""
    import core.services.diagnosis_gate as dg
    monkeypatch.setattr(dg, "_PROMISE_ENFORCE", False)
    txt = "Jeg har committet ændringen til main."
    assert dg.diagnosis_gate_enforce(txt, tools_used=[]) == txt
