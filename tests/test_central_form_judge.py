"""Tests for core/services/central_form_judge.py — den centrale form-ændrings-dommer (§6.1c).

Kernen: kald kun modellen når prompten ændrer FORM, ikke ved volatile detaljer (tid/tal).
off/shadow/on, self-safe. Hermetisk — mode + observe monkeypatchet.
"""
from __future__ import annotations

import pytest

from core.services import central_form_judge as fj


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    fj._reset_for_tests()
    monkeypatch.setattr(fj, "_observe", lambda *a, **k: None)  # ingen central_timeseries i unit-test
    yield
    fj._reset_for_tests()


def _mode(monkeypatch, m):
    monkeypatch.setattr(fj, "_kv_get", lambda k, d: m)


def test_form_key_ignores_volatile_numbers_and_time():
    a = fj.form_key("Humør 0.42 kl 14:03 den 2026-07-03 — hvordan har du det?")
    b = fj.form_key("Humør 0.91 kl 09:57 den 2026-07-01 — hvordan har du det?")
    assert a == b  # kun tal/tid adskiller → samme FORM


def test_form_key_differs_on_real_content():
    assert fj.form_key("Skriv en refleksion om havet") != fj.form_key("Skriv en refleksion om skoven")


def test_off_never_reuses(monkeypatch):
    _mode(monkeypatch, "off")
    fj.note_result("dream", "Drøm om tal 5", "en drøm")
    assert fj.judge("dream", "Drøm om tal 9")["reuse"] is False


def test_shadow_measures_but_does_not_reuse(monkeypatch):
    _mode(monkeypatch, "shadow")
    fj.note_result("dream", "Drøm om tal 5", "en drøm")
    d = fj.judge("dream", "Drøm om tal 9")   # samme form (kun tal ændret)
    assert d["reuse"] is False and d["would_reuse"] is True


def test_on_reuses_when_form_unchanged(monkeypatch):
    _mode(monkeypatch, "on")
    fj.note_result("dream", "Drøm om tal 5", "en holdt drøm")
    d = fj.judge("dream", "Drøm om tal 42")  # kun tallet ændret → uændret form
    assert d["reuse"] is True and d["held"] == "en holdt drøm"


def test_on_calls_when_form_changed(monkeypatch):
    _mode(monkeypatch, "on")
    fj.note_result("dream", "Drøm om havet", "holdt")
    assert fj.judge("dream", "Drøm om skoven")["reuse"] is False  # ny form → kald


def test_note_result_is_bounded(monkeypatch):
    for i in range(fj._MAX_KEYS_PER_NS + 8):
        fj.note_result("d", f"unik besked nummer {chr(65+i)} xx", f"svar {i}")
    assert len(fj._held["d"]) <= fj._MAX_KEYS_PER_NS


def test_self_safe_on_kv_failure(monkeypatch):
    monkeypatch.setattr(fj, "_kv_get", lambda k, d: (_ for _ in ()).throw(RuntimeError("boom")))
    assert fj.judge("x", "y")["reuse"] is False   # fejl → kald som før
