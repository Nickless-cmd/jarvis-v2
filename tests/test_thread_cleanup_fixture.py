from __future__ import annotations

import threading
import time


_DESCENDANT_DONE = threading.Event()


def test_thread_cleanup_tracks_descendants_started_during_teardown() -> None:
    """Fixture cleanup must also wait for children spawned by a test thread."""

    def child() -> None:
        time.sleep(0.2)
        _DESCENDANT_DONE.set()

    def parent() -> None:
        time.sleep(0.05)
        threading.Thread(target=child, name="test-cleanup-child", daemon=True).start()

    threading.Thread(target=parent, name="test-cleanup-parent", daemon=True).start()


def test_previous_tests_descendant_finished_before_next_test() -> None:
    assert _DESCENDANT_DONE.is_set(), (
        "the thread cleanup fixture returned before a descendant thread finished"
    )
