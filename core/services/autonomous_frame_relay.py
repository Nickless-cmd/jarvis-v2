"""Shared frame-log lifecycle for autonomous visible runs."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class AutonomousFrameRelay:
    """Publish one autonomous run to the authoritative v2 frame log.

    ``legacy_follow`` keeps the session-keyed follow buffer alive for older
    clients while ``run_event_log`` remains the authoritative replay source.
    """

    run_id: str
    session_id: str
    legacy_follow: bool = False
    _registered: bool = field(default=False, init=False)
    _finished: bool = field(default=False, init=False)

    def register(self) -> None:
        if self._registered:
            return
        from core.services import run_event_log

        run_event_log.create(self.run_id, self.session_id)
        if self.legacy_follow:
            from core.services.run_follow import begin_follow

            begin_follow(self.session_id, self.run_id)
        self._registered = True

    def publish(self, frame: str) -> None:
        if not self._registered or self._finished:
            return
        from core.services import run_event_log

        run_event_log.append(self.run_id, frame)
        if self.legacy_follow:
            from core.services.run_follow import publish_follow_frame

            publish_follow_frame(self.session_id, frame)

    def finish(self) -> None:
        if not self._registered or self._finished:
            return
        from core.services import run_event_log

        run_event_log.mark_done(self.run_id)
        if self.legacy_follow:
            from core.services.run_follow import end_follow

            end_follow(self.session_id)
        try:
            run_event_log.prune()
        finally:
            self._finished = True
