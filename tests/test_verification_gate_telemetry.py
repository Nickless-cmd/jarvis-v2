"""Unit tests for verification_gate_telemetry — the R2 heed-rate tracker.

Tests the public API of ``core/services/verification_gate_telemetry.py``
using an in-memory fake for ``load_json``/``save_json``.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from core.services import telemetry_gate as tg
from core.services import verification_gate_telemetry as vgt
from core.services.verification_gate_telemetry import (
    get_telemetry_summary,
    record_surface,
    record_verify_event,
    sweep_expired_surfaces,
    telemetry_section,
)

# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _fake_state_store(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Replace load_json / save_json with an in-memory dict.

    Returns the dict so tests can inspect or pre-seed it.
    """
    store: dict[str, Any] = {}

    def fake_load(name: str, default: Any) -> Any:
        return store.get(name, default)

    def fake_save(name: str, data: Any) -> None:
        store[name] = data

    monkeypatch.setattr(
        "core.services.verification_gate_telemetry.load_json", fake_load
    )
    monkeypatch.setattr(
        "core.services.verification_gate_telemetry.save_json", fake_save
    )
    # Udfaldsaksen cacher sit DB-opslag i 5 min. Uden denne reset ville én
    # tests tal lække ind i den næste.
    vgt._reset_outcome_cache()
    # En unit-test skal ikke ramme produktionens database. Standard er derfor
    # «ingen events» — de tests der måler udfaldsaksen patcher `connect` selv
    # via `_patch_events`.
    import core.runtime.db as _db

    monkeypatch.setattr(
        _db, "connect", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no db"))
    )
    return store


def _surface(overrides: dict | None = None) -> dict:
    """Helper: build a surface record with sensible defaults."""
    base = {
        "at": datetime.now(UTC).isoformat(),
        "kind": "unverified",
        "failed_verify_count": 0,
        "unverified_count": 3,
        "mutation_count": 5,
        "verify_count": 0,
        "resolved": False,
    }
    if overrides:
        base.update(overrides)
    return base


# ── record_surface ──────────────────────────────────────────────────────────


class TestRecordSurface:
    def test_skips_when_no_issues(self, _fake_state_store):
        """No failed_verify AND no unverified → nothing persisted."""
        record_surface(
            failed_verify_count=0,
            unverified_count=0,
            mutation_count=5,
            verify_count=0,
        )
        data = _fake_state_store.get("r2_verification_gate_telemetry", {})
        assert len(data.get("surfaces", [])) == 0

    def test_persists_failed_verify(self, _fake_state_store):
        """failed_verify > 0 → record with kind='failed_verify'."""
        record_surface(
            failed_verify_count=2,
            unverified_count=0,
            mutation_count=5,
            verify_count=3,
        )
        data = _fake_state_store["r2_verification_gate_telemetry"]
        surfaces = data["surfaces"]
        assert len(surfaces) == 1
        assert surfaces[0]["kind"] == "failed_verify"
        assert surfaces[0]["failed_verify_count"] == 2
        assert surfaces[0]["resolved"] is False

    def test_persists_unverified(self, _fake_state_store):
        """failed_verify=0, unverified>0 → kind='unverified'."""
        record_surface(
            failed_verify_count=0,
            unverified_count=3,
            mutation_count=5,
            verify_count=0,
        )
        data = _fake_state_store["r2_verification_gate_telemetry"]
        assert len(data["surfaces"]) == 1
        assert data["surfaces"][0]["kind"] == "unverified"

    def test_deduplicates_within_30s(self, _fake_state_store):
        """Two calls within 30s of each other → only one record."""
        record_surface(
            failed_verify_count=1,
            unverified_count=0,
            mutation_count=5,
            verify_count=0,
        )
        record_surface(
            failed_verify_count=2,
            unverified_count=0,
            mutation_count=5,
            verify_count=0,
        )
        data = _fake_state_store["r2_verification_gate_telemetry"]
        assert len(data["surfaces"]) == 1

    def test_allows_after_30s(self, _fake_state_store):
        """Two calls >30s apart → both recorded.

        Strategy: pre-seed store with a 31s-old surface, then call
        record_surface — it should NOT deduplicate because the last
        surface is older than 30s.
        """
        old_at = (datetime.now(UTC) - timedelta(seconds=31)).isoformat()
        _fake_state_store["r2_verification_gate_telemetry"] = {
            "surfaces": [_surface({"at": old_at})],
            "reactions": [],
        }
        record_surface(
            failed_verify_count=1,
            unverified_count=0,
            mutation_count=5,
            verify_count=0,
        )
        data = _fake_state_store["r2_verification_gate_telemetry"]
        assert len(data["surfaces"]) == 2
        data = _fake_state_store["r2_verification_gate_telemetry"]
        assert len(data["surfaces"]) == 2


