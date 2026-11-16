"""Real-process coverage for durable, session-bound recovery claims.

The workers in this module are deliberately launched as fresh interpreters.
They share an isolated on-disk SQLite database and recovery journal, but no
Python module state.  In particular, ``db_core.DB_PATH`` is patched in every
worker before database initialization; patching ``core.runtime.db.DB_PATH``
alone does not affect ``connect()``.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import time

PYTHON = "/home/bs/miniconda3/envs/ai/bin/python3"
REPO_ROOT = Path(__file__).resolve().parents[1]
THIS_FILE = Path(__file__).resolve()


def _worker_env(tmp_path: Path) -> tuple[dict[str, str], Path, Path]:
    home = tmp_path / "home"
    db_path = tmp_path / "shared" / "jarvis.db"
    home.mkdir(parents=True, exist_ok=True)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(
        {
            "HOME": str(home),
            "JARVIS_WORKSPACES_DIR": str(tmp_path / "workspaces"),
            "JARVIS_PROCESS_TEST_DB": str(db_path),
            "JARVIS_DB_NOPOOL": "1",
            "PYTHONPATH": str(REPO_ROOT),
        }
    )
    return env, home, db_path


def _run_worker(env: dict[str, str], *args: str, check: bool = True):
    return subprocess.run(
        [PYTHON, str(THIS_FILE), "--worker", *args],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=15,
        check=check,
    )


def _json_output(completed: subprocess.CompletedProcess[str]) -> dict:
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    assert lines, completed.stderr
    return json.loads(lines[-1])


def test_wake_survives_hard_restart_and_expired_claim_is_recovered_once(tmp_path):
    env, home, db_path = _worker_env(tmp_path)
    task_id = "wake-hard-restart"

    staged = _run_worker(env, "stage-crash", task_id, check=False)
    assert staged.returncode == 23, staged.stderr
    assert db_path.is_file(), "worker must initialize the explicitly isolated DB"
    assert (home / ".jarvis-v2/state/in_flight_runs.json").is_file()

    claim_result = tmp_path / "claim-before-crash.json"
    crashed = _run_worker(
        env, "claim-crash", task_id, "dead-owner", str(claim_result), check=False
    )
    assert crashed.returncode == 24, crashed.stderr
    first = json.loads(claim_result.read_text(encoding="utf-8"))
    assert first["task_id"] == task_id
    assert first["recovery_owner"] == "dead-owner"
    assert first["recovery_generation"] == 1

    blocked = _json_output(_run_worker(env, "claim", "other-owner", "1"))
    assert blocked == {"claim": None}, "a live lease must exclude another owner"

    time.sleep(1.1)
    recovered = _json_output(_run_worker(env, "dispatch", "restart-owner"))
    assert recovered == {
        "claimed": task_id,
        "generation": 2,
        "released": 0,
        "run_id": "restarted-visible-run",
        "started": 1,
    }

    duplicate = _json_output(_run_worker(env, "claim", "late-owner", "60"))
    assert duplicate == {"claim": None}, "the dispatched intention must not be taken twice"


def test_multi_worker_claim_race_has_exactly_one_winner_per_iteration(tmp_path):
    env, _home, db_path = _worker_env(tmp_path)
    iterations = 12
    worker_count = 4
    task_ids = [f"wake-race-{iteration:02d}" for iteration in range(iterations)]
    duplicates: list[tuple[int, list[str]]] = []
    for iteration, task_id in enumerate(task_ids):
        staged = _json_output(_run_worker(env, "stage-many", task_id))
        assert staged == {"db_path": str(db_path), "staged": 1}
        gate = tmp_path / f"race-{iteration:02d}.gate"
        processes = [
            subprocess.Popen(
                [PYTHON, str(THIS_FILE), "--worker", "race-claim", str(gate),
                 f"worker-{iteration:02d}-{worker}"],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            for worker in range(worker_count)
        ]
        gate.touch()
        results = []
        for process in processes:
            stdout, stderr = process.communicate(timeout=15)
            assert process.returncode == 0, stderr
            results.append(json.loads([line for line in stdout.splitlines() if line][-1]))

        winners = [result["task_id"] for result in results if result["task_id"]]
        if winners != [task_id]:
            duplicates.append((iteration, winners))

    assert duplicates == [], (
        f"each of {iterations} races must have exactly one winner; failures={duplicates}"
    )


def _bootstrap_worker(*, initialize_db: bool = False):
    db_path = Path(os.environ["JARVIS_PROCESS_TEST_DB"])
    from core.runtime import db as db_mod
    from core.runtime import db_core

    # connect() and init_db() resolve this module-global, not db.DB_PATH.
    db_core.DB_PATH = db_path
    db_mod.DB_PATH = db_path
    if initialize_db:
        db_mod.init_db()
    return db_path


def _worker_main(argv: list[str]) -> None:
    action, *args = argv
    initialize = action in {"stage-crash", "stage-many"}
    db_path = _bootstrap_worker(initialize_db=initialize)
    from core.services import agent_wake_intentions as wakes
    from core.services import in_flight_runs as in_flight

    if action == "stage-crash":
        task_id = args[0]
        wakes.stage_wake(
            task_id=task_id,
            session_id="session-process-restart",
            owner_user_id="owner-process-test",
            message="continue after a hard process restart",
        )
        os._exit(23)

    if action == "stage-many":
        for task_id in args:
            wakes.stage_wake(
                task_id=task_id,
                session_id=f"session-{task_id}",
                owner_user_id="owner-process-test",
                message=f"continue {task_id}",
            )
        print(json.dumps({"db_path": str(db_path), "staged": len(args)}), flush=True)
        return

    if action == "claim-crash":
        task_id, owner, result_path = args
        claim = in_flight.claim_due_recovery(owner=owner, lease_seconds=1)
        assert claim is not None and claim["task_id"] == task_id
        Path(result_path).write_text(json.dumps(claim), encoding="utf-8")
        os._exit(24)

    if action == "claim":
        owner, lease_seconds = args
        claim = in_flight.claim_due_recovery(
            owner=owner, lease_seconds=float(lease_seconds)
        )
        print(json.dumps({"claim": claim}), flush=True)
        return

    if action == "dispatch":
        owner = args[0]
        from core.services import visible_run_recovery_dispatcher as dispatcher
        from core.services.visible_runs_sections import detached_run

        dispatcher.LEASE_SECONDS = 60
        detached_run.start_user_run_detached = lambda **_kwargs: "restarted-visible-run"
        print(json.dumps(dispatcher.recover_due_once(owner=owner), sort_keys=True), flush=True)
        return

    if action == "race-claim":
        gate_path, owner = args
        deadline = time.monotonic() + 10
        while not Path(gate_path).exists():
            if time.monotonic() >= deadline:
                raise TimeoutError("race gate was not opened")
            time.sleep(0.002)
        claim = in_flight.claim_due_recovery(owner=owner, lease_seconds=60)
        print(json.dumps({"task_id": None if claim is None else claim["task_id"]}), flush=True)
        return

    raise ValueError(f"unknown worker action: {action}")


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] != "--worker":
        raise SystemExit("worker invocation required")
    _worker_main(sys.argv[2:])
