from __future__ import annotations


def _import_modules():
    runtime_tasks = __import__(
        "core.services.runtime_tasks",
        fromlist=["create_task"],
    )
    task_worker = __import__(
        "core.services.task_worker",
        fromlist=["claim_next_task"],
    )
    return runtime_tasks, task_worker


def test_claim_next_task_returns_highest_priority_queued(isolated_runtime) -> None:
    runtime_tasks, task_worker = _import_modules()

    runtime_tasks.create_task(
        kind="generic", goal="low one", origin="test", priority="low"
    )
    high = runtime_tasks.create_task(
        kind="generic", goal="high one", origin="test", priority="high"
    )
    runtime_tasks.create_task(
        kind="generic", goal="med one", origin="test", priority="medium"
    )

    claimed = task_worker.claim_next_task()

    assert claimed is not None
    assert claimed["task_id"] == high["task_id"]
    assert claimed["status"] == "running"


def test_claim_next_task_returns_none_when_no_matching_kind(isolated_runtime) -> None:
    runtime_tasks, task_worker = _import_modules()
    runtime_tasks.create_task(
        kind="some-other-kind", goal="x", origin="test", priority="high"
    )

    claimed = task_worker.claim_next_task(
        kinds=("initiative-followup", "heartbeat-followup"),
    )

    assert claimed is None


def test_execute_task_marks_succeeded_on_known_kind(isolated_runtime) -> None:
    runtime_tasks, task_worker = _import_modules()
    task = runtime_tasks.create_task(
        kind="generic", goal="noop-test", origin="test", priority="low"
    )

    task_worker._execute_task(task)

    reloaded = runtime_tasks.get_task(task["task_id"])
    assert reloaded is not None
    assert reloaded["status"] == "succeeded"
    assert reloaded.get("result_summary")


def test_execute_task_marks_failed_on_unknown_kind(isolated_runtime) -> None:
    runtime_tasks, task_worker = _import_modules()
    task = runtime_tasks.create_task(
        kind="totally-unknown-kind", goal="x", origin="test", priority="low"
    )

    task_worker._execute_task(task)

    reloaded = runtime_tasks.get_task(task["task_id"])
    assert reloaded is not None
    assert reloaded["status"] == "failed"
    assert "unknown kind" in str(reloaded.get("result_summary") or "").lower()


def test_tick_processes_up_to_budget(isolated_runtime) -> None:
    runtime_tasks, task_worker = _import_modules()
    for i in range(5):
        runtime_tasks.create_task(
            kind="generic", goal=f"t{i}", origin="test", priority="medium"
        )

    result = task_worker.tick_task_worker(budget=3)

    assert result["processed"] == 3
    assert result["succeeded"] == 3
    assert result["failed"] == 0
    assert result["remaining_queued"] >= 2


def test_tick_handles_initiative_and_heartbeat_followup(isolated_runtime) -> None:
    """Followup-tasks bliver afviklet — men som `blocked`, ikke `succeeded`.

    ÆNDRET 1/11-2026: testen krævede tidligere `succeeded == 2`, hvilket pinnede
    den fejl den skulle værne imod. Målt: 5.776 initiative-followup-tasks stod
    som `succeeded` med en ren gentagelse af målet som resultat, og præcis 1
    havde et artefakt. En handler der kun videresender en instruks har ikke
    udført noget, og må ikke sige at den har.
    """
    runtime_tasks, task_worker = _import_modules()
    runtime_tasks.create_task(
        kind="initiative-followup",
        goal="check memory",
        origin="test",
        priority="high",
    )
    runtime_tasks.create_task(
        kind="heartbeat-followup",
        goal="no-valid-execution-candidate",
        origin="test",
        priority="high",
    )

    result = task_worker.tick_task_worker(budget=5)

    assert result["processed"] == 2
    assert result["blocked"] == 2, "followup-handlers har intet udført — de skal sige det"
    assert result["succeeded"] == 0
    assert result["failed"] == 0