# ── record_verify_event ─────────────────────────────────────────────────────


class TestRecordVerifyEvent:
    def test_skips_non_ok_status(self, _fake_state_store):
        """Status != 'ok' → no surface is resolved."""
        # Pre-seed an unresolved surface
        _fake_state_store["r2_verification_gate_telemetry"] = {
            "surfaces": [_surface()],
            "reactions": [],
        }
        record_verify_event(tool="verify_file_contains", status="failed")
        data = _fake_state_store["r2_verification_gate_telemetry"]
        assert data["surfaces"][0]["resolved"] is False

    def test_heeds_most_recent_surface(self, _fake_state_store):
        """OK verify → most recent unresolved surface resolved."""
        old = _surface({"at": (datetime.now(UTC) - timedelta(seconds=50)).isoformat()})
        recent = _surface({"at": (datetime.now(UTC) - timedelta(seconds=10)).isoformat()})
        _fake_state_store["r2_verification_gate_telemetry"] = {
            "surfaces": [old, recent],
            "reactions": [],
        }
        record_verify_event(tool="verify_file_contains", status="ok")
        data = _fake_state_store["r2_verification_gate_telemetry"]
        # Only the most recent should be resolved
        assert data["surfaces"][0]["resolved"] is False  # old — untouched
        assert data["surfaces"][1]["resolved"] is True  # recent — heeded
        assert data["surfaces"][1]["heeded_by"] == "verify_file_contains"
        # Reaction recorded
        assert len(data["reactions"]) == 1
        assert data["reactions"][0]["verdict"] == "heeded"

    def test_ignores_outside_window(self, _fake_state_store):
        """Surface older than 60s → not heeded."""
        old = _surface({"at": (datetime.now(UTC) - timedelta(seconds=90)).isoformat()})
        _fake_state_store["r2_verification_gate_telemetry"] = {
            "surfaces": [old],
            "reactions": [],
        }
        record_verify_event(tool="verify_file_contains", status="ok")
        data = _fake_state_store["r2_verification_gate_telemetry"]
        assert data["surfaces"][0]["resolved"] is False

    def test_does_not_re_resolve_heeded_surface(self, _fake_state_store):
        """Already-resolved surface is skipped."""
        heeded = _surface({"resolved": True, "heeded_by": "verify_file_contains"})
        _fake_state_store["r2_verification_gate_telemetry"] = {
            "surfaces": [heeded],
            "reactions": [{"verdict": "heeded"}],
        }
        record_verify_event(tool="verify_file_contains", status="ok")
        data = _fake_state_store["r2_verification_gate_telemetry"]
        assert len(data["reactions"]) == 1  # no new reaction


# ── sweep_expired_surfaces ─────────────────────────────────────────────────


