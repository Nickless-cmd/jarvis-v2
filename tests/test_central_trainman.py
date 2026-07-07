"""Trainman (Spec F §4) — drømme vævet til narrative erindringer i private_brain.

Dækker: en drøm væves (source='dream' + theme + narrative); idempotens (samme dream_id ikke re-vævet);
3+ samme-tema på 7 dage → Agenda-signal; self-safe (fejlende kilde/skrivning kaster ikke); egress-fri
(intet drømme-INDHOLD publiceres på eventbus). Fixture: in-memory fake private_brain + stubbede kilder.
"""
from datetime import UTC, datetime, timedelta
from unittest import mock

import pytest

from core.services import central_trainman as t


class _FakeBrain:
    """In-memory stand-in for private_brain: insert er idempotent på record_id (INSERT OR IGNORE)."""

    def __init__(self):
        self.rows: list[dict] = []

    def insert(self, **kw):
        rid = kw.get("record_id")
        if any(r.get("record_id") == rid for r in self.rows):
            return {}
        row = dict(kw)
        row.setdefault("created_at", datetime.now(UTC).isoformat())
        self.rows.append(row)
        return row

    def list_records(self, *, limit=20, **_):
        return list(reversed(self.rows))[:limit]


@pytest.fixture
def brain():
    return _FakeBrain()


@pytest.fixture
def wired(brain):
    """Patch dream-source + private_brain write/list + agenda + eventbus at their import sources."""
    pushes: list[dict] = []

    def _push(*, focus, source="inner-voice", source_id="", priority="medium"):
        pushes.append({"focus": focus, "source": source, "source_id": source_id, "priority": priority})
        return "init-abc"

    with mock.patch("core.runtime.db.insert_private_brain_record", side_effect=brain.insert), \
            mock.patch("core.runtime.db.list_private_brain_records", side_effect=brain.list_records), \
            mock.patch("core.services.initiative_queue.push_initiative", side_effect=_push), \
            mock.patch("core.services.central_trainman._observe"):
        yield {"brain": brain, "pushes": pushes}


def _dream(did, theme, *, at=None):
    return {
        "consolidation_id": did,
        "at": (at or datetime.now(UTC).isoformat()),
        "theme_count": 1,
        "themes": [{"theme": theme, "sample_text": f"sample {theme}"}],
    }


def _patch_dreams(dreams):
    return mock.patch(
        "core.services.dream_consolidation_daemon.list_recent_dreams",
        return_value=dreams,
    )


# ── væve en drøm ──────────────────────────────────────────────────────────────

def test_dream_woven_into_private_brain(wired):
    with _patch_dreams([_dream("D124", "persistence_optimization")]):
        out = t.transform_dreams(trigger="test")
    assert out["status"] == "ok"
    assert out["woven"] == 1
    woven = [r for r in wired["brain"].rows if r["domain"] not in ("dream_reflection", "dream_silence")]
    assert len(woven) == 1
    r = woven[0]
    assert r["record_type"] == "dream"
    assert r["domain"] == "persistence_optimization"
    assert "persistence_optimization" in r["detail"]  # narrative bærer temaet
    sig = __import__("json").loads(r["source_signals"])
    assert sig["source"] == "dream"
    assert sig["dream_id"] == "D124"
    assert sig["interlanguage"]  # interlanguage-notation vævet med
    assert sig["theme"] == "persistence_optimization"


# ── idempotens ────────────────────────────────────────────────────────────────

def test_same_dream_id_not_reweaved(wired):
    d = _dream("D200", "speed")
    with _patch_dreams([d]):
        t.transform_dreams(trigger="test")
    with _patch_dreams([d]):
        out2 = t.transform_dreams(trigger="test")
    assert out2["woven"] == 0
    assert out2["skipped_existing"] == 1
    woven = [r for r in wired["brain"].rows if r["domain"] == "speed"]
    assert len(woven) == 1  # ingen dublet af selve drømmen


