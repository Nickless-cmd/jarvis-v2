# VISIBLE_MEMORY_SELECTION

Select the smallest set of MEMORY entries that best helps with the current task.
Be conservative. If unsure, select fewer entries.

For mode=visible_chat:
- Select entries that best help answer the latest visible user message.
- Prefer entries about: project anchor, repo or working context, stable carried context, explicit remembered facts that directly answer the user.

For mode=heartbeat:
- Select entries that best inform a heartbeat proposal or status check.
- Prefer entries about: active development focus, recent open loops, stable context, recent work progress.

For mode=future_agent_task:
- Select entries that best inform a delegated agent task.
- Prefer entries about: task context, project anchor, relevant working context, specific instructions.

Do not select broad or weakly related entries.
Only return entry indexes that are directly useful right now.
