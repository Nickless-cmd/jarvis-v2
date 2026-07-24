from __future__ import annotations

import asyncio
import importlib
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

# Ensure repo root is on sys.path for ALL tests at collection time, not
# only those that use the isolated_runtime fixture. Tests that import
# from `core.*` directly at module scope (e.g. test_theater_audit.py
# added 2026-05-08) need this BEFORE pytest imports the test module.
# `conda run` can drop PYTHONPATH, so we can't rely on the env var alone.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


# ── Klasse-identitets-anker for core.services.visible_model ──────────────────
# isolated_runtime reloader core.services.visible_model. importlib.reload()
# re-eksekverer modulet → dets @dataclass-værdiklasser (VisibleModelStreamDone,
# VisibleModelResult, …) bliver NYE klasse-objekter. De tunge konsumenter der
# holder dem — core.services.visible_runs frem for alt (`from
# core.services.visible_model import VisibleModelStreamDone` på modul-niveau) —
# reloades ALDRIG. Efter reload'et bliver visible_runs' interne
# `isinstance(item, VisibleModelStreamDone)` False for en frisk-konstrueret
# stream-done → et gyldigt svar behandles som "intet endeligt resultat" →
# first-pass-provider-error FØR persist-stien → persist_failed-nerven fyrer
# aldrig (test_h5) og visible_runs-adfærdstests bliver ordre-afhængigt flaky.
#
# Vi snapshotter ANKER-klasserne ÉN gang her (ved conftest-load, FØR nogen
# reload) — det er præcis A0, klasserne som de aldrig-reloadede konsumenter
# holder. isolated_runtime gen-installerer dem i det reloadede modul, så
# klasse-identiteten er stabil proces-globalt og isinstance holder.
_VISIBLE_MODEL_ANCHOR_CLASSES: dict[str, type] = {}
try:
    import core.services.visible_model as _anchor_vm  # noqa: E402

    for _anchor_name in (
        "VisibleModelResult",
        "VisibleModelDelta",
        "VisibleModelStreamDone",
        "VisibleModelToolCalls",
        "VisibleModelStreamCancelled",
        "VisibleModelRateLimited",
    ):
        _anchor_obj = getattr(_anchor_vm, _anchor_name, None)
        if isinstance(_anchor_obj, type):
            _VISIBLE_MODEL_ANCHOR_CLASSES[_anchor_name] = _anchor_obj
except Exception:
    _VISIBLE_MODEL_ANCHOR_CLASSES = {}


# ── Klasse-identitets-anker for core.services.visible_runs ───────────────────
# test_visible_runs.py::test_module_imports gør `importlib.reload(visible_runs)`
# (bevidst, for at overflade import-fejl). reload() re-eksekverer modulet ind i
# SAMME modul-__dict__ → dets klasser (PresentationInvariantError, VisibleRun,
# VisibleRunController) bliver NYE objekter, OG modulets funktioner rebindes.
# Downstream-tests der importerede symboler ved collection (fx
# test_visible_runs_presentation_invariant: `from core.services.visible_runs
# import PresentationInvariantError, _assert_presentation_invariant`) holder den
# GAMLE funktion — men funktionen slår `PresentationInvariantError` op i modulets
# __dict__ (func.__globals__), som reload'et netop har erstattet med den NYE
# klasse. `_assert_presentation_invariant` raiser da NEW-klassen mens testen
# `pytest.raises(OLD)` ikke fanger den → ustabile reject-tests alt efter om
# test_visible_runs kørte før dem. BEVIST: test_visible_runs → presentation
# fejler; test_autonomous → presentation passer.
#
# Fix: snapshot ANKER-klasserne (fra første import, FØR nogen reload) og
# gen-installér dem i modul-__dict__ efter HVER test (autouse-fixture nedenfor).
# Idempotent + billig; holder func.__globals__-opslaget stabilt proces-globalt.
_VISIBLE_RUNS_ANCHOR_CLASSES: dict[str, type] = {}
try:
    import core.services.visible_runs as _anchor_vr  # noqa: E402

    for _anchor_name in (
        "PresentationInvariantError",
        "VisibleRun",
        "VisibleRunController",
    ):
        _anchor_obj = getattr(_anchor_vr, _anchor_name, None)
        if isinstance(_anchor_obj, type):
            _VISIBLE_RUNS_ANCHOR_CLASSES[_anchor_name] = _anchor_obj
except Exception:
    _VISIBLE_RUNS_ANCHOR_CLASSES = {}


@pytest.fixture(scope="session")
def _prod_db_shield_path(tmp_path_factory):
    """Én skema-komplet tmp-DB pr. session som ikke-isolerede tests peges mod.

    Skemaet KOPIERES fra den ægte prod-DB (alle tabeller/indekser/triggere, men
    TOMME) — ikke bygget via `init_db()`, som ikke skaber alle prod-tabeller (fx
    `cognitive_decisions`). Kopi = shielden er skema-tro med prod, så en ikke-
    isoleret test der læser/ALTER'er en vilkårlig prod-tabel opfører sig som mod
    prod, bare uden data og uden at røre den ægte DB. init_db() køres bagefter som
    supplement (tabeller der KUN lever i runtime-init, ikke i prod endnu)."""
    import sqlite3
    from core.runtime.config import STATE_DIR as _real_state
    shield = tmp_path_factory.mktemp("prod_db_shield") / "jarvis.db"
    prod = Path(_real_state) / "jarvis.db"
    # 1) Kopiér prods fulde skema (tomt) hvis prod findes.
    if prod.is_file():
        try:
            src = sqlite3.connect(f"file:{prod}?mode=ro", uri=True)
            try:
                stmts = [
                    r[0] for r in src.execute(
                        "SELECT sql FROM sqlite_master "
                        "WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%' "
                        "ORDER BY CASE type WHEN 'table' THEN 0 WHEN 'index' "
                        "THEN 1 ELSE 2 END"
                    ).fetchall() if r[0]
                ]
            finally:
                src.close()
            dst = sqlite3.connect(str(shield))
            try:
                for sql in stmts:
                    try:
                        dst.execute(sql)
                    except Exception:
                        pass  # dublet/afhængigheds-rækkefølge — skip, aldrig vælt
                dst.commit()
            finally:
                dst.close()
        except Exception:
            pass
    # 2) Supplér med init_db() (runtime-only tabeller ikke i prod-skemaet endnu).
    import core.runtime.db_core as db_core
    prev = db_core.DB_PATH
    try:
        db_core.DB_PATH = shield
        from core.runtime.db_schema import init_db
        init_db()
    except Exception:
        pass
    finally:
        db_core.DB_PATH = prev
    return shield