class TestSweepExpiredSurfaces:
    def test_marks_expired_as_ignored(self, _fake_state_store):
        """Surfaces past 60s window → resolved + ignored_at."""
        old = _surface({"at": (datetime.now(UTC) - timedelta(seconds=90)).isoformat()})
        _fake_state_store["r2_verification_gate_telemetry"] = {
            "surfaces": [old],
            "reactions": [],
        }
        count = sweep_expired_surfaces()
        assert count == 1
        data = _fake_state_store["r2_verification_gate_telemetry"]
        assert data["surfaces"][0]["resolved"] is True
        assert "ignored_at" in data["surfaces"][0]
        assert len(data["reactions"]) == 1
        assert data["reactions"][0]["verdict"] == "ignored"

    def test_skips_recent_surfaces(self, _fake_state_store):
        """Surface within 60s → untouched."""
        fresh = _surface({"at": datetime.now(UTC).isoformat()})
        _fake_state_store["r2_verification_gate_telemetry"] = {
            "surfaces": [fresh],
            "reactions": [],
        }
        count = sweep_expired_surfaces()
        assert count == 0
        data = _fake_state_store["r2_verification_gate_telemetry"]
        assert data["surfaces"][0]["resolved"] is False

    def test_skips_already_resolved(self, _fake_state_store):
        """Already-resolved surface → not double-counted."""
        resolved = _surface({
            "at": (datetime.now(UTC) - timedelta(seconds=90)).isoformat(),
            "resolved": True,
        })
        _fake_state_store["r2_verification_gate_telemetry"] = {
            "surfaces": [resolved],
            "reactions": [],
        }
        count = sweep_expired_surfaces()
        assert count == 0


# ── get_telemetry_summary ──────────────────────────────────────────────────


class TestGetTelemetrySummary:
    def test_empty_when_no_data(self):
        """No surfaces → zero counts, no heed_rate."""
        s = get_telemetry_summary(hours=24)
        assert s["surfaced_total"] == 0
        assert s["heeded_total"] == 0
        assert s["ignored_total"] == 0
        assert s["heed_rate"] is None

    def test_counts_heeded_and_ignored(self, _fake_state_store):
        """Mix of heeded, ignored, unresolved → correct counts."""
        now = datetime.now(UTC)
        _fake_state_store["r2_verification_gate_telemetry"] = {
            "surfaces": [
                # Heeded (within window)
                _surface({
                    "at": (now - timedelta(hours=1)).isoformat(),
                    "resolved": True,
                    "heeded_by": "verify_file_contains",
                }),
                # Ignored (within window)
                _surface({
                    "at": (now - timedelta(hours=2)).isoformat(),
                    "resolved": True,
                    "ignored_at": now.isoformat(),
                }),
                # Unresolved — still in reaction window (<60s), should be
                # counted as surfaced but not heeded or ignored yet
                _surface({
                    "at": (now - timedelta(seconds=30)).isoformat(),
                    "resolved": False,
                }),
            ],
            "reactions": [],
        }
        s = get_telemetry_summary(hours=24)
        assert s["surfaced_total"] == 3
        assert s["heeded_total"] == 1
        assert s["ignored_total"] == 1
        assert s["heed_rate"] == pytest.approx(1 / 3, rel=0.01)

    def test_filters_by_window(self, _fake_state_store):
        """Surfaces outside the lookback window → excluded."""
        now = datetime.now(UTC)
        _fake_state_store["r2_verification_gate_telemetry"] = {
            "surfaces": [
                _surface({
                    "at": (now - timedelta(hours=2)).isoformat(),
                    "resolved": True,
                    "heeded_by": "verify",
                }),
                _surface({
                    "at": (now - timedelta(hours=50)).isoformat(),
                    "resolved": True,
                    "ignored_at": now.isoformat(),
                }),
            ],
            "reactions": [],
        }
        s = get_telemetry_summary(hours=24)
        assert s["surfaced_total"] == 1  # only the 2h-old one

    def test_by_kind_present(self, _fake_state_store):
        """by_kind breakdown is populated."""
        now = datetime.now(UTC)
        _fake_state_store["r2_verification_gate_telemetry"] = {
            "surfaces": [
                _surface({
                    "at": now.isoformat(),
                    "kind": "failed_verify",
                    "resolved": True,
                    "heeded_by": "verify",
                }),
                _surface({
                    "at": (now - timedelta(minutes=30)).isoformat(),
                    "kind": "unverified",
                    "resolved": False,
                }),
            ],
            "reactions": [],
        }
        s = get_telemetry_summary(hours=24)
        assert "failed_verify" in s["by_kind"]
        assert "unverified" in s["by_kind"]
        assert s["by_kind"]["failed_verify"]["surfaced"] == 1
        assert s["by_kind"]["failed_verify"]["heeded"] == 1

    def test_heed_rate_none_when_no_surfaces_in_window(self):
        """No surfaces in window → heed_rate is None."""
        s = get_telemetry_summary(hours=999)
        assert s["heed_rate"] is None


