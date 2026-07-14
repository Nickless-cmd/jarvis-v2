#!/usr/bin/env python
"""Fase 6 Task 8 — the jarvis-code migration-trigger gate.

Runs the acceptance harness across BOTH repos via subprocess (never imports
jarvis-code into jarvis-v2 or vice versa — jarvis-code cannot import core.*
and this script must not either), evaluates the §9 acceptance criteria
against a numeric bar, and emits a single go/no-go verdict.

Run:
    /opt/conda/envs/ai/bin/python scripts/acceptance/migration_gate.py
    /opt/conda/envs/ai/bin/python scripts/acceptance/migration_gate.py --self-test

Exit code: 0 iff go=True (all four §9 criteria pass); 1 otherwise, with the
failing criteria named on stdout and in verdict.json.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PY = "/opt/conda/envs/ai/bin/python"
JARVIS_V2_ROOT = Path(__file__).resolve().parents[2]
JARVIS_CODE_ROOT = Path("/home/bs/jarvis-code")
_SUBPROCESS_TIMEOUT_S = 300


def _run_pytest(cwd: Path, args: list[str], label: str) -> dict:
    t0 = time.monotonic()
    try:
        proc = subprocess.run(
            [PY, "-m", "pytest", *args, "-o", "addopts=", "-q"],
            cwd=str(cwd), capture_output=True, text=True, timeout=_SUBPROCESS_TIMEOUT_S)
        ok = proc.returncode == 0
        tail_out = "\n".join(proc.stdout.splitlines()[-15:])
        tail_err = "\n".join(proc.stderr.splitlines()[-15:])
    except subprocess.TimeoutExpired:
        ok, tail_out, tail_err = False, "", "TIMEOUT"
    return {"label": label, "ok": ok, "duration_s": round(time.monotonic() - t0, 2),
           "stdout_tail": tail_out, "stderr_tail": tail_err}


def _run_script(cwd: Path, args: list[str], label: str) -> dict:
    t0 = time.monotonic()
    try:
        proc = subprocess.run([PY, *args], cwd=str(cwd), capture_output=True, text=True,
                              timeout=_SUBPROCESS_TIMEOUT_S)
        ok = proc.returncode == 0
        tail_out = "\n".join(proc.stdout.splitlines()[-20:])
    except subprocess.TimeoutExpired:
        ok, tail_out = False, "TIMEOUT"
    return {"label": label, "ok": ok, "duration_s": round(time.monotonic() - t0, 2),
           "stdout_tail": tail_out}


_NUMERIC_BAR_SNIPPET = """
import sys, json, random
sys.path.insert(0, ".")
from tests.faults.test_fault_fuzz import _run_with_timeout, _is_silent_empty, N
from tests.faults.fault_library import random_fault_sequence
from tests.faults.mock_provider import no_orphan_pairs

silent = hangs = orphan = 0
for seed in range(N):
    rng = random.Random(seed * 7919 + 1)
    n_faults = rng.randint(1, 4)
    fault_names = random_fault_sequence(seed=seed, n=n_faults)
    result, provider, loop, hung = _run_with_timeout(fault_names)
    if hung:
        hangs += 1
    if _is_silent_empty(result):
        silent += 1
    if not no_orphan_pairs(loop.messages):
        orphan += 1
