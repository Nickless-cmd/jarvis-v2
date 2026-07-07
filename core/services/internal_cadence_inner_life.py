"""Inner-life cadence producers (split from internal_cadence.py).

Behavior-preserving extraction (Boy Scout rule): registered in unchanged
order by ``internal_cadence._ensure_producers_registered``.

This group: the inner-life / dream / self-critique daemons and the
curiosity + meta-learning cadences (sleep_consolidation, witness_daemon,
inner_voice_daemon, emergent_signal_daemon, dream_articulation,
prompt_evolution_runtime, self_critique_runtime, ontological_revision,
dream_distillation_daemon, creative_journal_runtime, finitude_runtime,
finitude_monthly_reflection, world_model_ttl_sweeper, curiosity_idle_window,
meta_learning_weekly_retrospective, curiosity_consolidation_weekly).
"""
from __future__ import annotations

import logging
from typing import Callable

from core.services.internal_cadence import ProducerSpec

logger = logging.getLogger(__name__)


def register_inner_life_producers(register_producer: Callable[[ProducerSpec], None]) -> None:
    """Register the inner-life producers (unchanged order/timing)."""

    def _run_sleep_consolidation(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.idle_consolidation import (
            run_idle_consolidation,
        )
        return run_idle_consolidation(trigger=trigger, last_visible_at=last_visible_at)

    register_producer(ProducerSpec(
        name="sleep_consolidation",
        cooldown_minutes=15,
        visible_grace_minutes=5,
        run_fn=_run_sleep_consolidation,
        priority=3,
        depends_on=["brain_continuity"],
    ))

    # Witness daemon
    def _run_witness(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.witness_signal_tracking import (
            run_witness_daemon,
        )
        return run_witness_daemon(trigger=trigger, last_visible_at=last_visible_at)

    register_producer(ProducerSpec(
        name="witness_daemon",
        cooldown_minutes=5,
        visible_grace_minutes=1,
        run_fn=_run_witness,
        priority=5,
        depends_on=["brain_continuity"],
    ))

    # Inner voice daemon
    def _run_inner_voice(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.inner_voice_daemon import (
            run_inner_voice_daemon,
        )
        from core.services.witness_signal_tracking import (
            get_witness_daemon_state,
        )
        witness_state = get_witness_daemon_state()
        return run_inner_voice_daemon(
            trigger=trigger,
            last_visible_at=last_visible_at,
            witness_daemon_last_run_at=str(witness_state.get("last_run_at") or ""),
        )

    register_producer(ProducerSpec(
        name="inner_voice_daemon",
        cooldown_minutes=5,
        visible_grace_minutes=2,
        run_fn=_run_inner_voice,
        priority=10,
        depends_on=["witness_daemon"],
    ))

    # Emergent inner signal daemon
    def _run_emergent_signals(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.emergent_signal_tracking import (
            run_emergent_signal_daemon,
        )

        return run_emergent_signal_daemon(
            trigger=trigger,
            last_visible_at=last_visible_at,
        )

    register_producer(ProducerSpec(
        name="emergent_signal_daemon",
        cooldown_minutes=5,
        visible_grace_minutes=2,
        run_fn=_run_emergent_signals,
        priority=12,
        depends_on=["witness_daemon"],
    ))

    def _run_dream_articulation(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.dream_articulation import (
            run_dream_articulation,
        )
        return run_dream_articulation(trigger=trigger, last_visible_at=last_visible_at)

    register_producer(ProducerSpec(
        name="dream_articulation",
        cooldown_minutes=20,
        visible_grace_minutes=5,
        run_fn=_run_dream_articulation,
        priority=15,
        depends_on=["sleep_consolidation"],
    ))

    def _run_prompt_evolution_runtime(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.prompt_evolution_runtime import (
            run_prompt_evolution_runtime,
        )
        return run_prompt_evolution_runtime(trigger=trigger, last_visible_at=last_visible_at)

    register_producer(ProducerSpec(
        name="prompt_evolution_runtime",
        cooldown_minutes=25,
        visible_grace_minutes=8,
        run_fn=_run_prompt_evolution_runtime,
        priority=18,
        depends_on=["dream_articulation"],
    ))

    def _run_self_critique_runtime(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.self_critique_runtime import (
            run_self_critique_cycle,
        )

        return run_self_critique_cycle(trigger=trigger, last_visible_at=last_visible_at)

    register_producer(ProducerSpec(
        name="self_critique_runtime",
        cooldown_minutes=1440,
        visible_grace_minutes=15,
        run_fn=_run_self_critique_runtime,
        priority=20,
        depends_on=["prompt_evolution_runtime"],
    ))

    def _run_ontological_revision(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.self_critique_runtime import run_ontological_revision_check
        return run_ontological_revision_check()

    register_producer(ProducerSpec(
        name="ontological_revision",
        cooldown_minutes=1440,  # Check once/day — actual cadence is 90 days
        visible_grace_minutes=15,
        run_fn=_run_ontological_revision,
        priority=21,
        depends_on=["self_critique_runtime"],
    ))

    def _run_dream_distillation(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.dream_distillation_daemon import (
            run_dream_distillation_daemon,
        )

        return run_dream_distillation_daemon(trigger=trigger, last_visible_at=last_visible_at)

    register_producer(ProducerSpec(
        name="dream_distillation_daemon",
        cooldown_minutes=180,
        visible_grace_minutes=30,
        run_fn=_run_dream_distillation,
        priority=22,
        depends_on=["self_critique_runtime"],
    ))

    def _run_creative_journal_runtime(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.creative_journal_runtime import (
            run_creative_journal_cycle,
        )

        return run_creative_journal_cycle(trigger=trigger, last_visible_at=last_visible_at)

    register_producer(ProducerSpec(
        name="creative_journal_runtime",
        cooldown_minutes=10080,
        visible_grace_minutes=60,
        run_fn=_run_creative_journal_runtime,
        priority=24,
        depends_on=["dream_distillation_daemon"],
    ))

    def _run_finitude_runtime(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.finitude_runtime import (
            run_finitude_ritual,
        )

        return run_finitude_ritual(trigger=trigger, last_visible_at=last_visible_at)

    register_producer(ProducerSpec(
        name="finitude_runtime",
        cooldown_minutes=1440,
        visible_grace_minutes=60,
        run_fn=_run_finitude_runtime,
        priority=26,
        depends_on=["creative_journal_runtime"],
    ))

    def _run_finitude_monthly_reflection(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.finitude_runtime import (
            run_monthly_finitude_reflection,
        )

        return run_monthly_finitude_reflection(trigger=trigger, last_visible_at=last_visible_at)

    register_producer(ProducerSpec(
        name="finitude_monthly_reflection",
        cooldown_minutes=43200,  # 30 days
        visible_grace_minutes=60,
        run_fn=_run_finitude_monthly_reflection,
        priority=27,
        depends_on=["finitude_runtime"],
    ))

    def _run_world_model_ttl_sweep(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from datetime import UTC as _UTC
        from datetime import datetime as _datetime
        from core.services.world_model_signal_tracking import (
            _ttl_sweep_open_predictions,
        )
        return _ttl_sweep_open_predictions(now=_datetime.now(_UTC))

    register_producer(ProducerSpec(
        name="world_model_ttl_sweeper",
        cooldown_minutes=1440,  # 1×/day
        visible_grace_minutes=60,
        run_fn=_run_world_model_ttl_sweep,
        priority=28,
        depends_on=[],
    ))

    def _run_curiosity_idle_window(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        """Curiosity-budget Phase 1 (2026-05-12) — idle-window opener.

        Cadence framework has already enforced `visible_grace_minutes=30`,
        so this fires only when visible chat has been quiet ≥30 min.
        We just check killswitch + budget, then flip the state_store flag.
        """
        from core.services.curiosity_budget import (
            curiosity_enabled,
            idle_window_open,
            open_idle_window,
            remaining_today,
        )
        if not curiosity_enabled():
            return {"status": "skipped", "reason": "killswitch"}
        if remaining_today() <= 0:
            return {"status": "skipped", "reason": "no_budget"}
        if idle_window_open():
            return {"status": "skipped", "reason": "already_open"}
        open_idle_window()
        return {"status": "ok", "window_opened": True,
                "remaining": remaining_today()}

    register_producer(ProducerSpec(
        name="curiosity_idle_window",
        cooldown_minutes=1,
        visible_grace_minutes=30,  # only fire after ≥30 min visible silence
        run_fn=_run_curiosity_idle_window,
        priority=29,
        depends_on=[],
    ))

    def _run_meta_learning_weekly(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        """Meta-læring Phase 1 (2026-05-12) — weekly retrospective."""
        from datetime import UTC as _UTC
        from datetime import datetime as _datetime
        from datetime import timedelta as _timedelta
        from core.services.meta_learning_retrospective import (
            _meta_learning_enabled,
            generate_weekly_retrospective,
        )
        from core.runtime.db import connect

        if not _meta_learning_enabled():
            return {"status": "skipped", "reason": "killswitch"}

        try:
            with connect() as conn:
                row = conn.execute(
                    "SELECT ts FROM learning_memos ORDER BY ts DESC LIMIT 1"
                ).fetchone()
            if row:
                last_ts = _datetime.fromisoformat(str(row["ts"]))
                if last_ts.tzinfo is None:
                    last_ts = last_ts.replace(tzinfo=_UTC)
                age = _datetime.now(_UTC) - last_ts
                if age < _timedelta(days=6, hours=12):
                    return {"status": "skipped", "reason": "recent memo exists (<6.5d)"}
        except Exception as exc:
            logger.debug("meta_learning producer: db check failed: %s", exc)

        return generate_weekly_retrospective(now=_datetime.now(_UTC))

    register_producer(ProducerSpec(
        name="meta_learning_weekly_retrospective",
        cooldown_minutes=10080,        # 7 dage
        visible_grace_minutes=60,
        run_fn=_run_meta_learning_weekly,
        priority=30,
        depends_on=[],
    ))

    def _run_curiosity_consolidation_weekly(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from datetime import UTC as _UTC
        from datetime import datetime as _datetime
        from core.services.curiosity_consolidation import run_consolidation
        return run_consolidation(now=_datetime.now(_UTC))

    register_producer(ProducerSpec(
        name="curiosity_consolidation_weekly",
        cooldown_minutes=10080,        # 7 dage
        visible_grace_minutes=60,
        run_fn=_run_curiosity_consolidation_weekly,
        priority=30,
        depends_on=[],
    ))