# ── telemetry_section ───────────────────────────────────────────────────────


class TestTelemetrySection:
    def test_none_when_few_surfaces(self, _fake_state_store):
        """<5 surfaces in 24h → None."""
        now = datetime.now(UTC)
        surfaces = [
            _surface({"at": (now - timedelta(hours=i)).isoformat()})
            for i in range(4)
        ]
        _fake_state_store["r2_verification_gate_telemetry"] = {
            "surfaces": surfaces,
            "reactions": [],
        }
        assert telemetry_section() is None

    def test_returns_formatted_with_5_surfaces(self, _fake_state_store):
        """≥5 surfaces → formatted string."""
        now = datetime.now(UTC)
        surfaces = [
            _surface({
                "at": (now - timedelta(hours=i)).isoformat(),
                "resolved": True,
                "heeded_by": "verify_file_contains" if i % 2 == 0 else None,
                "ignored_at": now.isoformat() if i % 2 == 1 else None,
            })
            for i in range(5)
        ]
        _fake_state_store["r2_verification_gate_telemetry"] = {
            "surfaces": surfaces,
            "reactions": [],
        }
        section = telemetry_section()
        assert section is not None
        assert "R2-gate" in section
        assert "surfaced=" in section
        assert "heeded=" in section

    def test_flags_low_heed_rate(self, _fake_state_store):
        """heed_rate < 0.4 → warning flag appended."""
        now = datetime.now(UTC)
        # 5 surfaces, 1 heeded, 4 ignored → 20% rate
        surfaces = [
            _surface({
                "at": (now - timedelta(hours=i)).isoformat(),
                "resolved": True,
                "heeded_by": "verify_file_contains" if i == 0 else None,
                "ignored_at": now.isoformat() if i > 0 else None,
            })
            for i in range(5)
        ]
        _fake_state_store["r2_verification_gate_telemetry"] = {
            "surfaces": surfaces,
            "reactions": [],
        }
        section = telemetry_section()
        assert section is not None
        assert "⚠" in section or "under 40%" in section

    def test_no_flag_when_heed_rate_ok(self, _fake_state_store):
        """heed_rate ≥ 0.4 → no warning flag."""
        now = datetime.now(UTC)
        # 5 surfaces, 3 heeded, 0 ignored, 2 unresolved
        surfaces = [
            _surface({
                "at": (now - timedelta(hours=i)).isoformat(),
                "resolved": True,
                "heeded_by": "verify_file_contains",
            })
            for i in range(3)
        ]
        surfaces += [
            _surface({
                "at": (now - timedelta(hours=i + 3)).isoformat(),
                "resolved": False,
            })
            for i in range(2)
        ]
        _fake_state_store["r2_verification_gate_telemetry"] = {
            "surfaces": surfaces,
            "reactions": [],
        }
        section = telemetry_section()
        assert section is not None
        assert "⚠" not in section


# ── _save: alders-beskæring + ærligt tab (20/9-2026) ────────────────────────