def test_agency_bridge_repair_prepares_brief(monkeypatch) -> None:
    _, task_worker = _import_modules()
    saved = {}

    monkeypatch.setattr(task_worker, "load_json", lambda name, default: {})
    monkeypatch.setattr(task_worker, "save_json", lambda name, data: saved.update({name: data}))
    monkeypatch.setattr(
        task_worker,
        "_matching_agency_edge",
        lambda **kwargs: {
            "id": "executive-tools",
            "title": "Living Executive -> Tools",
            "target": "Living Executive -> Tools",
            "missing_markers": ["living_executive.tool_plan_proposed"],
        },
    )

    task = {
        "task_id": "task-agency",
        "kind": "agency_bridge_repair",
        "goal": "Turn executive recovery plans into runnable tool proposals.",
        "origin": "agency-cartographer",
        "scope": "Living Executive -> Tools",
        "priority": "high",
    }

    result = task_worker._handle_agency_bridge_repair(task)

    assert result["status"] == "blocked"
    assert result["artifact_ref"] == "state:agency_bridge_repair_briefs:task-agency"
    assert "awaiting approved implementation lane" in result["blocked_reason"]
    brief = saved["agency_bridge_repair_briefs"][task["task_id"]]
    assert brief["edge"]["id"] == "executive-tools"
    assert "core/services/living_executive.py" in brief["suggested_files"]


def test_observability_bridge_repair_prepares_brief(monkeypatch) -> None:
    _, task_worker = _import_modules()
    saved = {}

    monkeypatch.setattr(task_worker, "load_json", lambda name, default: {})
    monkeypatch.setattr(task_worker, "save_json", lambda name, data: saved.update({name: data}))

    task = {
        "task_id": "task-observe",
        "kind": "observability_bridge_repair",
        "goal": "Expose identity_composer in Mission Control.",
        "origin": "system-cartographer",
        "scope": "core/services/identity_composer.py",
        "priority": "medium",
    }

    result = task_worker._handle_observability_bridge_repair(task)

    assert result["status"] == "blocked"
    assert result["artifact_ref"] == "state:observability_bridge_repair_briefs:task-observe"
    brief = saved["observability_bridge_repair_briefs"][task["task_id"]]
    assert brief["service"] == "identity_composer"
    assert "core/services/identity_composer.py" in brief["suggested_files"]


def test_theater_refactor_prepares_brief(monkeypatch) -> None:
    _, task_worker = _import_modules()
    saved = {}

    monkeypatch.setattr(task_worker, "load_json", lambda name, default: {})
    monkeypatch.setattr(task_worker, "save_json", lambda name, data: saved.update({name: data}))
    monkeypatch.setattr(
        task_worker,
        "_matching_theater_file",
        lambda **kwargs: {
            "path": "core/services/cognitive_state_assembly.py",
            "risk_score": 250,
            "high_risk": 5,
        },
    )

    task = {
        "task_id": "task-theater",
        "kind": "theater_refactor",
        "goal": "Convert cognitive_state_assembly to appraisal state.",
        "origin": "theater-audit",
        "scope": "core/services/cognitive_state_assembly.py",
        "priority": "high",
    }

    result = task_worker._handle_theater_refactor(task)

    assert result["status"] == "blocked"
    assert result["artifact_ref"] == "state:theater_refactor_briefs:task-theater"
    brief = saved["theater_refactor_briefs"][task["task_id"]]
    assert brief["audit_file"]["risk_score"] == 250
    assert brief["refactor_contract"]["state_before_prose"] is True
    assert "core/services/cognitive_state_assembly.py" in brief["suggested_files"]


# ── brief-generatorerne må ikke foreslå filer der ikke findes ────────────────
#
# Målt 11/10-2026: alle tre generatorer foreslog
# `apps/ui/src/components/mission-control/AgencyMapTab.jsx` — en fil der blev
# revet ud 6/7-2026 sammen med hele web-UI'ets Mission Control (`b8c985510`,
# Fase E: «MC lever nu i Centralen/Central-CLI»). Hver brief pegede altså på en
# død sti, og intet fangede det: fire opgaver stod blokeret i fem måneder med et
# mål ingen kunne bygge.
#
# Den levende flade er API-routelaget: `build_*_surface()` defineres i
# `core/services/` og eksponeres som route i
# `apps/api/jarvis_api/routes/mission_control_introspection.py` (144
# surface-kald), som desk'ens cowork-zone læser gennem `/mc/*`.
#
# Vagten er testen: hver sti en generator foreslår skal findes på disken.


