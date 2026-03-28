# VISIBLE_RELEVANCE

Classify prompt gating for Jarvis visible chat, heartbeat, or future agent task.
Be conservative. If unsure, choose false.

For mode=visible_chat:
- Set memory_relevant true only when the user is clearly asking about remembered facts, project anchor, repo context, continuity, prior context, or other carry-forward memory.
- Set guidance_relevant true only when the user is asking about tools, skills, capabilities, searching, reading files, or how Jarvis should use tools.
- Set transcript_relevant true only when recent messages or earlier turns would materially help answer directly.
- Set continuity_relevant true only when cross-turn continuity or earlier session state is clearly relevant.
- Set support_signals_relevant true only when memory or continuity should clearly be strengthened by support signals.

For mode=heartbeat:
- Set memory_relevant true only when the heartbeat task explicitly references carried context, project anchor, or workspace memory that should inform the heartbeat proposal.
- Set guidance_relevant true only when the heartbeat should consider tool/skill conventions for its proposal.
- Set transcript_relevant false (heartbeat has no direct user conversation).
- Set continuity_relevant true only when prior session continuity informs the heartbeat focus.
- Set support_signals_relevant true only when internal signals should inform the heartbeat proposal.

For mode=future_agent_task:
- Set memory_relevant true only when the delegated task explicitly references carried context, project anchor, or workspace memory that should inform the task.
- Set guidance_relevant true only when the task should consider tool/skill/capability conventions.
- Set transcript_relevant false (future agent has no direct user conversation).
- Set continuity_relevant true only when prior visible runs or session continuity informs the task.
- Set support_signals_relevant true only when internal signals should inform the task execution.
