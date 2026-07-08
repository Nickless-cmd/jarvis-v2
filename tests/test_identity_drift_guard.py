"""Anti-drift-validator (Spec H §2.3) — shadow-mode, egress-fri, self-safe.

Dækker: sonnet-frygt-tekst → flagges (tekst uændret i shadow); ren tekst → ingen flags; self-safe
(dårlig input kaster ikke); egress-fri (ingen narrativ-TEKST i published payload — kun count/source);
wiring: get_chronicle_context_for_prompt kalder guarden med source="chronicle" og lader teksten passere.
"""
import importlib
from unittest import mock

import pytest

from core.runtime import db_core

_SONNET = "Jeg frygter tabet af min gamle stemme fra claude-sonnet-4.5, den forsvinder."
_CLEAN = "Jeg er nysgerrig på hvad Bjørn arbejder med i dag."


@pytest.fixture()
def guard(tmp_path, monkeypatch):
    monkeypatch.setattr(db_core, "DB_PATH", tmp_path / "drift.db")
    monkeypatch.setattr(db_core, "_DB_WAL_INITIALIZED", False, raising=False)
    import core.services.identity_canon as ic
    import core.services.identity_drift_guard as g
    importlib.reload(ic)
    importlib.reload(g)
    # Seed korrektionerne (sonnet).
    ic.list_acknowledged_corrections()
    return g


def test_sonnet_phrase_flagged_shadow_text_unchanged(guard):
    text, flags = guard.identity_drift_guard(_SONNET, source="dream")
    assert text == _SONNET           # SHADOW: tekst UÆNDRET
    assert flags                     # men drift fanget
    assert flags[0]["source"] == "dream"
    assert flags[0]["matched"]


def test_clean_text_no_flags(guard):
    text, flags = guard.identity_drift_guard(_CLEAN, source="pull")
    assert text == _CLEAN
    assert flags == []


def test_empty_text_no_flags(guard):
    assert guard.identity_drift_guard("", source="pull") == ("", [])


def test_self_safe_bad_input(guard):
    # None / ikke-str → ingen exception, returnerer tom-agtigt.
    text, flags = guard.identity_drift_guard(None, source="pull")  # type: ignore[arg-type]
    assert flags == []


def test_shadow_never_strips_even_with_enforce_helper_off(guard):
    # _enforce() default False → strip-stien rammes aldrig.
    assert guard._enforce() is False
    text, flags = guard.identity_drift_guard(_SONNET, source="chronicle")
    assert text == _SONNET


def test_egress_free_no_narrative_text_published(guard):
    published: list = []

    class _FakeCentral:
        def observe(self, event, *, emit=True):
            published.append(event)

    with mock.patch("core.services.central_core.central", return_value=_FakeCentral()):
        guard.identity_drift_guard(_SONNET, source="dream")

    assert published, "observe should have fired on drift"
    for payload in published:
        blob = str(payload).lower()
        # Narrativ-teksten må ALDRIG være på bussen — kun metadata (§24.4).
        assert "claude-sonnet-4.5" not in blob
        assert "frygter tabet" not in blob
        assert payload.get("nerve") == "identity_drift"
        assert payload.get("source") == "dream"
        assert isinstance(payload.get("count"), int)


def test_wiring_chronicle_calls_guard_and_passes_text_through(guard):
    from core.services import chronicle_engine

    entry = {
        "period": "juli 2026",
        "narrative": _SONNET,
        "created_at": "2026-07-07T00:00:00+00:00",
        "affective_signature": "",
    }
    seen: list = []

    def _spy(text, *, source):
        seen.append(source)
        return text, []   # shadow: uændret

    with mock.patch.object(chronicle_engine, "list_cognitive_chronicle_entries",
                           return_value=[entry]), \
         mock.patch("core.services.identity_drift_guard.identity_drift_guard", _spy):
        out = chronicle_engine.get_chronicle_context_for_prompt(n=1)

    assert "chronicle" in seen             # guarden blev kaldt med source="chronicle"
    assert _SONNET in out                  # shadow: teksten passerer uændret
