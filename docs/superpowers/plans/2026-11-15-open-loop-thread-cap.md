# Open-loop Thread Cap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Giv nye open-loop-signaler en tråd, bevar forfald, håndhæv loft 128 og gør lukning irreversibel.

**Architecture:** Registry-lageret udskilles først fra den overstore executive-signalfil. Open-loop-upsert opretter derefter signal og tråd atomisk; servicelaget synliggør loftafvisning og refresh ejer særskilt inaktivitetsudløb.

**Tech Stack:** Python 3.11, sqlite3, pytest

**Spec:** `docs/superpowers/specs/2026-11-15-open-loop-thread-cap-design.md`

## Global Constraints

- Ingen ændring af de 118 eksisterende produktionsrækker.
- Loftet 128 har ét definitionssted.
- Normal bevis-lukning kræver fortsat evidence og en senere run.
- Brug TDD og kør syntax-smoke samt relevante og fulde tests før commit.

## Review Focus

- Samtidig oprettelse ved loftet må ikke kunne passere begge tællinger.
- En eksisterende aktiv række må ikke få en ny tråd ved hver observation.
- En lukket række og dens status_reason skal forblive uændret ved genobservation.
- Stale tråde skal udløbe uden falsk closure_evidence.
- Loftafvisning skal kunne observeres uden en delvist oprettet tråd eller række.

---

### Task 1: Udskil thread-registry

**Files:**
- Create: `core/runtime/db_runtime_open_loop_threads.py`
- Modify: `core/runtime/db_runtime_executive_signals.py`
- Test: `tests/test_thread_registry.py`

- [ ] Flyt registry schema, deklaration, opslag og listning til det fokuserede modul og re-eksportér symbolerne.
- [ ] Kør eksisterende thread-registry-tests og bekræft uændret adfærd.

### Task 2: Test og implementér tråd ved oprettelse og terminal historik

**Files:**
- Modify: `tests/test_thread_registry.py`
- Modify: `core/runtime/db_runtime_executive_signals.py`
- Modify: `core/services/open_loop_signal_tracking.py`

- [ ] Skriv tests for normal oprettelse → bevis-lukning og lukket række → ny åben række.
- [ ] Kør testene røde.
- [ ] Tilføj atomisk, valgfri trådoprettelse ved ny upsert og fjern `closed` fra merge-statusser.
- [ ] Kør testene grønne.

### Task 3: Test og implementér forfald samt loft

**Files:**
- Modify: `tests/test_thread_registry.py`
- Modify: `core/runtime/db_runtime_open_loop_threads.py`
- Modify: `core/runtime/db_runtime_executive_signals.py`
- Modify: `core/services/open_loop_signal_tracking.py`

- [ ] Skriv tests for tråd-bundet stale/udløb og synlig afvisning ved 128.
- [ ] Kør testene røde.
- [ ] Håndhæv loftet transaktionelt og tilføj særskilt registry-udløb uden closure-evidence.
- [ ] Kør testene grønne.

### Task 4: Verifikation og commit

**Files:**
- Verify: relevante tests, fuld pytest-suite, compileall, git diff

- [ ] Mål den levende DB read-only og dokumentér population/loft-effekt.
- [ ] Kør relevante tests, fuld suite og syntax-smoke.
- [ ] Commit via repository-wrapper med de seks krævede attribution-felter.