# ── tilbagevendende tema → Agenda-signal ─────────────────────────────────────

def test_three_same_theme_within_7d_signals_agenda(wired):
    now = datetime.now(UTC)
    dreams = [
        _dream("D1", "security_hardening", at=(now - timedelta(days=2)).isoformat()),
        _dream("D2", "security_hardening", at=(now - timedelta(days=1)).isoformat()),
        _dream("D3", "security_hardening", at=now.isoformat()),
    ]
    with _patch_dreams(dreams):
        out = t.transform_dreams(trigger="test")
    assert out["woven"] == 3
    assert out["agenda_signals"] >= 1
    assert wired["pushes"], "forventede et Agenda-push"
    p = wired["pushes"][-1]
    assert p["source"] == "dream"
    assert p["priority"] == "low"  # lav-prio, blokerer aldrig
    assert "security_hardening" in p["focus"]


def test_two_same_theme_does_not_signal(wired):
    now = datetime.now(UTC)
    dreams = [
        _dream("D1", "curiosity", at=(now - timedelta(days=1)).isoformat()),
        _dream("D2", "curiosity", at=now.isoformat()),
    ]
    with _patch_dreams(dreams):
        out = t.transform_dreams(trigger="test")
    assert out["agenda_signals"] == 0
    assert wired["pushes"] == []


# ── self-safe ─────────────────────────────────────────────────────────────────

def test_failing_dream_source_does_not_raise():
    with mock.patch(
        "core.services.dream_consolidation_daemon.list_recent_dreams",
        side_effect=RuntimeError("boom"),
    ), mock.patch("core.services.central_trainman._observe"):
        out = t.transform_dreams(trigger="test")
    assert out["status"] == "ok"
    assert out["woven"] == 0


def test_failing_write_does_not_raise(brain):
    with _patch_dreams([_dream("D9", "persistence")]), \
            mock.patch("core.runtime.db.list_private_brain_records", side_effect=brain.list_records), \
            mock.patch("core.runtime.db.insert_private_brain_record",
                       side_effect=RuntimeError("db down")), \
            mock.patch("core.services.central_trainman._observe"):
        out = t.transform_dreams(trigger="test")
    assert out["status"] == "ok"
    assert out["woven"] == 0  # skrivning fejlede men intet kastede


# ── egress-fri (§24.4) — intet drømme-INDHOLD publiceres ─────────────────────

def test_observe_publishes_no_dream_content(brain):
    published: list = []

    class _FakeCentral:
        def observe(self, payload):
            published.append(payload)

    with _patch_dreams([_dream("D_secret", "hemmeligt_tema")]), \
            mock.patch("core.runtime.db.insert_private_brain_record", side_effect=brain.insert), \
            mock.patch("core.runtime.db.list_private_brain_records", side_effect=brain.list_records), \
            mock.patch("core.services.central_core.central", return_value=_FakeCentral()):
        t.transform_dreams(trigger="test")

    assert published, "forventede en observe"
    blob = repr(published)
    # metadata-only: ingen narrativ-tekst, tema-navn eller dream_id på eventbus
    assert "hemmeligt_tema" not in blob
    assert "D_secret" not in blob
    assert "I nat drømte" not in blob
    for p in published:
        assert set(p.keys()) <= {
            "cluster", "nerve", "kind", "dreams_seen", "woven",
            "agenda_signals", "reflection_written", "silence_notes",
        }


# ── surface ───────────────────────────────────────────────────────────────────

def test_surface_lists_woven_and_distribution(wired):
    with _patch_dreams([_dream("D1", "persistence"), _dream("D2", "persistence"),
                        _dream("D3", "speed")]):
        t.transform_dreams(trigger="test")
    surf = t.build_trainman_surface()
    assert surf["active"] is True
    assert surf["woven_total"] == 3
    themes = {d["theme"]: d["count"] for d in surf["theme_distribution"]}
    assert themes.get("persistence") == 2
    assert themes.get("speed") == 1