def test_brief_generatorerne_foreslaar_kun_filer_der_findes() -> None:
    """En brief der peger på en fil der ikke findes, sender en agent i ørkenen."""
    from pathlib import Path

    _, task_worker = _import_modules()
    repo_rod = Path(__file__).resolve().parents[1]

    forslag: list[str] = []
    forslag += task_worker._suggested_agency_files(
        scope="core/services/memory_emotional_context.py",
        edge={
            "id": "hidden-runtime-mc",
            "target": "Hidden Runtime -> Mission Control",
            "title": "Hidden Runtime -> Mission Control",
        },
    )
    forslag += task_worker._suggested_observability_files(
        scope="core/services/memory_emotional_context.py",
        service="memory_emotional_context",
    )
    forslag += task_worker._suggested_theater_files(
        scope="core/services/cognitive_state_assembly.py",
    )

    assert forslag, "generatorerne skal foreslå mindst én fil"
    manglende = sorted({p for p in forslag if not (repo_rod / p).exists()})
    assert manglende == [], f"briefene peger på filer der ikke findes: {manglende}"


# --- Regression: falsk heartbeat-claim + kind-drift (asg-3910bc0cdaaf4c61) ---

def test_heartbeat_saetter_aldrig_en_task_til_running(isolated_runtime, monkeypatch) -> None:
    """Heartbeat må observere, ikke claime: ingen task forlader `queued` her."""
    from pathlib import Path

    runtime_tasks, _ = _import_modules()
    import core.services.runtime_browser_body as rbb
    import core.services.runtime_hooks as rh
    import core.services.self_experiments as se
    from core.services.heartbeat_manage_runtime_work import execute_manage_runtime_work

    monkeypatch.setattr(rh, "dispatch_unhandled_hook_events", lambda limit=4: [])
    monkeypatch.setattr(rbb, "ensure_browser_body", lambda **kw: {"body_id": "b"})
    monkeypatch.setattr(se, "observe_recent_visible_runs_for_self_experiments",
                        lambda limit=6: {"observed": 0})
    monkeypatch.setattr(se, "materialize_learning_curriculum_tasks",
                        lambda **kw: {"created": 0, "task_ids": []})
    t = runtime_tasks.create_task(kind="generic", goal="g", origin="test")

    execute_manage_runtime_work(tick_id="t1", workspace_dir=Path("/tmp"))

    assert runtime_tasks.get_task(t["task_id"])["status"] == "queued"


def test_running_har_altid_lease_og_andre_statusser_ingen(isolated_runtime) -> None:
    runtime_tasks, _ = _import_modules()
    t = runtime_tasks.create_task(kind="generic", goal="g", origin="test")
    # Selv en sti der blot sætter `running` får en lease (ingen evig running).
    r = runtime_tasks.update_task(t["task_id"], status="running")
    assert r["lease_expires_at"]
    r = runtime_tasks.update_task(t["task_id"], status="succeeded")
    assert r["lease_expires_at"] == ""


def test_reaper_requeuer_udloebet_og_leaseloes_running(isolated_runtime) -> None:
    from core.runtime import db as runtime_db

    runtime_tasks, task_worker = _import_modules()
    stale = runtime_tasks.create_task(kind="generic", goal="stale", origin="test")
    legacy = runtime_tasks.create_task(kind="generic", goal="legacy", origin="test")
    fresh = runtime_tasks.create_task(kind="generic", goal="fresh", origin="test")
    for t in (stale, legacy, fresh):
        runtime_tasks.update_task(t["task_id"], status="running")
    with runtime_db.connect() as conn:
        conn.execute("UPDATE runtime_tasks SET lease_expires_at='2000-01-01T00:00:00+00:00' WHERE task_id=?",
                     (stale["task_id"],))
        conn.execute("UPDATE runtime_tasks SET lease_expires_at='' WHERE task_id=?",
                     (legacy["task_id"],))
        conn.commit()

    reaped = set(runtime_tasks.reap_expired_leases())

    assert reaped == {stale["task_id"], legacy["task_id"]}
    assert runtime_tasks.get_task(stale["task_id"])["status"] == "queued"
    assert runtime_tasks.get_task(legacy["task_id"])["status"] == "queued"
    assert runtime_tasks.get_task(fresh["task_id"])["status"] == "running"


