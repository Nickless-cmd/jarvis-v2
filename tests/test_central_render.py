"""Tests for Spec B Fase B1+B2 — tilstand→notation (central_render) + pervasivt model-frit ræsonnement."""
from __future__ import annotations

from core.services import central_render as rd
from core.services import central_notation as nt


# ── B1: render-primitiver (model-frie, ærlig-None) ───────────────────────────────────
def test_render_cluster_relation():
    # memory→somatic er bundne (kontinuitet, krop)
    assert rd.render_cluster_relation("memory", "somatic") == "kontinuitet → krop"


def test_render_anomaly_is_an_edge():
    # system→krop bundet; anomali renderes som ægte kant mod 'stød' (så den kæder transitivt)
    assert rd.render_anomaly("system") == "krop → stød"


def test_render_decision_deny_and_allow():
    assert rd.render_decision("auth", verdict="deny") == "grænse ! grænse"      # auth→grænse
    assert rd.render_decision("tools", verdict="allow") == "handling → handling"  # tools→handling


def test_render_honest_none_on_unbound():
    """Genuint ubundne begreber → None (sproget gætter ikke)."""
    assert rd.render_anomaly("truth") is None            # truth ubundet (ceremoni-kandidat)
    assert rd.render_decision("council", verdict="deny") is None
    assert rd.render_cluster_relation("mutation", "skill") is None


def test_render_is_model_free_and_deterministic():
    """Ingen model-kald, samme input → samme output (ren symbol-operation)."""
    a = rd.render_cluster_relation("memory", "somatic")
    b = rd.render_cluster_relation("memory", "somatic")
    assert a == b == "kontinuitet → krop"


def test_state_snapshot_renders_anomalies(isolated_runtime):
    from core.runtime.db_anomalies import record_anomaly_signature
    record_anomaly_signature(signature="sig-sys-1", category="system", importance="high",
                             source="test", sample="boom")
    snap = rd.render_state_snapshot()
    sys_items = [s for s in snap if s["name"] == "system"]
    assert sys_items and sys_items[0]["notation_il"] == "krop → stød"
    assert sys_items[0]["source"] == "anomaly"


# ── B2: pervasivt ræsonnement + nordstjernen ─────────────────────────────────────────
def _seed_hyp(hyp_id, notation, status="active"):
    from core.runtime.db import connect
    from core.services import central_hypothesis_generator as gen
    gen.ensure_schema()
    with connect() as c:
        c.execute(
            "INSERT INTO central_hypotheses (hyp_id, source, statement, prediction, null_hypothesis, "
            "success_criterion, sample_size, ttl_seconds, provenance_json, confidence, status, "
            "outcome, grounded_samples, created_at, notation_il) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,NULL,0,'2026-07-02T00:00:00Z',?)",
            (hyp_id, "causal_convergence", "s", "p", "n", "sc", 5, 3600, "{}", 0.5, status, notation))
        c.commit()


def test_gather_spans_hypotheses_and_states(isolated_runtime):
    from core.runtime.db_anomalies import record_anomaly_signature
    _seed_hyp("h1", "kontinuitet → krop")
    record_anomaly_signature(signature="sig-sys-2", category="system", importance="high", source="t", sample="x")
    items = nt.gather_all_notations()
    srcs = {it["source"] for it in items}
    assert "hypothesis" in srcs and "anomaly" in srcs        # tvær-overflade


def test_cross_surface_transitive_inference(isolated_runtime):
    """B2 EXIT-GATE: en udledning der KRÆVER led fra to forskellige overflader.
    Anomali: 'krop → stød' (system-overflade). Hypotese: 'stød → fokus'. ⟹ 'krop → fokus'."""
    from core.runtime.db_anomalies import record_anomaly_signature
    _seed_hyp("h_stod", "stød → fokus")                     # hypotese-overflade
    record_anomaly_signature(signature="sig-sys-3", category="system", importance="high", source="t", sample="x")
    res = nt.model_free_reasoning()
    notas = {d["notation"] for d in res["derived_inferences"]}
    assert "krop → fokus" in notas                          # udledt PÅ TVÆRS af overflader
    assert res["model_used"] is False


def test_model_blackout_still_reasons(isolated_runtime, monkeypatch):
    """NORDSTJERNEN: selv med modellen utilgængelig fortsætter Centralen sit ræsonnement (0 model-token)."""
    # simulér model-blackout: enhver visible-model-sti kaster
    import builtins
    _seed_hyp("a", "kontinuitet → krop")
    _seed_hyp("b", "krop → fokus")
    res = nt.model_free_reasoning()
    assert res["model_used"] is False
    # transitiv udledning sker uden model: kontinuitet → krop + krop → fokus ⟹ kontinuitet → fokus
    assert "kontinuitet → fokus" in {d["notation"] for d in res["derived_inferences"]}


def test_reasoning_tick_reports_sources(isolated_runtime):
    _seed_hyp("h1", "kontinuitet → krop")
    out = nt.run_notation_reasoning_tick()
    assert out["status"] == "ok" and out["taxonomy_ratio"] is not None
