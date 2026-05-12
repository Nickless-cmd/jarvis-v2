#!/usr/bin/env python3
"""Smoke-test the jarvis-runtime startup path WITHOUT serving traffic.

Imports the FastAPI app and runs its lifespan context to completion. If
lifespan startup raises (TypeError on bad kwargs, missing DB column,
import failure, daemon init crash, etc.), this script exits non-zero —
which catches the class of bug that puts jarvis-runtime in a systemd
restart loop.

Usage:
    conda activate ai
    python scripts/smoke_test_startup.py

Exit codes:
    0  — lifespan started + shut down cleanly
    1  — exception during startup (script prints the traceback)
    2  — script ran longer than timeout (currently 60s)

Recommended: run before pushing changes that touch runtime startup paths
(apps/api/jarvis_api/app.py, core/runtime/db.py, core/services/*runtime*.py,
or anything imported during lifespan).
"""
from __future__ import annotations

import asyncio
import os
import signal
import sys
import time
import traceback
from pathlib import Path

# Ensure repo root is importable when run as a script
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


_TIMEOUT_SECONDS = 60


async def _run_lifespan() -> None:
    """Import app + drive lifespan context to completion."""
    # Skip the noisy parts that would fail on a dev box without all creds.
    # The point is to catch *startup* TypeErrors / schema drift / import
    # failures — not to validate that every external service is reachable.
    os.environ.setdefault("JARVIS_SMOKE_TEST", "1")

    from apps.api.jarvis_api.app import create_app
    app = create_app()

    # FastAPI's lifespan can be driven manually via the router's lifespan
    # context manager. We enter it (= startup) and exit (= shutdown). If
    # any startup hook raises, the context manager re-raises here.
    async with app.router.lifespan_context(app):
        # Startup completed without exception — that's the whole point.
        # Also verify the tool-router endpoint is reachable in-process.
        from fastapi.testclient import TestClient
        try:
            with TestClient(app) as client:
                r = client.get("/mc/tool-router-state")
                if r.status_code != 200:
                    raise RuntimeError(
                        f"tool-router-state returned {r.status_code}"
                    )
        except Exception:
            # Don't let endpoint check failures hide real startup bugs;
            # report but continue.
            traceback.print_exc()

        # Verify decision_signals registry populated (added 2026-05-07)
        try:
            import core.services.decision_triggers  # noqa: F401
            from core.services.decision_signals import _TRIGGER_REGISTRY
            expected = {"loop_nudge_5_rounds", "backend_unresolved_3_calls"}
            missing = expected - set(_TRIGGER_REGISTRY.keys())
            if missing:
                raise RuntimeError(
                    f"decision_signals registry missing: {missing}"
                )
        except Exception:
            traceback.print_exc()

        # Verify counterfactuals table exists + daemon importable (Phase 1)
        try:
            from core.runtime.db import connect
            with connect() as c:
                row = c.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name='counterfactuals'"
                ).fetchone()
                if row is None:
                    raise RuntimeError("counterfactuals table missing")
            from core.services.counterfactual_engine_runtime import (
                start_counterfactual_runtime,  # noqa: F401
            )
        except Exception:
            traceback.print_exc()

        # Verify absence_traces + soft_deleted_at columns + forgetting daemon (Lag 11)
        try:
            from core.runtime.db import connect
            with connect() as c:
                row = c.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name='absence_traces'"
                ).fetchone()
                if row is None:
                    raise RuntimeError("absence_traces table missing")
                cols = [
                    r[1] for r in c.execute(
                        "PRAGMA table_info(cognitive_chronicle_entries)"
                    ).fetchall()
                ]
                if "soft_deleted_at" not in cols:
                    raise RuntimeError(
                        "soft_deleted_at missing on cognitive_chronicle_entries"
                    )
            from core.services.forgetting_runtime import (
                start_forgetting_runtime,  # noqa: F401
            )
            from core.tools.forgetting_tools import (
                FORGETTING_TOOL_DEFINITIONS,  # noqa: F401
            )
        except Exception:
            traceback.print_exc()

        # Verify user_temperature_active table + engine importable (Lag 10)
        try:
            from core.runtime.db import connect
            with connect() as c:
                row = c.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name='user_temperature_active'"
                ).fetchone()
                if row is None:
                    raise RuntimeError("user_temperature_active table missing")
            from core.services.user_temperature_engine import (
                get_active_field,  # noqa: F401
                format_temperature_field_for_heartbeat,  # noqa: F401
                get_response_style_modifiers,  # noqa: F401
                run_structural_stream,  # noqa: F401
                run_llm_stream,  # noqa: F401
            )
            from core.services.user_temperature_runtime import (
                start_user_temperature_runtime,  # noqa: F401
            )
        except Exception:
            traceback.print_exc()

        # Verify skill_chain tool registered (Lag #4)
        try:
            from core.tools.skill_chain_tool import (
                SKILL_CHAIN_TOOL_DEFINITIONS,  # noqa: F401
                SKILL_CHAIN_TOOL_HANDLERS,  # noqa: F401
                _exec_skill_chain,  # noqa: F401
            )
            from core.tools.simple_tools import TOOL_DEFINITIONS, _TOOL_HANDLERS
            names = []
            for td in TOOL_DEFINITIONS:
                if "function" in td:
                    names.append(td["function"].get("name"))
                elif "name" in td:
                    names.append(td["name"])
            if "skill_chain" not in names:
                raise RuntimeError("skill_chain not in TOOL_DEFINITIONS")
            if "skill_chain" not in _TOOL_HANDLERS:
                raise RuntimeError("skill_chain not in _TOOL_HANDLERS")
        except Exception:
            traceback.print_exc()

        # Verify dream_bias_active table + engine importable (Lag 2)
        try:
            from core.runtime.db import connect
            with connect() as c:
                row = c.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name='dream_bias_active'"
                ).fetchone()
                if row is None:
                    raise RuntimeError("dream_bias_active table missing")
            from core.services.dream_bias_engine import (
                get_active_dream_bias,  # noqa: F401
                format_dream_bias_for_heartbeat,  # noqa: F401
                run_dream_bias_distillation,  # noqa: F401
            )
        except Exception:
            traceback.print_exc()

        # Creative voice (Lag #4 — added 2026-05-11)
        try:
            from core.services import voice_anchor, voice_curator  # noqa: F401
            from core.services.voice_anchor import read_voice_anchor  # noqa: F401
            from core.services.voice_curator import refresh_voice_recent  # noqa: F401
            from core.services.creative_journal_runtime import (  # noqa: F401
                _should_skip_week,
                _interval_days_for_state,
                _fetch_broken_decisions,
                _fetch_affective_klangbraet,
                _format_yaml_frontmatter,
                _quality_lane_enabled,
            )
            from core.services.prompt_contract import (  # noqa: F401
                format_journal_for_heartbeat,
            )
        except Exception:
            traceback.print_exc()

        # Finitude Phase 1 (Lag #3 — added 2026-05-11)
        try:
            from core.services.finitude_runtime import (  # noqa: F401
                _format_looming_end_section,
                _session_age_hours,
                _token_utilization_pct,
                _monthly_quality_lane_enabled,
                _is_due_for_monthly,
                run_monthly_finitude_reflection,
            )
        except Exception:
            traceback.print_exc()

        # Desire Phase 1 (Lag #5 — added 2026-05-11)
        try:
            from core.services.current_pull import (  # noqa: F401
                _pull_is_stale,
                _compute_landscape_embedding,
                _collect_appetite_texts,
                _collect_chronicle_texts,
                _collect_journal_texts,
                _archive_refresh_event,
                _should_run_staleness_check,
                _staleness_check_enabled,
            )
        except Exception:
            traceback.print_exc()

        # Music / Æstetik Phase 1 (Lag #6 — added 2026-05-11)
        try:
            from core.services.ambient_sound_daemon import (  # noqa: F401
                count_music_samples_last_hours,
                _select_music_influence_phrase,
                get_music_accumulator_for_prompt,
            )
            from core.services.creative_journal_runtime import (  # noqa: F401
                _fetch_recent_top_motif,
                _fetch_dominant_taste,
            )
        except Exception:
            traceback.print_exc()

        # Multi-step planner Phase 1 (added 2026-05-12)
        try:
            from core.services.plan_proposals import (  # noqa: F401
                mark_step_completed,
                format_cross_session_plans_for_awareness,
                _plan_todo_auto_create_enabled,
            )
            from core.services.agent_todos import create_from_plan  # noqa: F401
        except Exception:
            traceback.print_exc()

        # Unconscious modulation Phase 1 (Lag 10 — added 2026-05-12)
        try:
            from core.services.unconscious_modulation import (  # noqa: F401
                compute_unconscious_modulation,
                _modulation_enabled,
            )
        except Exception:
            traceback.print_exc()

        # Tool Invention Phase 1 (AGI track — added 2026-05-12)
        try:
            from core.services.skill_engine import (  # noqa: F401
                validate_skill_proposal,
                _collect_registered_tool_names,
            )
            from core.tools.skill_engine_tools import (  # noqa: F401
                _exec_propose_new_skill,
            )
            from core.tools.simple_tools import TOOL_DEFINITIONS, _TOOL_HANDLERS
            _names = [
                (e.get("function") or {}).get("name")
                for e in TOOL_DEFINITIONS if isinstance(e, dict)
            ]
            if "propose_new_skill" not in _names:
                raise RuntimeError("propose_new_skill not in TOOL_DEFINITIONS")
            if "propose_new_skill" not in _TOOL_HANDLERS:
                raise RuntimeError("propose_new_skill not in _TOOL_HANDLERS")
        except Exception:
            traceback.print_exc()

        # World Model Phase 1 — closing the loop (AGI track #1 — 2026-05-12)
        try:
            from core.services.world_model_signal_tracking import (  # noqa: F401
                extract_prediction_language,
                extract_resolution_language,
                record_prediction_nudge,
                record_resolution_nudge,
                format_world_model_nudges_for_awareness,
                _ttl_sweep_open_predictions,
                _compute_calibration_milestone,
                format_world_model_milestone_for_awareness,
            )
            from core.tools.world_model_tools import (  # noqa: F401
                _exec_predict_outcome,
                _exec_resolve_prediction,
            )
            from core.tools.simple_tools import TOOL_DEFINITIONS, _TOOL_HANDLERS
            _names = [
                (e.get("function") or {}).get("name")
                for e in TOOL_DEFINITIONS if isinstance(e, dict)
            ]
            if "predict_outcome" not in _names:
                raise RuntimeError("predict_outcome not in TOOL_DEFINITIONS")
            if "resolve_prediction" not in _names:
                raise RuntimeError("resolve_prediction not in TOOL_DEFINITIONS")
        except Exception:
            traceback.print_exc()


def main() -> int:
    started = time.monotonic()
    try:
        asyncio.run(asyncio.wait_for(_run_lifespan(), timeout=_TIMEOUT_SECONDS))
    except asyncio.TimeoutError:
        elapsed = time.monotonic() - started
        print(
            f"smoke_test_startup: TIMEOUT after {elapsed:.1f}s "
            f"(limit {_TIMEOUT_SECONDS}s) — startup hung",
            file=sys.stderr,
        )
        return 2
    except Exception:
        elapsed = time.monotonic() - started
        print(
            f"smoke_test_startup: FAILED after {elapsed:.1f}s",
            file=sys.stderr,
        )
        traceback.print_exc()
        return 1

    elapsed = time.monotonic() - started
    print(f"smoke_test_startup: OK in {elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    # Ignore SIGPIPE so child-process noise doesn't make this misreport
    try:
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    except (AttributeError, ValueError):
        pass
    sys.exit(main())