print(json.dumps({"silent_empty": silent, "hangs": hangs, "orphan_400": orphan, "n": N}))
"""


def _compute_numeric_bar() -> dict:
    """Runs the SAME N=100 fuzz aggregation the committed pytest regression
    (tests/faults/test_fault_fuzz.py) locks in, but reports the exact
    per-category counts rather than a single pass/fail — the §9.1 bar is
    0/0/0, not just 'the test suite was green'."""
    try:
        proc = subprocess.run([PY, "-c", _NUMERIC_BAR_SNIPPET], cwd=str(JARVIS_CODE_ROOT),
                              capture_output=True, text=True, timeout=_SUBPROCESS_TIMEOUT_S)
        if proc.returncode != 0:
            return {"silent_empty": -1, "hangs": -1, "orphan_400": -1, "n": 0,
                    "error": proc.stderr[-500:]}
        return json.loads(proc.stdout.strip().splitlines()[-1])
    except Exception as exc:  # noqa: BLE001
        return {"silent_empty": -1, "hangs": -1, "orphan_400": -1, "n": 0, "error": str(exc)}


def run_suites() -> dict:
    results: dict[str, dict] = {}
    results["client_fault_injection"] = _run_pytest(
        JARVIS_CODE_ROOT, ["tests/faults/test_fault_injection.py"],
        "client fault-injection — 7 named fault classes")
    results["client_fault_fuzz"] = _run_pytest(
        JARVIS_CODE_ROOT, ["tests/faults/test_fault_fuzz.py"],
        "client fault-fuzz — N=100 numeric bar")
    results["server_fault_injection"] = _run_pytest(
        JARVIS_V2_ROOT, ["tests/faults/test_agent_step_faults.py"],
        "server fault-injection — O1 envelope, A6, A8")
    results["multi_user_scoping"] = _run_pytest(
        JARVIS_V2_ROOT, ["tests/multi_user/test_agent_step_scoping.py"],
        "multi-user scoping on /v1/agent/step")
    results["security_floor"] = _run_pytest(
        JARVIS_CODE_ROOT, ["tests/test_security_floor_client.py"],
        "security floor (client) — 6 named §9.4 invariants")
    results["e2e_devtask"] = _run_script(
        JARVIS_CODE_ROOT, ["tests/e2e_devtask/run_acceptance.py"],
        "e2e multi-step dev-task (read→skill_gate→plan→dispatch→edit→test→remember)")
    results["numeric_bar"] = _compute_numeric_bar()
    return results


def evaluate(results: dict) -> dict:
    """Pure function: results dict -> verdict dict. No subprocess/IO here —
    keeps this testable in --self-test with a stubbed results dict."""
    nb = results.get("numeric_bar", {})
    numeric_bar_ok = (nb.get("silent_empty") == 0 and nb.get("hangs") == 0
                      and nb.get("orphan_400") == 0 and nb.get("n", 0) > 0)

    substrate_ui_free = bool(results.get("client_fault_injection", {}).get("ok"))
    server_envelope_ok = bool(results.get("server_fault_injection", {}).get("ok"))
    per_user_scoped = bool(results.get("multi_user_scoping", {}).get("ok"))
    security_floor = bool(results.get("security_floor", {}).get("ok"))
    e2e_passed = bool(results.get("e2e_devtask", {}).get("ok"))

    # §9's four acceptance criteria (docs/superpowers/specs/2026-07-14-jarvis-code-migration-checklist.md):
    criteria = {
        "1_fault_injection_harness_green": substrate_ui_free and server_envelope_ok,
        "1_numeric_bar_0_0_0_over_n100": numeric_bar_ok,
        "2_e2e_devtask_passed": e2e_passed,
        "3_not_blind_lane": server_envelope_ok,  # O1 envelope spies (Task 4) prove this
        "4_security_floor_active": security_floor and per_user_scoped,
    }
    failing = [k for k, v in criteria.items() if not v]
    go = len(failing) == 0

    return {
        "go": go,
        "substrate_ui_free": substrate_ui_free,
        "per_user_scoped": per_user_scoped,
        "security_floor": security_floor,
        "numeric_bar": {"silent_empty": nb.get("silent_empty"), "hangs": nb.get("hangs"),
                        "orphan_400": nb.get("orphan_400"), "n": nb.get("n")},
        "e2e_passed": e2e_passed,
        "criteria": criteria,
        "failing_criteria": failing,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _self_test() -> int:
    """Stubbed suite-runner asserting the verdict logic itself, without
    running any real subprocess — go=False when ANY counter is nonzero or
    any suite failed; go=True only when everything is clean."""
    all_green = {
        "client_fault_injection": {"ok": True}, "server_fault_injection": {"ok": True},
        "multi_user_scoping": {"ok": True}, "security_floor": {"ok": True},
        "e2e_devtask": {"ok": True},
        "numeric_bar": {"silent_empty": 0, "hangs": 0, "orphan_400": 0, "n": 100},
    }
    v = evaluate(all_green)
    assert v["go"] is True, f"expected go=True on all-green input, got {v}"

    one_silent = dict(all_green, numeric_bar={"silent_empty": 1, "hangs": 0, "orphan_400": 0, "n": 100})
    v = evaluate(one_silent)
    assert v["go"] is False and "1_numeric_bar_0_0_0_over_n100" in v["failing_criteria"], v

    one_hang = dict(all_green, numeric_bar={"silent_empty": 0, "hangs": 1, "orphan_400": 0, "n": 100})
    assert evaluate(one_hang)["go"] is False

    one_orphan = dict(all_green, numeric_bar={"silent_empty": 0, "hangs": 0, "orphan_400": 1, "n": 100})
    assert evaluate(one_orphan)["go"] is False

    e2e_failed = dict(all_green, e2e_devtask={"ok": False})
    v = evaluate(e2e_failed)
    assert v["go"] is False and "2_e2e_devtask_passed" in v["failing_criteria"], v

    security_failed = dict(all_green, security_floor={"ok": False})
    v = evaluate(security_failed)
    assert v["go"] is False and "4_security_floor_active" in v["failing_criteria"], v

    scoping_failed = dict(all_green, multi_user_scoping={"ok": False})
    v = evaluate(scoping_failed)
    assert v["go"] is False and "4_security_floor_active" in v["failing_criteria"], v

    empty_bar = dict(all_green, numeric_bar={})
    assert evaluate(empty_bar)["go"] is False, "an empty/missing numeric_bar must never read as passing"

    print("--self-test: all verdict-logic assertions PASSED")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true",
                        help="verify the verdict logic against a stubbed results dict "
                             "(no real suites run)")
    parser.add_argument("--out", default=str(JARVIS_V2_ROOT / "verdict.json"),
                        help="path to write verdict.json")
    args = parser.parse_args()

    if args.self_test:
        return _self_test()

    print("migration_gate: running acceptance suites (client=jarvis-code, server=jarvis-v2)...")
    results = run_suites()
    for key, r in results.items():
        if "ok" in r:
            print(f"  [{'PASS' if r['ok'] else 'FAIL'}] {r.get('label', key)} ({r.get('duration_s', '?')}s)")
    verdict = evaluate(results)
    verdict["_raw_results"] = results

    Path(args.out).write_text(json.dumps(verdict, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nverdict written to {args.out}")
    print(f"GO: {verdict['go']}")
    if not verdict["go"]:
        print(f"failing criteria: {verdict['failing_criteria']}")
    print(f"numeric_bar: {verdict['numeric_bar']}")
    return 0 if verdict["go"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