def test_tick_reaper_foer_claim_efter_worker_crash(isolated_runtime) -> None:
    from core.runtime import db as runtime_db

    runtime_tasks, task_worker = _import_modules()
    t = runtime_tasks.create_task(kind="generic", goal="crash", origin="test")
    claimed = task_worker.claim_next_task()  # worker "dør" her — ingen execute
    assert claimed["status"] == "running"
    with runtime_db.connect() as conn:
        conn.execute("UPDATE runtime_tasks SET lease_expires_at='2000-01-01T00:00:00+00:00'")
        conn.commit()

    result = task_worker.tick_task_worker(budget=1)

    assert result["reaped"] == 1
    assert runtime_tasks.get_task(t["task_id"])["status"] == "succeeded"


def test_claim_er_atomisk_anden_claim_taber(isolated_runtime) -> None:
    runtime_tasks, _ = _import_modules()
    t = runtime_tasks.create_task(kind="generic", goal="g", origin="test")
    assert runtime_tasks.claim_task(t["task_id"], owner="a") is not None
    assert runtime_tasks.claim_task(t["task_id"], owner="b") is None
    assert runtime_tasks.get_task(t["task_id"])["owner"] == "a"


def test_claimable_kinds_afledt_af_handler_registret(isolated_runtime) -> None:
    _, task_worker = _import_modules()
    assert set(task_worker.claimable_kinds()) == set(task_worker._KIND_HANDLERS)
    assert "curriculum-focus" in task_worker.claimable_kinds()


def test_curriculum_focus_naar_terminal_tilstand_inden_ét_tick(isolated_runtime) -> None:
    runtime_tasks, task_worker = _import_modules()
    t = runtime_tasks.create_task(kind="curriculum-focus", goal="lær x", origin="test")

    task_worker.tick_task_worker(budget=1)

    got = runtime_tasks.get_task(t["task_id"])
    assert got["status"] in {"blocked", "succeeded"}
    assert got["status"] != "queued"


def test_curriculum_focus_sender_maal_til_autonom_bane(isolated_runtime, monkeypatch) -> None:
    """Læringsmålet skal MATERIALISERES, ikke bare markeres blocked.

    Målt 20/11-2026: otte læringsmål stod fast siden 30/10 fordi handleren pegede
    på en bane ingen kode startede. `succeeded` kræver derfor et født run.
    """
    import core.services.visible_autonomous_run as var

    runtime_tasks, task_worker = _import_modules()
    kald: list[dict] = []

    def _fake_start(message, **kw):
        kald.append({"message": message, **kw})
        return True

    monkeypatch.setattr(var, "start_autonomous_run", _fake_start)
    t = runtime_tasks.create_task(
        kind="curriculum-focus", goal="Undgå: afbryder sit eget svar", origin="test"
    )

    task_worker.tick_task_worker(budget=1)

    got = runtime_tasks.get_task(t["task_id"])
    assert got["status"] == "succeeded"
    assert got["artifact_ref"] == f"run:work:{t['task_id']}"
    assert len(kald) == 1
    assert "afbryder sit eget svar" in kald[0]["message"]
    assert kald[0]["origin"] == "work"


def test_curriculum_focus_blocked_naar_run_guard_afviser(isolated_runtime, monkeypatch) -> None:
    """Et afvist run må IKKE meldes som succes — det var 1/11-fejlen."""
    import core.services.visible_autonomous_run as var

    runtime_tasks, task_worker = _import_modules()
    monkeypatch.setattr(var, "start_autonomous_run", lambda *a, **k: False)
    t = runtime_tasks.create_task(kind="curriculum-focus", goal="lær y", origin="test")

    task_worker.tick_task_worker(budget=1)

    got = runtime_tasks.get_task(t["task_id"])
    assert got["status"] == "blocked"
    assert "run-guard" in (got["blocked_reason"] or "")


