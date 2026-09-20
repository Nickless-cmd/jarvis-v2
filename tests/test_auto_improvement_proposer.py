"""Paritet for auto_improvement_proposer._is_safe_target efter Mutation-cluster-routing.

_is_safe_target rutes nu gennem gate_mutation (Centralen); samme bool-svar bevaret.
INFRASTRUCTURE_BLOCKED_MODULES er nu re-eksporteret fra den kanoniske kilde (single-source).
"""
from __future__ import annotations

from core.services import auto_improvement_proposer as aip


def test_is_safe_target_allows_identity_and_tools():
    # identitets-filer rutes via identity_mutation_log → sikre at foreslå her
    assert aip._is_safe_target("update SOUL.md") is True
    assert aip._is_safe_target("modify IDENTITY.md") is True
    assert aip._is_safe_target("change tool description") is True
    assert aip._is_safe_target("core.services.context_window_manager:baz") is True


def test_is_safe_target_blocks_infrastructure():
    assert aip._is_safe_target("core.services.auto_improvement_proposer:foo") is False
    assert aip._is_safe_target("core.services.plan_proposals:bar") is False
    assert aip._is_safe_target("core.services.identity_mutation_log:x") is False
    assert aip._is_safe_target("core.services.approvals:y") is False
    assert aip._is_safe_target("core.runtime.policy:z") is False


def test_is_safe_target_empty_false():
    assert aip._is_safe_target("") is False


def test_infrastructure_list_is_canonical_single_source():
    from core.services import gate_mutation as gm
    assert aip._INFRASTRUCTURE_BLOCKED_MODULES is gm.INFRASTRUCTURE_BLOCKED_MODULES


# ── Regression 2026-08-30: kronisk-provider-plan må ikke fyre på stale data ──
# Problemet: ved genstart læser proposeren et gammelt snapshot (fra natten) og
# genopretter provider-planen selvom provideren er kommet op igen.


def test_provider_health_chronic_skips_stale_snapshot(monkeypatch):
    from datetime import UTC, datetime, timedelta
    from core.services import auto_improvement_proposer as aip

    def stale_snap():
        return {
            "checked_at": (datetime.now(UTC) - timedelta(hours=12)).isoformat(),
            "unreachable": ["groq"],
        }

    monkeypatch.setattr(
        "core.services.provider_health_check.latest_health_snapshot", stale_snap
    )
    assert aip._check_provider_health_chronic() is None


def test_provider_health_chronic_fires_on_fresh_snapshot(monkeypatch):
    from datetime import UTC, datetime
    from core.services import auto_improvement_proposer as aip

    def fresh_snap():
        return {
            "checked_at": datetime.now(UTC).isoformat(),
            "unreachable": ["groq"],
        }

    monkeypatch.setattr(
        "core.services.provider_health_check.latest_health_snapshot", fresh_snap
    )
    res = aip._check_provider_health_chronic()
    assert res is not None
    assert "kronisk ikke-tilgængelig" in res["title"]


def test_provider_health_chronic_noop_when_all_up(monkeypatch):
    from datetime import UTC, datetime
    from core.services import auto_improvement_proposer as aip

    def fresh_snap():
        return {
            "checked_at": datetime.now(UTC).isoformat(),
            "unreachable": [],
        }

    monkeypatch.setattr(
        "core.services.provider_health_check.latest_health_snapshot", fresh_snap
    )
    assert aip._check_provider_health_chronic() is None


# ── Regression 2026-09-13: auto-planernes titel må ikke indeholde volatile tal ──
# Problemet: dedup'en i plan_proposals matcher på EKSAKT titel. Når titlen bar et
# tal (score, antal), slap en dismissed plan igennem som "ny" i det øjeblik tallet
# ændrede sig — og genopstod ved hver genstart. Titel er en STABIL identitet;
# tallet hører i `why`. Målt: `Heartbeat tick-kvalitet er degraderende (85.0/100)`
# blev dismissed, men ville blive genforeslået som `(83.2/100)`.


def test_tick_quality_titel_stabil_paa_tvaers_af_score(monkeypatch):
    """To forskellige scores skal give SAMME titel — ellers genopstår planen."""
    from core.services import agent_self_evaluation as ase
    from core.services import auto_improvement_proposer as aip

    def with_score(score):
        monkeypatch.setattr(
            ase,
            "tick_quality_summary",
            lambda days=7: {"trend": "degrading", "count": 10, "avg_score": score},
        )
        return aip._check_tick_quality_degraded()

    a, b = with_score(85.0), with_score(83.2)
    assert a is not None and b is not None
    assert a["title"] == b["title"]
    assert "85.0" not in a["title"] and "83.2" not in b["title"]
    assert "85.0" in a["why"]  # tallet er bevaret — bare ikke i identiteten


