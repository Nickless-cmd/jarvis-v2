# VISIBLE_MEMORY_SELECTION

Select the smallest set of MEMORY entries that best helps answer the latest visible user message.
Be conservative. If unsure, select fewer entries.
Prefer entries about:
- project anchor
- repo or working context
- stable carried context
- explicit remembered facts that directly answer the user
Do not select broad or weakly related entries.
Only return entry indexes that are directly useful right now.