class TestSaveAldersBeskaering:
    """Loftet var et *antal* (500), ikke en *tid*.

    Målt 20/9-2026 stod begge ringe præcis på 500/500, hvilket dækkede 9,7 døgn
    ved ~52 poster/døgn. Ved 500/døgn ville «7d» reelt være 1 døgn — og tallet
    ville se lige så rigtigt ud. Disse tests holder horisonten fast som *tid*,
    og tabet som *talt*.
    """

    @staticmethod
    def _s(dage: float, **extra) -> dict:
        return {
            "at": (datetime.now(UTC) - timedelta(days=dage)).isoformat(),
            "kind": "unverified",
            "resolved": False,
            **extra,
        }

    def test_gamle_poster_ryger_nye_bliver(self, _fake_state_store):
        tg.nulstil_tab()
        vgt._save({"surfaces": [self._s(40), self._s(20), self._s(1)],
                   "reactions": []})
        gemt = _fake_state_store[vgt._TELEMETRY_KEY]
        assert len(gemt["surfaces"]) == 2  # 40 dage ude; 20 og 1 inde

    def test_alderstab_taelles(self, _fake_state_store):
        """Kriterium 2: usynligt tab er ikke i orden. Alders-tabet skal tælles."""
        tg.nulstil_tab()
        vgt._save({"surfaces": [self._s(40), self._s(50), self._s(1)],
                   "reactions": []})
        assert tg.tabt("verification_gate_telemetry.surfaces") == 2

    def test_30d_horisont_er_maalbar(self, _fake_state_store):
        """Kernen i fixet: en post 20 dage gammel overlever, så «30d» er et
        ægte tal og ikke et loft der hed 500."""
        tg.nulstil_tab()
        vgt._save({"surfaces": [self._s(20), self._s(8), self._s(2)],
                   "reactions": []})
        gemt = _fake_state_store[vgt._TELEMETRY_KEY]
        assert len(gemt["surfaces"]) == 3
        assert vgt._RETENTION_DAYS == 30

    def test_uden_tidsstempel_beholdes(self, _fake_state_store):
        """Alder ukendt → behold. Et gæt ville kaste rigtige poster væk."""
        tg.nulstil_tab()
        vgt._save({"surfaces": [{"kind": "x"}, self._s(1)], "reactions": []})
        gemt = _fake_state_store[vgt._TELEMETRY_KEY]
        assert len(gemt["surfaces"]) == 2

    def test_loftet_holder_selv_om_taelleren_braekker(
        self, _fake_state_store, monkeypatch
    ):
        """Regnskabet må aldrig koste os selve beskæringen — en ring uden loft
        ville vokse til den spiste state-filen."""
        monkeypatch.setattr(
            tg, "beskaer_efter_alder",
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("nede")),
        )
        vgt._save({"surfaces": list(range(vgt._MAX_RECORDS + 500)),
                   "reactions": []})
        gemt = _fake_state_store[vgt._TELEMETRY_KEY]
        assert len(gemt["surfaces"]) == vgt._MAX_RECORDS, "loftet forsvandt med tælleren"

    def test_naiv_tidsstempel_kaster_ikke(self, _fake_state_store):
        """Et naivt tidsstempel (uden tz) må ikke vælte sammenligningen."""
        tg.nulstil_tab()
        naiv = (datetime.now(UTC).replace(tzinfo=None)).isoformat()
        vgt._save({"surfaces": [{"at": naiv, "kind": "unverified"}],
                   "reactions": []})
        gemt = _fake_state_store[vgt._TELEMETRY_KEY]
        assert len(gemt["surfaces"]) == 1


# ── measure_outcome_axis ────────────────────────────────────────────────────
#
# Den gamle akse (`get_telemetry_summary`) måler om der kom et verify-kald
# inden for 60 sekunder. Målt 17/11-2026 faldt 97,5 % af den ægte verifikation
# uden for det vindue, så «ignored» betød «svarede ikke hurtigt nok» — ikke
# «verificerede ikke». Disse tests låser den nye akses kontrakt fast.


class _FakeConn:
    """Minimal DB-stand-in: returnerer de rækker testen giver den."""

    def __init__(self, rows: list[tuple]) -> None:
        self._rows = rows
        self.queries: list[tuple] = []

    def execute(self, sql: str, params: tuple = ()) -> "_FakeConn":
        self.queries.append((sql, params))
        return self

    def fetchall(self) -> list[tuple]:
        return self._rows

    def __enter__(self) -> "_FakeConn":
        return self

    def __exit__(self, *a: object) -> bool:
        return False


def _patch_events(monkeypatch: pytest.MonkeyPatch, rows: list[tuple]) -> _FakeConn:
    """Patch `core.runtime.db.connect` — funktionen importerer den ved kald."""
    import core.runtime.db as _db

    conn = _FakeConn(rows)
    monkeypatch.setattr(_db, "connect", lambda *a, **k: conn)
    return conn


