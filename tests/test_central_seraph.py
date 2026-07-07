"""Seraph (Spec F §1) — portvagt for hypotese-modenhed.

Dækker: GREEN på en moden hypotese (nok jordede samples + overlevet Sentinel + interlanguage);
RED på en umoden (mangler et af kriterierne, med grunden i `missing`); self-safe (fejlende kilde
kaster ikke); egress-fri (intet hypotese-INDHOLD publiceres på eventbus — kun tællinger).
Injektion: patch hypotese-kilden + Sentinels list_attacks direkte (samme mock-stil som søsknene).
"""
from unittest import mock

from core.services import central_seraph as s


def _hyp(hid, *, grounded=5, sample_size=5, notation="pres ! x → y", confidence=0.6,
         statement="Events i 'tool' forudsiger events i 'cost'"):
    return {
        "hyp_id": hid,
        "statement": statement,
        "confidence": confidence,
        "grounded_samples": grounded,
        "sample_size": sample_size,
        "notation_il": notation,
        "created_at": "2026-07-07T00:00:00+00:00",
    }


def _wire(hyps, *, contested=()):
    """Patch hypotese-kilden + Sentinel-angreb + eventbus-observe."""
    return (
        mock.patch("core.services.central_seraph._active_hypotheses", return_value=list(hyps)),
        mock.patch("core.services.central_sentinel.list_attacks",
                   return_value=[{"hyp_id": h} for h in contested]),
        mock.patch("core.services.central_seraph._observe"),
    )


# ── GREEN på moden hypotese ───────────────────────────────────────────────────

def test_mature_hypothesis_is_green():
    p1, p2, p3 = _wire([_hyp("clh-1")])
    with p1, p2, p3:
        out = s.guard()
    assert out["status"] == "ok"
    assert out["green"] == 1
    assert out["red"] == 0
    assert out["green_ids"] == ["clh-1"]
    j = out["judged"][0]
    assert j["verdict"] == "GREEN"
    assert j["enough_samples"] and j["survived_sentinel"] and j["has_interlanguage"]
    assert j["missing"] == []


# ── RED: for få samples ───────────────────────────────────────────────────────

def test_too_few_samples_is_red():
    p1, p2, p3 = _wire([_hyp("clh-2", grounded=1, sample_size=5)])
    with p1, p2, p3:
        out = s.guard()
    assert out["green"] == 0 and out["red"] == 1
    j = out["judged"][0]
    assert j["verdict"] == "RED"
    assert "samples" in j["missing"]


# ── RED: uafklaret Sentinel-angreb (ikke overlevet) ───────────────────────────

def test_contested_by_sentinel_is_red():
    p1, p2, p3 = _wire([_hyp("clh-3")], contested=["clh-3"])
    with p1, p2, p3:
        out = s.guard()
    assert out["red"] == 1
    j = out["judged"][0]
    assert j["verdict"] == "RED"
    assert j["survived_sentinel"] is False
    assert "sentinel" in j["missing"]


# ── RED: mangler interlanguage-notation ───────────────────────────────────────

def test_missing_interlanguage_is_red():
    p1, p2, p3 = _wire([_hyp("clh-4", notation="")])
    with p1, p2, p3:
        out = s.guard()
    assert out["red"] == 1
    j = out["judged"][0]
    assert j["has_interlanguage"] is False
    assert "interlanguage" in j["missing"]


# ── deferral er UDSÆTTELSE, ikke blok (intet muteres) ─────────────────────────

def test_mixed_population_green_and_red():
    hyps = [_hyp("clh-a"), _hyp("clh-b", grounded=0), _hyp("clh-c", notation="")]
    p1, p2, p3 = _wire(hyps)
    with p1, p2, p3:
        out = s.guard()
    assert out["seen"] == 3
    assert out["green"] == 1
    assert out["red"] == 2
    assert out["green_ids"] == ["clh-a"]


# ── self-safe ─────────────────────────────────────────────────────────────────

def test_failing_data_source_does_not_raise():
    # The DB read and Sentinel read both blow up → their own try/except return []/set();
    # guard() must still complete and never raise.
    with mock.patch("core.runtime.db.connect", side_effect=RuntimeError("db down")), \
            mock.patch("core.services.central_sentinel.list_attacks", side_effect=RuntimeError("x")), \
            mock.patch("core.services.central_seraph._observe"):
        out = s.guard()
    assert out["status"] == "ok"
    assert out["seen"] == 0


# ── egress-fri (§24.4) — intet hypotese-INDHOLD publiceres ────────────────────

def test_observe_publishes_no_hypothesis_content():
    published: list = []

    class _FakeCentral:
        def observe(self, payload):
            published.append(payload)

    secret_stmt = "HEMMELIG hypotese om selvbilledet"
    hyps = [_hyp("clh-secret", statement=secret_stmt, notation="pres ! hemmeligt → y")]
    with mock.patch("core.services.central_seraph._active_hypotheses", return_value=hyps), \
            mock.patch("core.services.central_sentinel.list_attacks", return_value=[]), \
            mock.patch("core.services.central_core.central", return_value=_FakeCentral()):
        s.guard()

    assert published, "forventede en observe"
    blob = repr(published)
    assert secret_stmt not in blob
    assert "hemmeligt" not in blob
    assert "clh-secret" not in blob
    for p in published:
        assert set(p.keys()) <= {"cluster", "nerve", "kind", "seen", "green", "red"}


# ── surface ───────────────────────────────────────────────────────────────────

def test_surface_lists_ready_and_deferred():
    hyps = [_hyp("clh-ready"), _hyp("clh-defer", grounded=0)]
    with mock.patch("core.services.central_seraph._active_hypotheses", return_value=hyps), \
            mock.patch("core.services.central_sentinel.list_attacks", return_value=[]), \
            mock.patch("core.services.central_seraph._observe"):
        surf = s.build_seraph_surface()
    assert surf["active"] is True
    assert surf["green_count"] == 1
    assert surf["red_count"] == 1
    assert surf["ready_to_surface"][0]["hyp_id"] == "clh-ready"
    assert surf["deferred"][0]["hyp_id"] == "clh-defer"
    assert "samples" in surf["deferred"][0]["missing"]