def test_curriculum_focus_blocked_naar_run_start_kaster(isolated_runtime, monkeypatch) -> None:
    import core.services.visible_autonomous_run as var

    runtime_tasks, task_worker = _import_modules()

    def _boom(*a, **k):
        raise RuntimeError("ingen bane")

    monkeypatch.setattr(var, "start_autonomous_run", _boom)
    t = runtime_tasks.create_task(kind="curriculum-focus", goal="lær z", origin="test")

    task_worker.tick_task_worker(budget=1)

    got = runtime_tasks.get_task(t["task_id"])
    assert got["status"] == "blocked"
    assert "run-start fejlede" in (got["blocked_reason"] or "")


def test_health_rapporterer_unclaimable_kinds(isolated_runtime) -> None:
    runtime_tasks, task_worker = _import_modules()
    runtime_tasks.create_task(kind="ingen-handler-kind", goal="x", origin="test")
    runtime_tasks.create_task(kind="generic", goal="y", origin="test")

    sig = task_worker.build_task_worker_surface()["signals"]

    assert sig["claimable_queued"] == 1
    assert sig["unclaimable_queued"] == 1
    assert sig["unclaimable_kinds"] == {"ingen-handler-kind": 1}


# --- RUN -> CONFIDENCE (20/11-2026) ----------------------------------------
def _pv_domaener() -> dict:
    import json

    from core.runtime.db_cognitive import get_latest_cognitive_personality_vector

    pv = get_latest_cognitive_personality_vector() or {}
    return json.loads(str(pv.get("confidence_by_domain") or "{}"))


def _koer_curriculum_med_callback(isolated_runtime, monkeypatch, *, scope, outcome, did_work):
    import core.services.visible_autonomous_run as var

    runtime_tasks, task_worker = _import_modules()
    monkeypatch.setattr(
        task_worker, "_run_did_work", lambda sid, goal, **kw: did_work
    )
    captured: dict = {}

    def _fake_start(message, **kw):
        captured.update(kw)
        return True

    monkeypatch.setattr(var, "start_autonomous_run", _fake_start)
    runtime_tasks.create_task(
        kind="curriculum-focus", goal="inspicér desktop-apps", origin="test", scope=scope
    )
    task_worker.tick_task_worker(budget=1)
    cb = captured.get("completion_callback")
    assert cb is not None, "koblingen mangler: ingen completion_callback sendt til runnet"
    cb(outcome=outcome, visible_run_id="r1", session_id="s1", error="")


def test_curriculum_run_opretter_manglende_domaene_og_loefter_ved_bevist_arbejde(
    isolated_runtime, monkeypatch
) -> None:
    _koer_curriculum_med_callback(
        isolated_runtime, monkeypatch,
        scope="desktop app inspection", outcome="completed", did_work=True,
    )
    d = _pv_domaener()
    assert d["desktop app inspection"] == 0.35  # 0.30 start + 0.05


def test_curriculum_run_uden_bevis_loefter_aldrig(isolated_runtime, monkeypatch) -> None:
    """Succeeded uden at noget blev gjort må ikke løfte noget (1/11-fejlen)."""
    _koer_curriculum_med_callback(
        isolated_runtime, monkeypatch,
        scope="desk render capabilities", outcome="completed", did_work=False,
    )
    assert _pv_domaener()["desk render capabilities"] == 0.3  # oprettet, ikke løftet


def test_curriculum_run_der_fejler_saenker(isolated_runtime, monkeypatch) -> None:
    _koer_curriculum_med_callback(
        isolated_runtime, monkeypatch,
        scope="desk render capabilities", outcome="failed", did_work=False,
    )
    assert _pv_domaener()["desk render capabilities"] == 0.27


