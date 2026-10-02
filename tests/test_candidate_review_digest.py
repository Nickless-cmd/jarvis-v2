"""Test af den ugentlige kandidat-review-digest (1/10-2026).

Digesten er push-vejen Bjørn manglede: kandidaterne ventede på et menneske,
men intet signalerede det. Testene dækker de tre ting der kan gå stille galt —
at tallene er forkerte, at den tier for sent, og at en fejlet besked vælter
daemonen.
"""
from datetime import UTC, datetime, timedelta

import core.services.candidate_review_digest as crd


class _FakeConn:
    """Minimal stand-in for sqlite-connect: execute() → self, fetchall() → rows."""

    def __init__(self, rows):
        self._rows = rows

    def execute(self, sql, params=None):  # noqa: ARG002 — SQL ignoreres med vilje
        return self

    def fetchall(self):
        return self._rows

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _patch_rows(monkeypatch, rows):
    import core.runtime.db as db
    monkeypatch.setattr(db, "connect", lambda: _FakeConn(rows))


def _patch_last_tick(monkeypatch, value):
    """Bind throttle-tilstanden — den bor nu på disk, ikke i en modul-global."""
    monkeypatch.setattr(crd, "_load_last_tick", lambda: value)
    monkeypatch.setattr(crd, "_save_last_tick", lambda now: None)


def test_digest_taeller_per_type_og_finder_aeldste(monkeypatch):
    now = datetime.now(UTC)
    _patch_rows(monkeypatch, [
        ("memory_promotion", 1541, (now - timedelta(days=58)).isoformat()),
        ("preference_update", 545, (now - timedelta(days=10)).isoformat()),
    ])
    d = crd.build_candidate_review_digest()
    assert d["total_proposed"] == 2086
    assert d["by_type"]["memory_promotion"] == 1541
    assert d["oldest_days"] == 58
    assert d["oldest_type"] == "memory_promotion"


def test_tom_koe_giver_ingen_tekst(monkeypatch):
    _patch_rows(monkeypatch, [])
    d = crd.build_candidate_review_digest()
    assert d["total_proposed"] == 0
    assert crd.format_candidate_review_digest(d) == ""


def test_tekst_naevner_tal_og_alder(monkeypatch):
    now = datetime.now(UTC)
    _patch_rows(monkeypatch, [
        ("memory_promotion", 100, (now - timedelta(days=40)).isoformat()),
    ])
    t = crd.format_candidate_review_digest(crd.build_candidate_review_digest())
    assert "100" in t
    assert "40" in t


def test_ugyldigt_tidsstempel_springes_over_men_tallet_beholdes(monkeypatch):
    _patch_rows(monkeypatch, [("memory_promotion", 42, "ikke-en-dato")])
    d = crd.build_candidate_review_digest()
    assert d["total_proposed"] == 42
    assert d["oldest_days"] is None


def test_tick_tier_under_taerskel(monkeypatch):
    _patch_last_tick(monkeypatch, None)
    _patch_rows(monkeypatch, [("memory_promotion", 3, datetime.now(UTC).isoformat())])
    r = crd.tick_candidate_review_digest()
    assert r["sent"] is False
    assert r["reason"] == "below-threshold"


def test_tick_throttler_indtil_ugen_er_gået(monkeypatch):
    _patch_last_tick(monkeypatch, datetime.now(UTC))
    r = crd.tick_candidate_review_digest()
    assert r["sent"] is False
    assert r["reason"] == "cadence"


def test_tick_sender_over_taerskel(monkeypatch):
    _patch_last_tick(monkeypatch, None)
    now = datetime.now(UTC)
    _patch_rows(monkeypatch, [
        ("memory_promotion", 500, (now - timedelta(days=20)).isoformat()),
    ])
    sendt = {}
    import core.services.notification_bridge as nb
    monkeypatch.setattr(
        nb, "send_session_notification",
        lambda text, **kw: (sendt.update(text=text), {"status": "ok"})[1],
    )
    r = crd.tick_candidate_review_digest()
    assert r["sent"] is True
    assert "500" in sendt["text"]


def test_fejlet_notifikation_vaelter_ikke_daemonen(monkeypatch):
    _patch_last_tick(monkeypatch, None)
    _patch_rows(monkeypatch, [("memory_promotion", 500, datetime.now(UTC).isoformat())])
    import core.services.notification_bridge as nb

    def _boom(*a, **k):
        raise RuntimeError("notifikation nede")

    monkeypatch.setattr(nb, "send_session_notification", _boom)
    r = crd.tick_candidate_review_digest()
    assert r["sent"] is False


def test_database_fejl_giver_tom_digest_ikke_kast(monkeypatch):
    import core.runtime.db as db

    def _boom():
        raise RuntimeError("ingen DB")

    monkeypatch.setattr(db, "connect", _boom)
    d = crd.build_candidate_review_digest()
    assert d["total_proposed"] == 0
    assert "error" in d


def test_throttlen_overlever_en_genstart(monkeypatch, tmp_path):
    """Regression (2/10-2026): kadencen laa i en modul-global og blev nulstillet
    ved HVER runtime-genstart — saa «ugentligt» blev «ved hver genstart», og
    koen blev annonceret igen og igen. Den skal laeses fra disk, ikke fra RAM.
    """
    import core.runtime.state_store as ss

    monkeypatch.setattr(ss, "_STATE_DIR", tmp_path)
    _patch_rows(monkeypatch, [("memory_promotion", 500, datetime.now(UTC).isoformat())])
    sendt = []
    import core.services.notification_bridge as nb
    monkeypatch.setattr(
        nb, "send_session_notification",
        lambda text, **kw: (sendt.append(text), {"status": "ok"})[1],
    )

    foerste = crd.tick_candidate_review_digest()
    assert foerste["sent"] is True

    # Simulér genstart: RAM er tom, men disken staar. Uden persistens ville
    # andet kald sende igen; med den skal det ties ihjel af kadencen.
    andet = crd.tick_candidate_review_digest()
    assert andet["sent"] is False
    assert andet["reason"] == "cadence"
    assert len(sendt) == 1
