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
