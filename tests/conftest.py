from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture()
def isolated_runtime(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> SimpleNamespace:
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    monkeypatch.chdir(repo_root)

    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(home))

    module_names = [
        "core.runtime.config",
        "core.runtime.settings",
        "core.runtime.db",
        "core.runtime.bootstrap",
        "core.auth.profiles",
        "core.auth.copilot_oauth",
        "core.runtime.provider_router",
        "core.identity.workspace_bootstrap",
        "core.identity.visible_identity",
        "apps.api.jarvis_api.services.prompt_contract",
        "apps.api.jarvis_api.services.visible_model",
        "apps.api.jarvis_api.services.heartbeat_runtime",
        "apps.api.jarvis_api.services.candidate_tracking",
        "apps.api.jarvis_api.services.non_visible_lane_execution",
        "apps.api.jarvis_api.services.reflection_signal_tracking",
        "apps.api.jarvis_api.services.temporal_recurrence_signal_tracking",
        "apps.api.jarvis_api.services.witness_signal_tracking",
        "apps.api.jarvis_api.services.open_loop_signal_tracking",
        "apps.api.jarvis_api.services.internal_opposition_signal_tracking",
        "apps.api.jarvis_api.services.self_review_signal_tracking",
        "apps.api.jarvis_api.services.self_review_record_tracking",
        "apps.api.jarvis_api.services.self_review_run_tracking",
        "apps.api.jarvis_api.services.self_review_outcome_tracking",
        "apps.api.jarvis_api.services.self_review_cadence_signal_tracking",
        "apps.api.jarvis_api.services.dream_hypothesis_signal_tracking",
        "apps.api.jarvis_api.services.dream_adoption_candidate_tracking",
        "apps.api.jarvis_api.services.dream_influence_proposal_tracking",
        "apps.api.jarvis_api.services.self_authored_prompt_proposal_tracking",
        "apps.api.jarvis_api.services.user_understanding_signal_tracking",
        "apps.api.jarvis_api.services.remembered_fact_signal_tracking",
        "apps.api.jarvis_api.services.private_inner_note_signal_tracking",
        "apps.api.jarvis_api.services.private_initiative_tension_signal_tracking",
        "apps.api.jarvis_api.services.private_inner_interplay_signal_tracking",
        "apps.api.jarvis_api.services.private_state_snapshot_tracking",
        "apps.api.jarvis_api.services.private_temporal_curiosity_state_tracking",
        "apps.api.jarvis_api.services.inner_visible_support_signal_tracking",
        "apps.api.jarvis_api.services.private_temporal_promotion_signal_tracking",
        "apps.api.jarvis_api.services.user_md_update_proposal_tracking",
        "apps.api.jarvis_api.services.memory_md_update_proposal_tracking",
        "apps.api.jarvis_api.services.selfhood_proposal_tracking",
        "apps.api.jarvis_api.services.open_loop_closure_proposal_tracking",
        "apps.api.jarvis_api.routes.mission_control",
    ]
    modules: dict[str, object] = {}
    for name in module_names:
        module = importlib.import_module(name)
        modules[name] = importlib.reload(module)

    runtime_bootstrap = modules["core.runtime.bootstrap"]
    runtime_db = modules["core.runtime.db"]
    workspace_bootstrap = modules["core.identity.workspace_bootstrap"]

    runtime_bootstrap.ensure_runtime_dirs()
    runtime_db.init_db()
    workspace_bootstrap.ensure_default_workspace()

    return SimpleNamespace(
        config=modules["core.runtime.config"],
        settings=modules["core.runtime.settings"],
        db=runtime_db,
        bootstrap=runtime_bootstrap,
        auth_profiles=modules["core.auth.profiles"],
        copilot_oauth=modules["core.auth.copilot_oauth"],
        provider_router=modules["core.runtime.provider_router"],
        workspace_bootstrap=workspace_bootstrap,
        visible_identity=modules["core.identity.visible_identity"],
        prompt_contract=modules["apps.api.jarvis_api.services.prompt_contract"],
        visible_model=modules["apps.api.jarvis_api.services.visible_model"],
        heartbeat_runtime=modules["apps.api.jarvis_api.services.heartbeat_runtime"],
        candidate_tracking=modules["apps.api.jarvis_api.services.candidate_tracking"],
        non_visible_lane_execution=modules["apps.api.jarvis_api.services.non_visible_lane_execution"],
        reflection_tracking=modules["apps.api.jarvis_api.services.reflection_signal_tracking"],
        temporal_recurrence_tracking=modules["apps.api.jarvis_api.services.temporal_recurrence_signal_tracking"],
        witness_tracking=modules["apps.api.jarvis_api.services.witness_signal_tracking"],
        open_loop_tracking=modules["apps.api.jarvis_api.services.open_loop_signal_tracking"],
        internal_opposition_tracking=modules["apps.api.jarvis_api.services.internal_opposition_signal_tracking"],
        self_review_tracking=modules["apps.api.jarvis_api.services.self_review_signal_tracking"],
        self_review_record_tracking=modules["apps.api.jarvis_api.services.self_review_record_tracking"],
        self_review_run_tracking=modules["apps.api.jarvis_api.services.self_review_run_tracking"],
        self_review_outcome_tracking=modules["apps.api.jarvis_api.services.self_review_outcome_tracking"],
        self_review_cadence_tracking=modules["apps.api.jarvis_api.services.self_review_cadence_signal_tracking"],
        dream_hypothesis_tracking=modules["apps.api.jarvis_api.services.dream_hypothesis_signal_tracking"],
        dream_adoption_candidate_tracking=modules["apps.api.jarvis_api.services.dream_adoption_candidate_tracking"],
        dream_influence_proposal_tracking=modules["apps.api.jarvis_api.services.dream_influence_proposal_tracking"],
        self_authored_prompt_proposal_tracking=modules["apps.api.jarvis_api.services.self_authored_prompt_proposal_tracking"],
        user_understanding_signal_tracking=modules["apps.api.jarvis_api.services.user_understanding_signal_tracking"],
        remembered_fact_signal_tracking=modules["apps.api.jarvis_api.services.remembered_fact_signal_tracking"],
        private_inner_note_signal_tracking=modules["apps.api.jarvis_api.services.private_inner_note_signal_tracking"],
        private_initiative_tension_signal_tracking=modules["apps.api.jarvis_api.services.private_initiative_tension_signal_tracking"],
        private_inner_interplay_signal_tracking=modules["apps.api.jarvis_api.services.private_inner_interplay_signal_tracking"],
        private_state_snapshot_tracking=modules["apps.api.jarvis_api.services.private_state_snapshot_tracking"],
        private_temporal_curiosity_state_tracking=modules["apps.api.jarvis_api.services.private_temporal_curiosity_state_tracking"],
        inner_visible_support_signal_tracking=modules["apps.api.jarvis_api.services.inner_visible_support_signal_tracking"],
        private_temporal_promotion_signal_tracking=modules["apps.api.jarvis_api.services.private_temporal_promotion_signal_tracking"],
        user_md_update_proposal_tracking=modules["apps.api.jarvis_api.services.user_md_update_proposal_tracking"],
        memory_md_update_proposal_tracking=modules["apps.api.jarvis_api.services.memory_md_update_proposal_tracking"],
        selfhood_proposal_tracking=modules["apps.api.jarvis_api.services.selfhood_proposal_tracking"],
        open_loop_closure_proposal_tracking=modules["apps.api.jarvis_api.services.open_loop_closure_proposal_tracking"],
        mission_control=modules["apps.api.jarvis_api.routes.mission_control"],
    )
