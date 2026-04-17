"""Council Deliberation Controller — active agent dynamics inside deliberation.

Manages the deliberation loop with:
- Witness escalation: silent observer can request to join as active participant
- Dynamic recruitment: cheap LLM detects missing perspectives after round 2
- Deadlock detection: bag-of-words cosine similarity across rounds
- Graduated deadlock response: devil's advocate first, then forced conclusion

Used by agent_runtime._run_collective_round (council mode) and
autonomous_council_daemon._run_autonomous_council.
"""
from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from core.eventbus.bus import event_bus

_DEADLOCK_THRESHOLD = 0.82
_MAX_ROUNDS = 8
_WITNESS_MARKER = "[ESKALERER]"
_RECRUITMENT_ROUND = 2


@dataclass
class DeliberationResult:
    transcript: str
    conclusion: str
    rounds_run: int
    deadlock_occurred: bool
    witness_escalated: bool
    recruited: str | None


def _cosine_similarity(a: str, b: str) -> float:
    """Bag-of-words cosine similarity between two strings. Returns 0.0–1.0."""
    if not a or not b:
        return 0.0
    tokens_a = Counter(a.lower().split())
    tokens_b = Counter(b.lower().split())
    vocab = set(tokens_a) | set(tokens_b)
    if not vocab:
        return 0.0
    dot = sum(tokens_a.get(w, 0) * tokens_b.get(w, 0) for w in vocab)
    norm_a = math.sqrt(sum(v * v for v in tokens_a.values()))
    norm_b = math.sqrt(sum(v * v for v in tokens_b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _is_deadlocked(round_outputs: list[list[str]]) -> bool:
    """Return True if round N is semantically similar to round N-2 (1-indexed rounds)."""
    if len(round_outputs) < 3:
        return False
    last = " ".join(round_outputs[-1])
    two_ago = " ".join(round_outputs[-3])
    return _cosine_similarity(last, two_ago) > _DEADLOCK_THRESHOLD


def _check_witness_escalation(witness_output: str) -> bool:
    """Return True if the witness is requesting to escalate to active participant."""
    return witness_output.strip().lower().startswith(_WITNESS_MARKER.lower())


def build_witness_prompt(*, transcript: str) -> str:
    """Build the system prompt for the witness agent."""
    return (
        "Du observerer denne deliberation. Du lytter til alt, men taler ikke — "
        "medmindre du ser noget afgørende der overses af de andre deltagere.\n\n"
        f"Transcript hidtil:\n{transcript}\n\n"
        f"Hvis du vil tale, start dit svar med '{_WITNESS_MARKER}'. "
        "Ellers svar med blot 'observerer.' for at indikere at du lytter."
    )


def _call_recruitment_llm(*, topic: str, transcript: str) -> str:
    from core.services.non_visible_lane_execution import execute_cheap_lane
    prompt = (
        f"Emne: {topic}\n\n"
        f"Transcript:\n{transcript[:600]}\n\n"
        "Mangler deliberationen et væsentligt perspektiv? "
        "Svar med ét rollernavn (f.eks. 'etiker', 'tekniker', 'pragmatiker') eller 'nej'."
    )
    result = execute_cheap_lane(message=prompt)
    return str(result.get("text") or "nej").strip()


def _analyze_recruitment_need(
    *,
    topic: str,
    transcript: str,
    active_members: list[str],
) -> str | None:
    """Ask LLM if a new role is needed. Returns role name or None.

    Returns None if LLM says 'nej' or suggested role is already active.
    """
    response = _call_recruitment_llm(topic=topic, transcript=transcript)
    role = response.strip().lower()
    if role == "nej" or not role:
        return None
    if role in [m.lower() for m in active_members]:
        return None
    return role


class DeliberationController:
    """Manages a deliberation with witness escalation, recruitment, and deadlock handling."""

    def __init__(
        self,
        *,
        topic: str,
        members: list[str],
        max_rounds: int = _MAX_ROUNDS,
    ) -> None:
        self.topic = topic
        self.active_members = list(members)
        self.max_rounds = max_rounds
        self._round_outputs: list[list[str]] = []
        self._transcript_lines: list[str] = []
        self._witness_escalated = False
        self._recruited: str | None = None
        self._deadlock_occurred = False
        self._recruited_done = False

    def run(self) -> DeliberationResult:
        """Run the full deliberation. Returns DeliberationResult."""
        conclusion = ""
        force_conclude = False
        devils_advocate_added = False

        for round_num in range(1, self.max_rounds + 1):
            outputs = self._run_round()
            self._round_outputs.append(outputs)
            self._transcript_lines.extend(outputs)

            # Check witness escalation
            for output in outputs:
                if _check_witness_escalation(output) and not self._witness_escalated:
                    self._witness_escalated = True
                    if "witness" not in self.active_members:
                        self.active_members.append("witness")
                    event_bus.publish("council.witness_escalated", {"round": round_num})

            # Recruitment after round 2 (once only)
            if round_num == _RECRUITMENT_ROUND and not self._recruited_done:
                self._recruited_done = True
                transcript_so_far = "\n".join(self._transcript_lines[-10:])
                try:
                    role = _analyze_recruitment_need(
                        topic=self.topic,
                        transcript=transcript_so_far,
                        active_members=self.active_members,
                    )
                    if role:
                        self._recruited = role
                        self.active_members.append(role)
                        event_bus.publish("council.agent_recruited", {"role": role, "round": round_num})
                except Exception:
                    pass

            # Deadlock detection (from round 3)
            if _is_deadlocked(self._round_outputs):
                self._deadlock_occurred = True
                event_bus.publish("council.deadlock_detected", {"round": round_num})
                if not devils_advocate_added:
                    devils_advocate_added = True
                    if "devils_advocate" not in self.active_members:
                        self.active_members.append("devils_advocate")
                    extra_outputs = self._run_round()
                    self._round_outputs.append(extra_outputs)
                    self._transcript_lines.extend(extra_outputs)
                    if not _is_deadlocked(self._round_outputs):
                        event_bus.publish("council.deadlock_resolved", {"round": round_num + 1})
                        continue
                # Still deadlocked: force conclude
                force_conclude = True
                event_bus.publish("council.deadlock_forced_conclusion", {"round": round_num})
                break

            if round_num >= self.max_rounds:
                force_conclude = True
                break

        conclusion = self._synthesize(forced=force_conclude)
        return DeliberationResult(
            transcript="\n".join(self._transcript_lines),
            conclusion=conclusion,
            rounds_run=len(self._round_outputs),
            deadlock_occurred=self._deadlock_occurred,
            witness_escalated=self._witness_escalated,
            recruited=self._recruited,
        )

    def _run_round(self) -> list[str]:
        """Run one round of deliberation. Override in subclasses for real agent execution."""
        return [f"{member}: (deliberating)" for member in self.active_members]

    def _synthesize(self, *, forced: bool = False) -> str:
        """Produce council conclusion. Override in real integration."""
        prefix = "Rådet er gået i stå. " if forced else ""
        return f"{prefix}Konklusion baseret på {len(self._transcript_lines)} bidrag."
