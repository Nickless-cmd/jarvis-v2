# Side task inbox lifecycle implementation plan

The approved design is the eight point list in the task conversation.

1. Extend `core/services/side_tasks.py` with an explicit queue state, work
   session/run links, a stable finding key, and terminal history. Keep old
   records readable and serialize mutations across API/runtime processes.
2. Add a read-only side task source to `core/services/inbox_view.py`. Keep
   `side_tasks` as the status authority; map pending/queued/activated to the
   inbox's waiting/on-way/in-progress sections and hide the section when empty.
   Route `inbox_done`/`inbox_drop` for side-task IDs through that authority.
3. Add a structured unresolved-finding tool. It records the disposition of
   concrete findings and creates a deduplicated side task only for deferred
   coverage gaps. Relevant new test failures must remain current-work blockers.
   Add concise end-of-run guidance so Jarvis calls it when appropriate.
4. Update Desk's existing task surfaces and API type for the queue status and
   work run ID. Verify focused Python/Desk tests, syntax and type checking.
5. Commit through the repository attribution wrapper, integrate with the
   current remote without overwriting concurrent work, push, deploy on the
   container through the documented pull/restart flow, and check health.

Tests are written and observed failing before each implementation step.