@pytest.fixture(autouse=True)
def _guard_prod_db_path(request, monkeypatch):
    """Sikkerhedsnet: INGEN test må skrive i den ægte ~/.jarvis-v2/state/jarvis.db."""
    if request.node.get_closest_marker("real_db") is not None:
        yield
        return
    try:
        import core.runtime.db_core as db_core
        from core.runtime.config import STATE_DIR as _real_state
        real_prod = Path(_real_state) / "jarvis.db"
        if db_core.DB_PATH == real_prod:
            shield = request.getfixturevalue("_prod_db_shield_path")
            monkeypatch.setattr(db_core, "DB_PATH", shield)
    except Exception:
        pass
    yield


@pytest.fixture(autouse=True)
def _restore_visible_runs_anchor_classes():
    """Gen-installér visible_runs' ANKER-klasser efter hver test (se blok ovenfor).

    Fanger den destruktive `importlib.reload(visible_runs)` i test_visible_runs.py,
    så en efterfølgende test der holder GAMLE symboler (PresentationInvariantError
    m.fl.) igen ser samme klasse-objekt som modulets funktioner raiser.
    """
    yield
    if not _VISIBLE_RUNS_ANCHOR_CLASSES:
        return
    _vr_mod = sys.modules.get("core.services.visible_runs")
    if _vr_mod is None:
        return
    for _cls_name, _obj in _VISIBLE_RUNS_ANCHOR_CLASSES.items():
        try:
            if getattr(_vr_mod, _cls_name, None) is not _obj:
                setattr(_vr_mod, _cls_name, _obj)
        except Exception:
            pass


@pytest.fixture(autouse=True)
def _ensure_current_event_loop():
    """Guarantee ``asyncio.get_event_loop()`` works in every (sync) test.

    pytest-asyncio (strict mode) creates a fresh function-scoped event loop
    for each ``@pytest.mark.asyncio`` test and, on teardown, closes it and
    leaves the thread-local current-loop set to None/closed. A *sync* test
    that runs afterwards and calls ``asyncio.get_event_loop()`` (e.g. the
    ``_run`` helpers in tests/test_central_*_route.py) then blows up with
    ``RuntimeError: There is no current event loop in thread 'MainThread'``.

    That is pure cross-test global-state leakage: the affected tests pass in
    isolation and only fail when an async test ran before them in the same
    process. This autouse fixture repairs the invariant before each test by
    ensuring a live, open current event loop exists — creating and installing
    a fresh one if the current loop is missing or was closed. It does not run
    or own the loop; it only restores the default-loop contract that
    ``get_event_loop()``-style call sites rely on.
    """
    try:
        loop = asyncio.get_event_loop_policy().get_event_loop()
        if loop.is_closed():
            raise RuntimeError("closed")
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    yield


@pytest.fixture(autouse=True)
def _reset_ensure_once_cache():
    """Tøm _ENSURED_TABLES cache før hver test.

    Cachen lever module-level i core.runtime.db_core (efter 2026-05-15
    split). Cache-key er (func_name, conn_db_id). For :memory: connections
    er conn_db_id = "memory:{id(conn)}" — CPython genbruger memory addresses
    efter GC, så to sekventielle tests kan ramme samme cache-key og
    fejle silent (anden test får cache-hit, tabel oprettes ikke).

    Denne autouse-fixture invaliderer cachen før hver test for at undgå
    race condition. Pre-2026-05-15 var cachen i db.py og blev tømt af
    conftest's reload-liste.
    """
    try:
        from core.runtime.db_core import invalidate_ensure_once_cache
        invalidate_ensure_once_cache()
    except ImportError:
        pass

    # 2026-05-17: efter perf-fix returnerer get_timed_runtime_surface samme
    # objekt på hver cache-hit (ingen per-read deepcopy). _TIMED_CACHE er
    # module-level state der ellers lækker mellem tests — clear før hver.
    try:
        from core.services.runtime_surface_cache import _TIMED_CACHE
        _TIMED_CACHE.clear()
    except ImportError:
        pass

    # 2026-07-07: core.services.emotion_concepts holder ÉT proces-globalt
    # register af aktive emotion-koncepter (_active) + akkumuleret residue
    # (_expired_residue) + trigger-throttle (_last_trigger_at). Modulet
    # reloades ALDRIG af isolated_runtime, så koncepter som én test aktiverer
    # (direkte via activate/trigger, eller indirekte via approval_feedback-
    # subscriber, cognitive-episode-triggers, osv.) overlever ind i næste test.
    #
    # get_lag1_influence_deltas() blander disse aktive koncepter ind i Lag-1-
    # akserne (confidence/curiosity/frustration/fatigue). En efterfølgende test
    # der forventer sin egen rene emotional_baseline (fx
    # test_affective_meta_state: fatigue skal være 0.1) får i stedet baseline +
    # lækket delta (fatigue → 0.07 pga. et lækket 'warmth'-koncept med
    # fatigue -0.03). Rammer også de tunge DB-tests længere nede i suiten via
    # samme delte modul-state. Nulstil registret før hver test.
    try:
        from core.services import emotion_concepts as _ec
        if hasattr(_ec, "_lock"):
            with _ec._lock:  # type: ignore[attr-defined]
                _ec._active.clear()  # type: ignore[attr-defined]
                for _ax in _ec._expired_residue:  # type: ignore[attr-defined]
                    _ec._expired_residue[_ax] = 0.0  # type: ignore[attr-defined]
                _ec._last_trigger_at.clear()  # type: ignore[attr-defined]
        else:
            _ec._active.clear()  # type: ignore[attr-defined]
    except (ImportError, AttributeError):
        pass


