"""Trigger: fire when Jarvis has had 5 consecutive tool-only rounds.

Decision: dec_d56d89ceec24 — "Når loop-nudge fyrer, tager jeg en bevidst
stilling: fortsætte eller opsumlere. Jeg ignorerer den ikke."

Cooldown: 1 turn. Even though the trigger uses == (so it only matches at
exactly round 5), cooldown is belt-and-suspenders: if a future change
broadens to >= 5, cooldown still ensures one-fire-per-spree.
"""
from __future__ import annotations

from core.services.decision_signals import register, TriggerContext


def loop_nudge_5_rounds(ctx: TriggerContext) -> bool:
    return ctx.consecutive_tool_only_rounds == 5


register("loop_nudge_5_rounds", loop_nudge_5_rounds, cooldown_turns=1)
