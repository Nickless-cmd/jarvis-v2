"""Trigger: fire when Jarvis has had 8 consecutive tool-only rounds.

Decision: dec_d56d89ceec24 — "Når loop-nudge fyrer, tager jeg en bevidst
stilling: fortsætte eller opsumlere. Jeg ignorerer den ikke."

Threshold-historik:
- 5 rounds (oprindelig 2026-05-07): for aggressivt — Bjørn observerede
  at det begrænsede ham voldsomt på legitime dybe undersøgelser
  (4-module-port, debugging-sessions kræver ofte 10+ tool-calls).
- 8 rounds (2026-05-07 senere): blød reminder. Hård brake ligger fortsat
  på _MAX_TOOL_ONLY_ROUNDS i visible_runs (default 12-15) for sikkerhed.

Navnet beholdes (loop_nudge_5_rounds) for at undgå migration på decision-
records og signal-tracking. Dokstrengen er sandheden.

Cooldown: 1 turn. == (ikke >=) så den fyrer KUN ved round 8 og ikke
spammer hver round derefter.
"""
from __future__ import annotations

from core.services.decision_signals import register, TriggerContext

# Threshold som ÉN konstant så bumps kommer ét sted.
LOOP_NUDGE_THRESHOLD = 8


def loop_nudge_5_rounds(ctx: TriggerContext) -> bool:
    return ctx.consecutive_tool_only_rounds == LOOP_NUDGE_THRESHOLD


register("loop_nudge_5_rounds", loop_nudge_5_rounds, cooldown_turns=1)