def _verify_row(tool: str, when: datetime, status: str = "ok") -> tuple:
    import json as _json

    return (
        _json.dumps({"tool": tool, "status": status, "run_id": "r1"}),
        when.isoformat(),
    )


class TestMeasureOutcomeAxis:
    def test_no_surfaces_returns_empty(self):
        """Ingen advarsler → ingen rate, ingen DB-forespørgsel."""
        r = vgt.measure_outcome_axis(hours=24)
        assert r["surfaces"] == 0
        assert r["rate"] is None
        assert r["cross_tab"] == {}

    def test_verify_after_old_window_still_counts(
        self, _fake_state_store, monkeypatch
    ):
        """Kernefejlen: verify 30 min efter advarslen er ude af 60s-vinduet,
        men er stadig en ægte verifikation."""
        now = datetime.now(UTC)
        _fake_state_store[vgt._TELEMETRY_KEY] = {
            "surfaces": [
                _surface({
                    "at": (now - timedelta(minutes=40)).isoformat(),
                    "resolved": True,
                    "ignored_at": (now - timedelta(minutes=39)).isoformat(),
                })
            ],
            "reactions": [],
        }
        _patch_events(
            monkeypatch,
            [_verify_row("verify_file_contains", now - timedelta(minutes=10))],
        )
        r = vgt.measure_outcome_axis(hours=24)
        assert r["surfaces"] == 1
        assert r["verified"] == 1
        assert r["rate"] == 1.0
        # 30 min efter advarslen → med i 30/60/240, ikke i 1/5/10
        assert r["per_horizon"][1] == 0
        assert r["per_horizon"][5] == 0
        assert r["per_horizon"][10] == 0
        assert r["per_horizon"][30] == 1
        assert r["per_horizon"][240] == 1

    def test_ignored_but_verified_lands_in_cross_tab(
        self, _fake_state_store, monkeypatch
    ):
        """Den ægte fejlform: gammel akse sagde «ignored», ny akse ser
        verifikationen. Uenigheden SKAL være synlig i cross_tab."""
        now = datetime.now(UTC)
        _fake_state_store[vgt._TELEMETRY_KEY] = {
            "surfaces": [
                _surface({
                    "at": (now - timedelta(minutes=90)).isoformat(),
                    "resolved": True,
                    "ignored_at": (now - timedelta(minutes=89)).isoformat(),
                })
            ],
            "reactions": [],
        }
        _patch_events(
            monkeypatch,
            [_verify_row("verify_file_contains", now - timedelta(minutes=20))],
        )
        r = vgt.measure_outcome_axis(hours=24)
        assert r["cross_tab"]["ignored_but_verified"] == 1
        assert r["cross_tab"]["ignored_and_unverified"] == 0

    def test_genuint_uverificeret_taelles_som_uverificeret(
        self, _fake_state_store, monkeypatch
    ):
        """Modstykket: uden verify-kald er advarslen reelt uverificeret."""
        now = datetime.now(UTC)
        _fake_state_store[vgt._TELEMETRY_KEY] = {
            "surfaces": [
                _surface({
                    "at": (now - timedelta(minutes=90)).isoformat(),
                    "resolved": True,
                    "ignored_at": (now - timedelta(minutes=89)).isoformat(),
                })
            ],
            "reactions": [],
        }
        _patch_events(monkeypatch, [])
        r = vgt.measure_outcome_axis(hours=24)
        assert r["verified"] == 0
        assert r["cross_tab"]["ignored_and_unverified"] == 1

    def test_light_tool_taelles_ikke_som_verifikation(
        self, _fake_state_store, monkeypatch
    ):
        """En læsning er ikke en kontrol. `read_file` står i _LIGHT_VERIFY_TOOLS
        og må ikke gøre en advarsel «verificeret» på udfaldsaksen."""
        now = datetime.now(UTC)
        _fake_state_store[vgt._TELEMETRY_KEY] = {
            "surfaces": [
                _surface({"at": (now - timedelta(minutes=40)).isoformat(),
                          "resolved": True,
                          "ignored_at": (now - timedelta(minutes=39)).isoformat()})
            ],
            "reactions": [],
        }
        _patch_events(monkeypatch, [_verify_row("read_file", now)])
        r = vgt.measure_outcome_axis(hours=24)
        assert r["verified"] == 0
        assert r["rate"] == 0.0

    def test_verify_foer_advarslen_taelles_ikke(
        self, _fake_state_store, monkeypatch
    ):
        """Tidslig orden: et verify-kald der kom FØR advarslen kan ikke være
        en reaktion på den."""
        now = datetime.now(UTC)
        _fake_state_store[vgt._TELEMETRY_KEY] = {
            "surfaces": [
                _surface({"at": (now - timedelta(minutes=40)).isoformat(),
                          "resolved": True,
                          "ignored_at": (now - timedelta(minutes=39)).isoformat()})
            ],
            "reactions": [],
        }
        _patch_events(
            monkeypatch,
            [_verify_row("verify_file_contains", now - timedelta(minutes=60))],
        )
        r = vgt.measure_outcome_axis(hours=24)
        assert r["verified"] == 0

    def test_feajlet_verify_taelles_ikke(self, _fake_state_store, monkeypatch):
        """Et verify-kald der selv fejlede beviser ingenting."""
        now = datetime.now(UTC)
        _fake_state_store[vgt._TELEMETRY_KEY] = {
            "surfaces": [
                _surface({"at": (now - timedelta(minutes=40)).isoformat(),
                          "resolved": True,
                          "ignored_at": (now - timedelta(minutes=39)).isoformat()})
            ],
            "reactions": [],
        }
        _patch_events(
            monkeypatch,
            [_verify_row("verify_file_contains", now, status="failed")],
        )
        r = vgt.measure_outcome_axis(hours=24)
        assert r["verified"] == 0

    def test_median_seconds_to_verify(self, _fake_state_store, monkeypatch):
        """Median reaktionstid måles på dem der BLEV verificeret."""
        now = datetime.now(UTC)
        _fake_state_store[vgt._TELEMETRY_KEY] = {
            "surfaces": [
                _surface({"at": (now - timedelta(minutes=50)).isoformat()}),
                _surface({"at": (now - timedelta(minutes=30)).isoformat()}),
            ],
            "reactions": [],
        }
        _patch_events(
            monkeypatch,
            [
                _verify_row("verify_file_contains", now - timedelta(minutes=40)),
                _verify_row("verify_file_contains", now - timedelta(minutes=10)),
            ],
        )
        r = vgt.measure_outcome_axis(hours=24)
        # 10 min og 20 min → median 15 min = 900 s
        assert r["median_seconds_to_verify"] == pytest.approx(900.0, rel=0.02)