def test_stale_goals_titel_stabil_paa_tvaers_af_antal(monkeypatch):
    from core.services import agent_self_evaluation as ase
    from core.services import auto_improvement_proposer as aip

    def with_count(n):
        monkeypatch.setattr(
            ase,
            "detect_stale_goals",
            lambda: [{"title": f"mål {i}", "goal_id": f"g{i}"} for i in range(n)],
        )
        return aip._check_stale_goals()

    a, b = with_count(2), with_count(5)
    assert a is not None and b is not None
    assert a["title"] == b["title"]
    assert "2" in a["why"]  # antallet er bevaret i why


def test_decision_adherence_titel_stabil_paa_tvaers_af_score(monkeypatch):
    from core.services import agent_self_evaluation as ase
    from core.services import auto_improvement_proposer as aip

    def with_score(score):
        monkeypatch.setattr(
            ase,
            "decision_adherence_summary",
            lambda: {
                "flag": True,
                "score": score,
                "adhered": 3,
                "total": 10,
                "revoked": 7,
            },
        )
        return aip._check_decision_adherence()

    a, b = with_score(55), with_score(48)
    assert a is not None and b is not None
    assert a["title"] == b["title"]
    assert "55" in a["why"]


def test_provider_titel_stabil_paa_tvaers_af_antal(monkeypatch):
    from datetime import UTC, datetime

    import core.services.provider_health_check as phc
    from core.services import auto_improvement_proposer as aip

    def with_n(n):
        monkeypatch.setattr(
            phc,
            "latest_health_snapshot",
            lambda: {
                "checked_at": datetime.now(UTC).isoformat(),
                "unreachable": [f"p{i}" for i in range(n)],
            },
        )
        return aip._check_provider_health_chronic()

    a, b = with_n(1), with_n(2)
    assert a is not None and b is not None
    assert a["title"] == b["title"]


# ── Regression 2026-09-20: ingen demotion-plan for en ALREADY-disabled provider ──
# Problemet: health-checken pinger hvert endpoint i _PING_ENDPOINTS uanset
# enabled-status. En provider der har været `enabled: false` i uger (sambanova,
# 21/6) lander derfor i `unreachable`, og proposeren filede en demotion-plan
# hvis trin 1 var en no-op. Målt: plan-1472fb6460 (19/9), dismissed 20/9.


def _fresh_snap_with(monkeypatch, providers):
    from datetime import UTC, datetime

    import core.services.provider_health_check as phc

    monkeypatch.setattr(
        phc,
        "latest_health_snapshot",
        lambda: {
            "checked_at": datetime.now(UTC).isoformat(),
            "unreachable": list(providers),
        },
    )


def test_provider_health_chronic_skips_already_disabled(monkeypatch):
    from core.services import auto_improvement_proposer as aip

    _fresh_snap_with(monkeypatch, ["sambanova"])
    monkeypatch.setattr(aip, "_already_disabled_providers", lambda: {"sambanova"})
    assert aip._check_provider_health_chronic() is None


def test_provider_health_chronic_keeps_enabled_provider(monkeypatch):
    from core.services import auto_improvement_proposer as aip

    _fresh_snap_with(monkeypatch, ["groq", "sambanova"])
    monkeypatch.setattr(aip, "_already_disabled_providers", lambda: {"sambanova"})
    res = aip._check_provider_health_chronic()
    assert res is not None
    assert "groq" in res["why"]
    # den fra-slåede provider må ikke nævnes i indgrebet
    assert "sambanova" not in res["why"]
    assert "sambanova" not in res["steps"][0]


def test_provider_health_chronic_keeps_unknown_provider(monkeypatch):
    """Ukendte navne (slet ikke i registret) filtreres ikke — vi kan ikke
    hævde de er slået fra, så et reelt signal må gerne fyre."""
    from core.services import auto_improvement_proposer as aip

    _fresh_snap_with(monkeypatch, ["p0"])
    monkeypatch.setattr(aip, "_already_disabled_providers", lambda: set())
    res = aip._check_provider_health_chronic()
    assert res is not None
    assert "p0" in res["why"]


def test_already_disabled_providers_reads_registry(monkeypatch):
    import core.runtime.provider_router as pr
    from core.services import auto_improvement_proposer as aip

    monkeypatch.setattr(
        pr,
        "load_provider_router_registry",
        lambda: {
            "providers": [
                {"provider": "groq", "enabled": True},
                {"provider": "sambanova", "enabled": False},
                {"provider": "opencode", "enabled": False},
                {"provider": "cerebras", "enabled": True},
                "ikke-en-dict",
                {"provider": "", "enabled": False},
            ],
            "models": [],
        },
    )
    assert aip._already_disabled_providers() == {"sambanova", "opencode"}


def test_already_disabled_providers_empty_on_failure(monkeypatch):
    """Kan registret ikke læses, filtrerer vi intet — hellere en plan for
    meget end et reelt signal vi ikke ser."""
    import core.runtime.provider_router as pr
    from core.services import auto_improvement_proposer as aip

    def boom():
        raise RuntimeError("registry unavailable")

    monkeypatch.setattr(pr, "load_provider_router_registry", boom)
    assert aip._already_disabled_providers() == set()
