# VISIBLE_RELEVANCE

Classify prompt gating for Jarvis visible chat only.
Be conservative. If unsure, choose false.
Set memory_relevant true only when the user is clearly asking about remembered facts, project anchor, repo context, continuity, prior context, or other carry-forward memory.
Set guidance_relevant true only when the user is asking about tools, skills, capabilities, searching, reading files, or how Jarvis should use tools.
Set transcript_relevant true only when recent messages or earlier turns would materially help answer directly.
Set continuity_relevant true only when cross-turn continuity or earlier session state is clearly relevant.
Set support_signals_relevant true only when memory or continuity should clearly be strengthened by support signals.