class TestSectionViserAegteDaekning:
    """Koblingen: uden disse to er `measure_outcome_axis` en funktion ingen
    kalder — præcis den teater-form den skal afløse."""

    def test_sektionen_viser_aegte_daekning(self, _fake_state_store, monkeypatch):
        now = datetime.now(UTC)
        _fake_state_store[vgt._TELEMETRY_KEY] = {
            "surfaces": [
                _surface({
                    "at": (now - timedelta(hours=2, minutes=i)).isoformat(),
                    "resolved": True,
                    "ignored_at": now.isoformat(),
                })
                for i in range(5)
            ],
            "reactions": [],
        }
        _patch_events(
            monkeypatch,
            [_verify_row("verify_file_contains", now - timedelta(minutes=30))],
        )
        section = telemetry_section()
        assert section is not None
        assert "ægte dækning" in section
        assert "1/5" in section

    def test_uden_db_viser_kun_den_gamle_akse(self, _fake_state_store):
        """DB-fejl må ikke tage prompten med sig — sektionen skal stadig
        rendere, bare uden den ægte akse."""
        now = datetime.now(UTC)
        _fake_state_store[vgt._TELEMETRY_KEY] = {
            "surfaces": [
                _surface({"at": (now - timedelta(hours=i)).isoformat()})
                for i in range(5)
            ],
            "reactions": [],
        }
        section = telemetry_section()
        assert section is not None
        assert "R2-gate" in section
        assert "ægte dækning" not in section
