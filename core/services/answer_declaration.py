"""A conservative veto for answer markers attached to work announcements.

This never discovers an answer from prose. A marker is still required; a
small lexical grammar only rejects contradictory first-person work openings.
"""
from __future__ import annotations

import re

from core.services.code_answer_boundary import AnswerMarkerStream

_DA_ACTIONS = ('måle', 'tjekke', 'undersøge', 'læse', 'verificere', 'teste',
               'kontrollere', 'kigge', 'bygge', 'rette', 'inspicere')
_EN_ACTIONS = ('check', 'inspect', 'verify', 'test', 'measure', 'read', 'investigate', 'build', 'fix')
_WORK_OPENINGS = tuple(
    lead + action
    for leads, actions in (
        (('nu skal jeg ', 'nu vil jeg ', 'jeg skal ', 'jeg vil ', 'lad mig ',
          'først skal jeg ', 'først vil jeg '), _DA_ACTIONS),
        (("let me ", "i'll ", 'i will ', 'i need to ', "first i'll ", "first, i'll "), _EN_ACTIONS),
    )
    for lead in leads for action in actions
)


def declaration_intent(text: str, *, final: bool = False) -> str:
    """Return work/answer/pending; only explicit work openings are vetoed."""
    prefix = re.sub(r'\s+', ' ', text.lstrip().lstrip('*_').lstrip()).casefold()
    for opening in _WORK_OPENINGS:
        if prefix.startswith(opening) and (len(prefix) > len(opening)
                and not prefix[len(opening)].isalpha() or final and prefix == opening):
            return 'work'
    if not final and (not prefix or any(opening.startswith(prefix) or prefix == opening
                                        for opening in _WORK_OPENINGS)):
        return 'pending'
    return 'answer'


class AnswerDeclarationStream:
    """Validate before emitting a boundary, independently of delta chunking."""

    def __init__(self) -> None:
        self.marker = AnswerMarkerStream(deduplicate=False)
        self.accepted = False
        self.candidate: str | None = None
        self.rejected = 0

    def _resolve(self, *, final: bool = False) -> list[tuple[str, str]]:
        if self.candidate is None:
            return []
        intent = declaration_intent(self.candidate, final=final)
        if intent == 'pending':
            return []
        text, self.candidate = self.candidate, None
        if intent == 'work':
            self.rejected += 1
            return [('text', text)]
        if not text.strip():
            return [('text', text)]
        self.accepted = True
        return [('answer_start', ''), ('text', text)]

    def _consume(self, parts: list[tuple[str, str]]) -> list[tuple[str, str]]:
        out: list[tuple[str, str]] = []
        for kind, value in parts:
            if kind == 'answer_start':
                if not self.accepted:
                    out.extend(self._resolve(final=True))
                    if not self.accepted:
                        self.candidate = ''
            elif self.candidate is not None:
                self.candidate += value
                out.extend(self._resolve())
            else:
                out.append((kind, value))
        return out

    def feed(self, text: str) -> list[tuple[str, str]]:
        """Pass ordinary text through; inspect only the opening after a marker."""
        return self._consume(self.marker.feed(text))

    def flush(self) -> list[tuple[str, str]]:
        """Release an incomplete candidate at a round or stream boundary."""
        return self._consume(self.marker.flush()) + self._resolve(final=True)

    def reset_round(self) -> None:
        """Reset lexical line/fence state, retaining the accepted turn boundary."""
        self.marker.line_start = True
        self.marker.line_prefix = ''
        self.marker.fence = ''