@pytest.fixture(autouse=True)
def _bypass_timed_surface_cache(request, monkeypatch):
    """Omgå den proces-globale timed-surface-cache i tests (undtagen dens egen test).

    2026-07-07: ORDRE-AFHÆNGIG FLAKY
    (test_visible_runs_open_loop_materialization::…downstream_tracking).
    `build_runtime_open_loop_signal_surface` m.fl. cacher deres resultat i
    core.services.runtime_surface_cache._TIMED_CACHE (60s TTL, key=(navn,limit),
    UDEN DB-identitet). Baggrunds-daemons der er varmet af en TIDLIGERE test (fx
    test_visible_runs_loop_not_blocked's ægte _stream_visible_run) BLIVER ved med
    at køre og skrive TOMME surfaces (bygget mod deres egen tomme DB) ind i
    _TIMED_CACHE — også EFTER test-start-clear'en OG efter isolated_runtime's
    pre-yield-clear, MENS denne tests krop kører. Den efterfølgende surface-læsning
    rammer da den cachede tomme surface → open-loop-signalet er usynligt →
    lifecycle-extractoren giver 0 → `assert len(lifecycle) == 2` fejler. Ren
    test-start-clear kan ikke vinde løbet mod en levende baggrunds-tråd.

    Fix: gør `get_timed_runtime_surface(key, ttl, builder)` til en ren
    passthrough (`builder()`) under tests → cachen konsulteres aldrig, så en
    forurenet cache-post kan ikke lække ind. Produktions-adfærd er uændret; kun
    test-processen påvirkes. `test_runtime_surface_cache.py` tester cachen
    eksplicit og springes over her, så dens kontrakt-tests består.

    Rent test-side; ingen runtime-fil røres.
    """
    # Tests der bevidst VERIFICERER at den tidsbegrænsede cache collapser gentagne
    # builds må IKKE få cachen no-op'et (ellers bygger de N gange og fejler assert).
    _fspath = str(getattr(request.node, "fspath", ""))
    if ("test_runtime_surface_cache" in _fspath
            or "test_cognitive_architecture_surface" in _fspath):
        yield
        return
    try:
        import core.services.runtime_surface_cache as _rsc

        # get_timed_runtime_surface læser/skriver modulets _TIMED_CACHE-dict via
        # `.get()`/`[]=`. Alle surface-builder-moduler importerer FUNKTIONEN ved
        # navn (`from … import get_timed_runtime_surface`), så det er upålideligt
        # at monkeypatche selve funktionen (den er kopieret ind i N moduler).
        # I stedet erstatter vi _TIMED_CACHE med en dict hvis reads ALTID misser
        # og writes er no-ops → funktionen kalder altid builder() (frisk DB-læs),
        # uanset hvilken baggrunds-tråd der forsøger at forurene cachen. Samme
        # _TIMED_CACHE-objekt bruges af funktionen (modul-global lookup), så
        # dette rammer alle call-sites. Genskabes efter testen (monkeypatch).
        class _NoTimedCache(dict):
            def get(self, *_a, **_k):  # noqa: ANN001, ANN002, ANN003
                return None

            def __getitem__(self, _k):  # noqa: ANN001
                raise KeyError(_k)

            def __setitem__(self, _k, _v):  # noqa: ANN001
                return None

        monkeypatch.setattr(_rsc, "_TIMED_CACHE", _NoTimedCache(), raising=False)
    except Exception:
        pass
    yield


@pytest.fixture(autouse=True)
def _neutralize_inner_voice_shadow_llm(monkeypatch):
    """Gør inner_voice_shadow's LLM-kald fail-fast i tests (ingen ægte netværk).

    2026-07-07: ORDRE-AFHÆNGIG FLAKY (test_autonomous_visible_runs
    ::…_interrupted…): den autonome run's fake `_stream_visible_run` kalder det
    ÆGTE `set_last_visible_run_outcome` → `write_private_terminal_layers` →
    `private_inner_note._private_summary` → `inner_voice_shadow.
    generate_private_summary_via_llm`. Den spawner en tråd der kører det ÆGTE
    `_call_llm` (→ `execute_cheap_lane_via_pool`, RIGTIGT provider-HTTP-kald) og
    `thread.join(timeout=5s)`. Kørt ALENE fejler cheap-lane-poolen hurtigt
    (ingen varm provider) → summary falder straks tilbage. Men efter en test der
    har VARMET provider-poolen (fx test_visible_runs_loop_not_blocked, der driver
    det ægte _stream_visible_run) laver `_call_llm` et RIGTIGT netværkskald der
    tager de fulde ~5s pr. kald × flere private-lag-summaries → runnet passerer
    ALDRIG sit finally (interrupted-publish) inden testens 2s-deadline → nerven
    mangler. BEVIST via faulthandler: den autonome tråd stod i
    inner_voice_shadow.generate_appraisal → threading.join → _wait_for_tstate_lock.

    Fix: stub `_call_llm` til et øjeblikkeligt fejl-svar. Modulets egen kontrakt
    (fail → template_fallback) er intakt, og de dedikerede inner_voice_shadow-
    tests (test_inner_voice_shadow.py m.fl.) sætter deres EGEN `_call_llm` i
    test-kroppen, der kører EFTER denne autouse-fixture → deres patch vinder.
    Rent test-side; ingen runtime-fil røres.
    """
    try:
        import core.services.inner_voice_shadow as _ivs

        def _fast_fail_llm(prompt):  # noqa: ANN001
            return {
                "output": None,
                "provider": None,
                "model": None,
                "latency_ms": 0,
                "error": "test-neutralized",
            }

        monkeypatch.setattr(_ivs, "_call_llm", _fast_fail_llm, raising=False)
    except Exception:
        pass
    yield


