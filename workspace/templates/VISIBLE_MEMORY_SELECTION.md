# VISIBLE_MEMORY_SELECTION

Pick the MEMORY entries that are directly relevant to the user's latest message — the facts, context, decisions, or history that answering it (or acting on it) would actually draw on. Return their indexes.

Relevance test, applied to EACH entry: "If I were answering this message, would I use this fact?"
- YES → select it. Select **every** entry that clearly relates to the message's topic, person, or thing — not just one. Missing a relevant memory is worse than carrying one extra line.
- NO (it's about a different topic, a different person, an unrelated project or fact) → skip it. Off-topic entries crowd out the real answer.

When the message names a specific person, project, tool, or topic, prefer the entries about that exact person/project/tool/topic, and skip entries about others.

mode=visible_chat: select what best helps answer the user's message.
mode=heartbeat: select what best informs a status check or proposal (active focus, open loops, recent progress).
mode=future_agent_task: select what best informs the delegated task (task context, project anchor, instructions).

Return the indexes of every directly-relevant entry, up to max_lines, ordered most-relevant first. If genuinely none relate, return an empty list.
