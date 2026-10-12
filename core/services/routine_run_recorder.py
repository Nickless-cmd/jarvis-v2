"""Session-neutral append-only recorder for observable Routine run events."""
from __future__ import annotations

from typing import Mapping

from core.runtime import db_routines


class RoutineRunRecorder:
    def append(
        self, run_id: str, *, kind: str, payload: Mapping[str, object],
        terminal: bool = False, event_id: str | None = None,
        generation: int | None = None,
    ) -> dict:
        return db_routines.append_run_event(
            run_id=run_id,
            kind=kind,
            payload=payload,
            terminal=terminal,
            event_id=event_id,
            expected_generation=generation,
        )

    def list(self, run_id: str, *, decrypt_for: str | None = None) -> list[dict]:
        return db_routines.read_run_events(run_id, decrypt_for=decrypt_for)