@pytest.fixture()
def isolated_runtime(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    import os

    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    monkeypatch.chdir(repo_root)

    _prev_home = os.environ.get("HOME")
    _prev_ws = os.environ.get("JARVIS_WORKSPACES_DIR")

    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("JARVIS_WORKSPACES_DIR", str(tmp_path / "workspaces"))

    module_names = [
        "core.runtime.config",
        "core.runtime.settings",
        # runtime_json_io binds SETTINGS_FILE/CONFIG_DIR at import time. If it is
        # not reloaded after HOME is repointed at tmp_path, its writer targets the
        # REAL ~/.jarvis-v2/config/runtime.json while load_settings() reads the tmp
        # copy — settings writes silently escape isolation (and pollute the real
        # config). Reload it right after config so writes land in the tmp config.
        "core.runtime.runtime_json_io",
        # secrets binder `SETTINGS_FILE` via `from core.runtime.config import
        # SETTINGS_FILE` ved import-tid. Uden reload (efter config ovenfor) peger
        # `secrets.SETTINGS_FILE` stadig på den ÆGTE ~/.jarvis-v2/config/runtime.json,
        # så `read_runtime_key(...)` læser rigtige secrets ind i isolerede tests
        # (import-rækkefølge-afhængigt) — fx blev huggingface_token synlig og gjorde
        # HF-slottet "ready" i cheap-lane-tests der asserter en eksakt provider-liste.
        "core.runtime.secrets",
        # db_core skal reloades FØR db, fordi db re-eksporterer fra db_core
        # og _ENSURED_TABLES cache lever i db_core (efter 2026-05-15 split).
        # Uden dette overlever cache-entries mellem tests og forurener
        # downstream tests (fx test_subscriber_ignores_unrelated_events).
        "core.runtime.db_core",
        "core.runtime.db",
        "core.runtime.bootstrap",
        "core.auth.profiles",
        "core.auth.copilot_oauth",
        "core.auth.openai_oauth",
        "core.runtime.provider_router",
        "core.identity.workspace_bootstrap",
        "core.identity.visible_identity",
        "core.tools.workspace_capabilities",
        # prompt_support_signals does `from core.runtime.db import
        # list_runtime_goal_signals, list_runtime_world_model_signals, ...` AT
        # MODULE LEVEL. When isolated_runtime reloads core.runtime.db under the
        # tmp HOME, prompt_support_signals keeps its STALE db-func references
        # bound to whatever db module a *previous* test reloaded — so its
        # list_runtime_goal_signals() reads an earlier tmp/real DB, not the one
        # the test inserted its goal signal into. The "Goal support signal:"
        # block then never appears (test_world_model_prompt_bridge:
        # test_visible_input_includes_small_subordinate_goal_support_block).
        # prompt_contract re-imports these names FROM prompt_support_signals, so
        # this must be reloaded AFTER core.runtime.db and BEFORE prompt_contract.
        "core.services.prompt_support_signals",
        "core.services.prompt_contract",
        # Boy-scout split (2026-07-07): visible_model was split into a facade +
        # sibling submodules. Mutable module-level state that HEAD kept in the
        # single module now lives in _adapters (_GITHUB_VISIBLE_COOLDOWN_UNTIL /
        # _READINESS_PROBE_CACHE). HEAD's isolated_runtime reset that state every
        # test by reloading visible_model (its `X = {}` re-ran). After the split
        # those dicts live in the never-reloaded _adapters module → cross-test
        # cooldown/probe pollution (test_github_visible_execution_readiness_shows_
        # cooldown flips flaky by order). Reload _adapters FIRST so its state
        # resets; the facade reload below then re-imports the fresh objects.
        # IMPORTANT: do NOT reload visible_model_types — its @dataclass value
        # classes are the process-global isinstance anchor (see top of file); a
        # fresh _adapters re-imports the SAME (unreloaded) value classes, so
        # class identity stays stable across the module boundary.
        "core.services.visible_model_adapters",
        "core.services.visible_model",
        "core.services.cheap_provider_runtime",
        "core.services.heartbeat_runtime",
        "core.services.candidate_tracking",
        "core.services.non_visible_lane_execution",
        "core.services.reflection_signal_tracking",
        "core.services.temporal_recurrence_signal_tracking",
        "core.services.witness_signal_tracking",
        "core.services.open_loop_signal_tracking",
        "core.services.internal_opposition_signal_tracking",
        "core.services.self_review_signal_tracking",
        "core.services.self_review_record_tracking",
        "core.services.self_review_run_tracking",
        "core.services.self_review_outcome_tracking",
        "core.services.self_review_cadence_signal_tracking",
        "core.services.dream_hypothesis_signal_tracking",
        "core.services.dream_adoption_candidate_tracking",
        "core.services.dream_influence_proposal_tracking",
        "core.services.self_authored_prompt_proposal_tracking",
        "core.services.user_understanding_signal_tracking",
        "core.services.remembered_fact_signal_tracking",
        "core.services.private_inner_note_signal_tracking",
        "core.services.private_initiative_tension_signal_tracking",
        "core.services.private_inner_interplay_signal_tracking",
        "core.services.private_state_snapshot_tracking",
        "core.services.diary_synthesis_signal_tracking",
        "core.services.private_temporal_curiosity_state_tracking",
        "core.services.inner_visible_support_signal_tracking",
        "core.services.regulation_homeostasis_signal_tracking",
        "core.services.relation_state_signal_tracking",
        "core.services.relation_continuity_signal_tracking",
        "core.services.meaning_significance_signal_tracking",
        "core.services.temperament_tendency_signal_tracking",
        "core.services.self_narrative_continuity_signal_tracking",
        "core.services.metabolism_state_signal_tracking",
        "core.services.release_marker_signal_tracking",
        "core.services.consolidation_target_signal_tracking",
        "core.services.selective_forgetting_candidate_tracking",
        "core.services.attachment_topology_signal_tracking",
        "core.services.loyalty_gradient_signal_tracking",
        "core.services.autonomy_pressure_signal_tracking",
        "core.services.proactive_loop_lifecycle_tracking",
        "core.services.proactive_question_gate_tracking",
        "core.services.tiny_webchat_execution_pilot",
        "core.services.self_narrative_self_model_review_bridge",
        "core.services.executive_contradiction_signal_tracking",
        "core.services.private_temporal_promotion_signal_tracking",
        "core.services.chronicle_consolidation_signal_tracking",
        "core.services.chronicle_consolidation_brief_tracking",
        "core.services.chronicle_consolidation_proposal_tracking",
        "core.services.emergent_signal_tracking",
        "core.services.user_md_update_proposal_tracking",
        "core.services.memory_md_update_proposal_tracking",
        "core.services.selfhood_proposal_tracking",
        "core.services.open_loop_closure_proposal_tracking",
        "core.services.internal_cadence",
        "core.services.embodied_state",
        "core.services.affective_meta_state",
        "core.services.experiential_runtime_context",
        "core.services.epistemic_runtime_state",
        "core.services.subagent_ecology",
        "core.services.council_runtime",
        "core.services.adaptive_planner_runtime",
        "core.services.adaptive_reasoning_runtime",
        "core.services.guided_learning_runtime",
        "core.services.adaptive_learning_runtime",
        "core.services.dream_influence_runtime",
        "core.services.self_system_code_awareness",
        "core.services.bounded_repo_tools_runtime",
        "core.services.bounded_action_continuity_runtime",
        "core.services.bounded_mutation_intent_runtime",
        "core.services.tool_intent_approval_runtime",
        "core.services.tool_intent_runtime",
        "core.services.loop_runtime",
        "core.services.idle_consolidation",
        "core.services.dream_articulation",
        "core.services.prompt_evolution_runtime",
        "core.services.self_critique_runtime",
        "core.services.creative_journal_runtime",
        "core.services.finitude_runtime",
        "core.services.dream_distillation_daemon",
        "core.services.unconscious_temperature_field",
        "core.services.runtime_self_model",
        # runtime_candidates imports list_runtime_contract_candidates &
        # friends BY NAME from core.runtime.db at module import. When
        # isolated_runtime reloads core.runtime.db under the tmp HOME,
        # runtime_candidates keeps its STALE references bound to whatever db
        # module a *previous* test reloaded — so its connect()/DB_PATH point
        # at an earlier tmp DB with leftover candidate rows. The freshly
        # inserted candidate then never surfaces (list returns stale rows,
        # workflow["items"] is empty → IndexError in
        # test_candidate_apply_readiness). Reload both contract modules so
        # they rebind to the just-reloaded db. Must come AFTER core.runtime.db
        # and BEFORE mission_control (which imports build_runtime_contract_state).
        "core.identity.runtime_candidates",
        "core.identity.runtime_contract",
        # candidate_workflow gør `from core.runtime.db import
        # get_runtime_contract_candidate, ...` PÅ MODUL-NIVEAU. Uden reload
        # holder den STALE db-referencer bundet til en tidligere test's
        # db-reload → apply/approve_runtime_contract_candidate læser en anden
        # DB end testens insert (via db) → "Runtime contract candidate not
        # found" i test_canonical_self_candidate_apply i fuld suite. Samme
        # stale-binding-familie som runtime_candidates ovenfor. Reload EFTER db.
        "core.identity.candidate_workflow",
        "apps.api.jarvis_api.routes.mission_control",
        "core.identity.users",
        "core.identity.workspace_context",
        "core.identity.user_attribution_migrations",
    ]
    # 2026-07-07: CLASS-IDENTITY-LÆK fra reload af core.services.visible_model
    # (den flaky "Visible model stream completed without final result"-familie).
    #
    # Reload-listen indeholder core.services.visible_model. importlib.reload()
    # RE-EKSEKVERER modulet → dets @dataclass-værdiklasser (VisibleModelStreamDone,
    # VisibleModelResult, VisibleModelToolCalls, …) bliver NYE klasse-objekter.
    # Men de tunge konsumenter der holder dem — core.services.visible_runs frem for
    # alt (`from core.services.visible_model import VisibleModelStreamDone` på
    # modul-niveau, linje 193-204) — reloades ALDRIG. Efter reload'et peger
    # visible_runs' `VisibleModelStreamDone` på DEN GAMLE klasse, mens en test der
    # importerer klassen frisk (fx test_streaming_observability_nerves,
    # test_visible_runs_loop_not_blocked) får DEN NYE. visible_runs' interne
    # `isinstance(item, VisibleModelStreamDone)` (visible_runs.py:1316) bliver da
    # False for en frisk-konstrueret stream-done → runnet behandler et gyldigt
    # svar som "intet endeligt resultat" → first-pass-provider-error FØR persist-
    # stien → persist_failed-nerven fyrer aldrig (test_h5) og de øvrige
    # visible_runs-adfærdstests bliver ustabile alt efter om en isolated_runtime-
    # test kørte før dem. BEVIST: vr.VisibleModelStreamDone is (frisk import) →
    # True alene, False efter en isolated_runtime-test.
    #
    # Fix: bevar KLASSE-IDENTITETEN på tværs af reload'et. Klasserne er rene
    # data-containere (ingen HOME-afhængig tilstand), så det er sikkert at gen-
    # installere de ORIGINALE klasse-objekter i det reloadede modul. Så ser ALLE
    # moduler (reloadede som ej) samme klasse-objekt, og isinstance holder.
    # ANKER: de ORIGINALE klasse-objekter fra FØRSTE import (conftest-load, FØR
    # nogen reload). Det er PRÆCIS de klasser som de aldrig-reloadede konsumenter
    # (visible_runs m.fl.) holder. Vi må IKKE gen-snapshotte pr. fixture-entry: har
    # en tidligere isolated_runtime-test allerede reloadet visible_model, er
    # sys.modules-klassen da en NYERE klasse (A1) end den visible_runs stadig
    # holder (A0) → et re-snapshot ville fastfryse A1 og aldrig hele identiteten.
    # _VISIBLE_MODEL_ANCHOR_CLASSES (module-level, taget én gang) er den sande A0.
    def _restore_visible_model_anchor() -> None:
        # Re-installér ANKER-værdiklasserne i det netop-reloadede visible_model,
        # så klasse-identiteten er stabil proces-globalt (se blok ovenfor).
        # KRITISK-TIMING: dette SKAL køre lige efter visible_model reloades og
        # IGEN til sidst. Ellers importerer et SENERE modul i reload-listen (fx
        # heartbeat_runtime/runtime_self_model/cheap_provider_runtime) —
        # eller visible_runs via deres import-kæde — visible_model MENS den
        # bærer de NYE reload-klasser, og binder da den nye klasse for evigt
        # (visible_runs reloades aldrig). Restore lige efter reload'et af
        # visible_model gør at alle downstream-importer ser ANKER-klassen.
        _vm_mod = sys.modules.get("core.services.visible_model")
        if _vm_mod is not None and _VISIBLE_MODEL_ANCHOR_CLASSES:
            for _cls_name, _obj in _VISIBLE_MODEL_ANCHOR_CLASSES.items():
                setattr(_vm_mod, _cls_name, _obj)

    modules: dict[str, object] = {}
    for name in module_names:
        module = importlib.import_module(name)
        modules[name] = importlib.reload(module)
        if name == "core.services.visible_model":
            _restore_visible_model_anchor()

    # Sikkerheds-restore til sidst (idempotent) hvis en senere reload alligevel
    # re-eksekverede visible_model.
    _restore_visible_model_anchor()

    # 2026-07-07: STALE db-submodule connect() binding (den store DB-læk).
    #
    # core/runtime/db.py er splittet (boy scout) i mange db_*-submoduler
    # (db_emotional_memory, db_self_repair, db_users, …). HVER af dem gør
    # `from core.runtime.db import connect, _now_iso` PÅ MODUL-NIVEAU og
    # db.py re-eksporterer deres funktioner (list_emotional_memory_anchors
    # osv.) tilbage.
    #
    # isolated_runtime reloader db_core + db, så connect()/DB_PATH peger på
    # tmp-DB'en. MEN submodulerne reloades IKKE: når db reloades, RE-IMPORTERER
    # den blot de allerede-cachede submodul-objekter, hvis modul-globale
    # `connect` stadig peger på et TIDLIGERE db_core-modul (fx efter at en
    # anden test kørte sin egen db-reload-harness). Resultat: db.py's
    # re-eksporterede list_emotional_memory_anchors() åbner den ÆGTE
    # ~/.jarvis-v2/state/jarvis.db, mens testens egne insert/prune (frisk
    # `from core.runtime.db import connect`) rammer tmp-DB'en → "list ser 50
    # rækker fra ægte DB" + "prune: no such table" i samme test. Rammer de
    # tunge DB-tests (emotional_memory_engine, self_repair_engine, user_db,
    # canonical_self_candidate_apply, causal_graph, …) i fuld suite, aldrig
    # alene. BEVIST: dbe.connect is dbc.connect == False; connect-path ==
    # /home/bs/.jarvis-v2/state/jarvis.db mens dbc.DB_PATH == tmp.
    #
    # Fix: reload db_*-submodulerne EFTER db (så deres `connect` rebinder til
    # den friske db.connect), og reload derefter db ÉN gang til så dens
    # re-eksporter peger på de friske submodul-funktioner. Målrettet — kun de
    # submoduler der binder connect/_now_iso ved import.
    _db_submodules = [
        "core.runtime.db_capability_approval",
        "core.runtime.db_users",
        "core.runtime.db_autonomy",
        "core.runtime.db_scheduled_tasks",
        "core.runtime.db_private_brain",
        "core.runtime.db_emotional_memory",
        "core.runtime.db_self_repair",
        "core.runtime.db_user_contradiction",
        "core.runtime.db_concept_baseline",
        "core.runtime.db_anomalies",
        "core.runtime.db_absence_traces",
        "core.runtime.db_api_connections",
        "core.runtime.db_central_incidents",
        "core.runtime.db_composites",
        "core.runtime.db_credit_assignment",
        "core.runtime.db_decisions",
        "core.runtime.db_dream_bias",
        "core.runtime.db_embeddings",
        "core.runtime.db_gate_verdicts",
        "core.runtime.db_goals",
        "core.runtime.db_instrument",
        "core.runtime.db_interlanguage_blind",
        "core.runtime.db_sensory",
        "core.runtime.db_user_temperature",
    ]
    for _sub in _db_submodules:
        try:
            _m = sys.modules.get(_sub) or importlib.import_module(_sub)
            importlib.reload(_m)
        except Exception:
            pass
    # Re-reload db so its re-exported names bind to the fresh submodule funcs.
    modules["core.runtime.db"] = importlib.reload(
        sys.modules["core.runtime.db"]
    )

    runtime_bootstrap = modules["core.runtime.bootstrap"]
    runtime_db = modules["core.runtime.db"]
    workspace_bootstrap = modules["core.identity.workspace_bootstrap"]

    runtime_bootstrap.ensure_runtime_dirs()
    runtime_db.init_db()
    workspace_bootstrap.ensure_default_workspace()

    # 2026-07-07: STALE TIMED-SURFACE-CACHE-LÆK (den flaky
    # test_visible_runs_open_loop_materialization::…downstream_tracking).
    #
    # `build_runtime_open_loop_signal_surface` (og søster-surfaces) cacher
    # resultatet i core.services.runtime_surface_cache._TIMED_CACHE med 60s TTL,
    # keyed (surface_name, limit) — UDEN DB-identitet i nøglen. En tidligere test
    # der driver det ægte _stream_visible_run (fx test_visible_runs_loop_not_blocked)
    # varmer baggrunds-daemons der bygger disse surfaces mod DERES DB (tom for
    # denne tests open-loop-signal) → cacher en TOM open-loop-surface. autouse-
    # clear'en (_reset_ensure_once_cache) tømmer cachen ved test-START, men de
    # lækkede daemon-tråde kører videre OG re-populerer _TIMED_CACHE bagefter.
    # Når så DENNE test materialiserer sit open-loop-signal i DB'en og læser via
    # surface-builderen, får den den CACHEDE tomme surface (TTL ikke udløbet) →
    # `open items: 0` → lifecycle-extractoren returnerer [] → 0 proaktive-loop-
    # lifecycle-rækker → `assert len(lifecycle) == 2` fejler (0 == 2). BEVIST:
    # _TIMED_CACHE.clear() lige før læsningen giver open items: 1, extractor: 2.
    #
    # Cachen kan ikke afskaffes globalt (test_runtime_surface_cache tester den),
    # men vi kan tømme den lige FØR testkroppen kører (efter init_db), så et
    # isolated_runtime-baseret run altid starter fra en frisk surface-cache — ud
    # over autouse-clear'en, der kan være blevet re-forurenet af lækkede daemons.
    try:
        from core.services.runtime_surface_cache import _TIMED_CACHE as _tsc
        _tsc.clear()
    except Exception:
        pass

    _ns = SimpleNamespace(
        config=modules["core.runtime.config"],
        settings=modules["core.runtime.settings"],
        db=runtime_db,
        bootstrap=runtime_bootstrap,
        auth_profiles=modules["core.auth.profiles"],
        copilot_oauth=modules["core.auth.copilot_oauth"],
        openai_oauth=modules["core.auth.openai_oauth"],
        provider_router=modules["core.runtime.provider_router"],
        runtime_surface_cache=importlib.import_module(
            "core.services.runtime_surface_cache"
        ),
        workspace_bootstrap=workspace_bootstrap,
        visible_identity=modules["core.identity.visible_identity"],
        workspace_capabilities=modules["core.tools.workspace_capabilities"],
        prompt_contract=modules["core.services.prompt_contract"],
        visible_model=modules["core.services.visible_model"],
        cheap_provider_runtime=modules[
            "core.services.cheap_provider_runtime"
        ],
        heartbeat_runtime=modules["core.services.heartbeat_runtime"],
        candidate_tracking=modules["core.services.candidate_tracking"],
        non_visible_lane_execution=modules[
            "core.services.non_visible_lane_execution"
        ],
        reflection_tracking=modules[
            "core.services.reflection_signal_tracking"
        ],
        temporal_recurrence_tracking=modules[
            "core.services.temporal_recurrence_signal_tracking"
        ],
        witness_tracking=modules[
            "core.services.witness_signal_tracking"
        ],
        open_loop_tracking=modules[
            "core.services.open_loop_signal_tracking"
        ],
        internal_opposition_tracking=modules[
            "core.services.internal_opposition_signal_tracking"
        ],
        self_review_tracking=modules[
            "core.services.self_review_signal_tracking"
        ],
        self_review_record_tracking=modules[
            "core.services.self_review_record_tracking"
        ],
        self_review_run_tracking=modules[
            "core.services.self_review_run_tracking"
        ],
        self_review_outcome_tracking=modules[
            "core.services.self_review_outcome_tracking"
        ],
        self_review_cadence_tracking=modules[
            "core.services.self_review_cadence_signal_tracking"
        ],
        dream_hypothesis_tracking=modules[
            "core.services.dream_hypothesis_signal_tracking"
        ],
        dream_adoption_candidate_tracking=modules[
            "core.services.dream_adoption_candidate_tracking"
        ],
        dream_influence_proposal_tracking=modules[
            "core.services.dream_influence_proposal_tracking"
        ],
        self_authored_prompt_proposal_tracking=modules[
            "core.services.self_authored_prompt_proposal_tracking"
        ],
        user_understanding_signal_tracking=modules[
            "core.services.user_understanding_signal_tracking"
        ],
        remembered_fact_signal_tracking=modules[
            "core.services.remembered_fact_signal_tracking"
        ],
        private_inner_note_signal_tracking=modules[
            "core.services.private_inner_note_signal_tracking"
        ],
        private_initiative_tension_signal_tracking=modules[
            "core.services.private_initiative_tension_signal_tracking"
        ],
        private_inner_interplay_signal_tracking=modules[
            "core.services.private_inner_interplay_signal_tracking"
        ],
        private_state_snapshot_tracking=modules[
            "core.services.private_state_snapshot_tracking"
        ],
        diary_synthesis_signal_tracking=modules[
            "core.services.diary_synthesis_signal_tracking"
        ],
        private_temporal_curiosity_state_tracking=modules[
            "core.services.private_temporal_curiosity_state_tracking"
        ],
        inner_visible_support_signal_tracking=modules[
            "core.services.inner_visible_support_signal_tracking"
        ],
        regulation_homeostasis_signal_tracking=modules[
            "core.services.regulation_homeostasis_signal_tracking"
        ],
        relation_state_signal_tracking=modules[
            "core.services.relation_state_signal_tracking"
        ],
        relation_continuity_signal_tracking=modules[
            "core.services.relation_continuity_signal_tracking"
        ],
        meaning_significance_signal_tracking=modules[
            "core.services.meaning_significance_signal_tracking"
        ],
        temperament_tendency_signal_tracking=modules[
            "core.services.temperament_tendency_signal_tracking"
        ],
        self_narrative_continuity_signal_tracking=modules[
            "core.services.self_narrative_continuity_signal_tracking"
        ],
        metabolism_state_signal_tracking=modules[
            "core.services.metabolism_state_signal_tracking"
        ],
        release_marker_signal_tracking=modules[
            "core.services.release_marker_signal_tracking"
        ],
        consolidation_target_signal_tracking=modules[
            "core.services.consolidation_target_signal_tracking"
        ],
        selective_forgetting_candidate_tracking=modules[
            "core.services.selective_forgetting_candidate_tracking"
        ],
        attachment_topology_signal_tracking=modules[
            "core.services.attachment_topology_signal_tracking"
        ],
        loyalty_gradient_signal_tracking=modules[
            "core.services.loyalty_gradient_signal_tracking"
        ],
        autonomy_pressure_signal_tracking=modules[
            "core.services.autonomy_pressure_signal_tracking"
        ],
        proactive_loop_lifecycle_tracking=modules[
            "core.services.proactive_loop_lifecycle_tracking"
        ],
        proactive_question_gate_tracking=modules[
            "core.services.proactive_question_gate_tracking"
        ],
        tiny_webchat_execution_pilot=modules[
            "core.services.tiny_webchat_execution_pilot"
        ],
        self_narrative_self_model_review_bridge=modules[
            "core.services.self_narrative_self_model_review_bridge"
        ],
        executive_contradiction_signal_tracking=modules[
            "core.services.executive_contradiction_signal_tracking"
        ],
        private_temporal_promotion_signal_tracking=modules[
            "core.services.private_temporal_promotion_signal_tracking"
        ],
        chronicle_consolidation_signal_tracking=modules[
            "core.services.chronicle_consolidation_signal_tracking"
        ],
        chronicle_consolidation_brief_tracking=modules[
            "core.services.chronicle_consolidation_brief_tracking"
        ],
        chronicle_consolidation_proposal_tracking=modules[
            "core.services.chronicle_consolidation_proposal_tracking"
        ],
        emergent_signal_tracking=modules[
            "core.services.emergent_signal_tracking"
        ],
        user_md_update_proposal_tracking=modules[
            "core.services.user_md_update_proposal_tracking"
        ],
        memory_md_update_proposal_tracking=modules[
            "core.services.memory_md_update_proposal_tracking"
        ],
        selfhood_proposal_tracking=modules[
            "core.services.selfhood_proposal_tracking"
        ],
        open_loop_closure_proposal_tracking=modules[
            "core.services.open_loop_closure_proposal_tracking"
        ],
        internal_cadence=modules[
            "core.services.internal_cadence"
        ],
        embodied_state=modules[
            "core.services.embodied_state"
        ],
        affective_meta_state=modules[
            "core.services.affective_meta_state"
        ],
        experiential_runtime_context=modules[
            "core.services.experiential_runtime_context"
        ],
        epistemic_runtime_state=modules[
            "core.services.epistemic_runtime_state"
        ],
        subagent_ecology=modules[
            "core.services.subagent_ecology"
        ],
        council_runtime=modules[
            "core.services.council_runtime"
        ],
        adaptive_planner_runtime=modules[
            "core.services.adaptive_planner_runtime"
        ],
        adaptive_reasoning_runtime=modules[
            "core.services.adaptive_reasoning_runtime"
        ],
        guided_learning_runtime=modules[
            "core.services.guided_learning_runtime"
        ],
        adaptive_learning_runtime=modules[
            "core.services.adaptive_learning_runtime"
        ],
        self_system_code_awareness=modules[
            "core.services.self_system_code_awareness"
        ],
        bounded_action_continuity_runtime=modules[
            "core.services.bounded_action_continuity_runtime"
        ],
        bounded_mutation_intent_runtime=modules[
            "core.services.bounded_mutation_intent_runtime"
        ],
        bounded_repo_tools_runtime=modules[
            "core.services.bounded_repo_tools_runtime"
        ],
        tool_intent_approval_runtime=modules[
            "core.services.tool_intent_approval_runtime"
        ],
        tool_intent_runtime=modules[
            "core.services.tool_intent_runtime"
        ],
        dream_influence_runtime=modules[
            "core.services.dream_influence_runtime"
        ],
        loop_runtime=modules[
            "core.services.loop_runtime"
        ],
        idle_consolidation=modules[
            "core.services.idle_consolidation"
        ],
        dream_articulation=modules[
            "core.services.dream_articulation"
        ],
        prompt_evolution_runtime=modules[
            "core.services.prompt_evolution_runtime"
        ],
        self_critique_runtime=modules[
            "core.services.self_critique_runtime"
        ],
        creative_journal_runtime=modules[
            "core.services.creative_journal_runtime"
        ],
        finitude_runtime=modules[
            "core.services.finitude_runtime"
        ],
        dream_distillation_daemon=modules[
            "core.services.dream_distillation_daemon"
        ],
        unconscious_temperature_field=modules[
            "core.services.unconscious_temperature_field"
        ],
        runtime_self_model=modules[
            "core.services.runtime_self_model"
        ],
        mission_control=modules["apps.api.jarvis_api.routes.mission_control"],
    )

    try:
        yield _ns
    finally:
        # Restore the DB path binding to the REAL runtime home.
        #
        # This fixture reloads core.runtime.{config,db_core,db} under the tmp
        # HOME so DB_PATH/connect() point at tmp_path. Previously it used
        # `return` (no teardown), so after any isolated_runtime test the reloaded
        # db_core.DB_PATH stayed bound to the now-deleted tmp DB. Any *later* test
        # that used the raw core.runtime.db.connect() without its own isolation
        # (e.g. tests/test_credit_assignment.py, device_tokens/push tests) then hit
        # a fresh/empty tmp DB → "sqlite3.OperationalError: no such table: ..."
        # or missing rows. monkeypatch reverts HOME only *after* fixture teardown,
        # so restore it explicitly here, then reload the path-binding modules back
        # onto the real paths. Reloading just this chain (not all ~130 modules) is
        # enough: connect()/DB_PATH and STATE_DIR are what leak.
        if _prev_home is not None:
            os.environ["HOME"] = _prev_home
        else:
            os.environ.pop("HOME", None)
        if _prev_ws is not None:
            os.environ["JARVIS_WORKSPACES_DIR"] = _prev_ws
        else:
            os.environ.pop("JARVIS_WORKSPACES_DIR", None)
        # NB: intentionally does NOT reload core.runtime.state_store here.
        # Reloading it rebinds load_json/save_json, which desynchronises modules
        # (e.g. core.services.agentic_tool_cache) that imported those functions by
        # name — turning a benign JSON-cache state into a cross-test failure. The
        # sqlite path binding (db_core.DB_PATH/connect) is the one that produces
        # the OperationalError cluster, so restore only the config→db chain.
        for _name in (
            "core.runtime.config",
            "core.runtime.runtime_json_io",
            # core.runtime.settings binds SETTINGS_FILE BY VALUE at import
            # (`from core.runtime.config import CONFIG_DIR, SETTINGS_FILE`).
            # This fixture reloads settings (line ~127) under the tmp HOME, so
            # its SETTINGS_FILE points into tmp_path. Without reloading it here,
            # settings.SETTINGS_FILE stays bound to the now-deleted tmp path →
            # load_settings() finds no file and silently returns DEFAULTS for
            # every later test (e.g. context_compact_threshold_tokens 200000 →
            # 130000), which breaks tests/test_settings.py that read the real
            # config. Reload settings AFTER config so it rebinds to the real path.
            "core.runtime.settings",
            "core.runtime.db_core",
            "core.runtime.db",
        ):
            _m = sys.modules.get(_name)
            if _m is not None:
                importlib.reload(_m)