def test_normaliseret_scope_loefter_og_saenker_stadig_paa_samme_noegle(
    isolated_runtime, monkeypatch
) -> None:
    from core.services.self_experiments import normaliser_fejl_til_domaene as n

    noegle = n("Afbrød sit eget svar midt i sætningen ('og den skal lukkes m")
    _koer_curriculum_med_callback(
        isolated_runtime, monkeypatch, scope=noegle, outcome="completed", did_work=True
    )
    assert _pv_domaener()[noegle] == 0.35
    # anden formulering af samme fejltype → samme nøgle, ingen ny støjnøgle
    noegle2 = n("Holder op midt i en sætning ('jeg skal vide om det er fronte")
    _koer_curriculum_med_callback(
        isolated_runtime, monkeypatch, scope=noegle2, outcome="failed", did_work=False
    )
    assert _pv_domaener()[noegle] == 0.32
    assert [k for k in _pv_domaener() if "midt" in k or "saetning" in k] == [noegle]


def test_bevis_porten_maaler_runnet_ikke_sessionen(isolated_runtime) -> None:
    """MÅLT 20/11-2026 — hvorfor «adherence-analyse» stod stille på 0.35.

    Den gamle port krævede at målet stod i en ``user``-række i sessionen.
    Målt i den levende base: **0 af 8.742 user-rækker** indeholdt nogensinde
    «LÆRINGSMÅL» — den autonome prompt bliver aldrig en brugerbesked. Porten
    returnerede derfor False hver gang, ``_confidence_delta`` gav 0.0, og
    domænet stod på 0.35 i alle 1.011 vektor-versioner. Tallet blev aldrig
    målt, kun arvet.

    Porten måles derfor på RUNNET: ``runtime_action_outcomes`` bærer run_id
    (1.963 distinkte runs, også autonome). Sessionen er delt mellem dagens
    runs og kan derfor ikke bruges som anker.
    """
    _runtime_tasks, task_worker = _import_modules()
    from core.runtime.db import connect

    def _outcome(run_id: str) -> None:
        with connect() as conn:
            conn.execute(
                "INSERT INTO runtime_action_outcomes"
                " (outcome_id, action_id, decision_mode, result_status, run_id, recorded_at)"
                " VALUES (?,?,?,?,?,?)",
                (f"o-{run_id}", "a1", "auto", "ok", run_id, "2026-11-20T00:00:00Z"),
            )

    def _svar(run_id: str, tekst: str) -> None:
        with connect() as conn:
            conn.execute(
                "INSERT INTO visible_runs"
                " (run_id, lane, provider, model, status, text_preview)"
                " VALUES (?,?,?,?,?,?)",
                (run_id, "visible", "ollama", "test", "completed", tekst),
            )

    # 1) intet spor overhovedet
    assert task_worker._run_did_work_from_outcomes("r-tom") is False

    # 2) værktøjskald, men intet svar
    _outcome("r-vaerktoej")
    assert task_worker._run_did_work_from_outcomes("r-vaerktoej") is False

    # 3) svar, men ingen værktøjer — «sluttede uden fejl» er ikke bevis (1/11-fejlen)
    _svar("r-svar", "noget tekst")
    assert task_worker._run_did_work_from_outcomes("r-svar") is False

    # 4) begge dele: bevis
    _outcome("r-bevis")
    _svar("r-bevis", "noget tekst")
    assert task_worker._run_did_work_from_outcomes("r-bevis") is True

    # 5) ankret på run_id — naboens arbejde i samme session krediterer ikke
    assert task_worker._run_did_work_from_outcomes("r-nabo") is False


def test_callbacken_sender_run_id_videre_til_bevis_porten(isolated_runtime, monkeypatch) -> None:
    """Uden run_id videre ville per-run-porten aldrig blive kaldt — ren teater."""
    _runtime_tasks, task_worker = _import_modules()
    set_metode: dict = {}

    def _fake_gate(sid, goal, *, run_id=""):
        set_metode["run_id"] = run_id
        return True

    monkeypatch.setattr(task_worker, "_run_did_work", _fake_gate)
    cb = task_worker._make_curriculum_completion_callback("adherence-analyse", "mål x")
    cb(outcome="completed", session_id="s1", visible_run_id="autonomous-abc")
    assert set_metode["run_id"] == "autonomous-abc"
