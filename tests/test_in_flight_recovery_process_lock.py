from __future__ import annotations

import multiprocessing

from core.runtime import state_store
from core.services import in_flight_runs as ifr


def _claim(owner: str, gate, output) -> None:
    gate.wait()
    output.put(bool(ifr.claim_due_recovery(owner=owner)))


def test_cross_process_claim_has_exactly_one_winner(tmp_path, monkeypatch):
    monkeypatch.setattr(state_store, "_STATE_DIR", tmp_path)
    ifr.mark_started(run_id="r1", session_id="s1", user_message="continue")
    ifr.settle_recovering("r1", reason="shutdown")

    context = multiprocessing.get_context("fork")
    gate = context.Event()
    output = context.Queue()
    processes = [
        context.Process(target=_claim, args=(f"{index}:1", gate, output))
        for index in range(2)
    ]
    for process in processes:
        process.start()
    gate.set()
    winners = [output.get(timeout=5) for _ in processes]
    for process in processes:
        process.join(timeout=5)
        assert process.exitcode == 0

    assert winners.count(True) == 1
    assert winners.count(False) == 1
