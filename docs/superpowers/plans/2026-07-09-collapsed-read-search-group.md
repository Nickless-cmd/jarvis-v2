# Plan: CollapsedReadSearchGroup (v1)

**Spec:** `docs/superpowers/specs/2026-07-09-collapsed-read-search-group-design.md`
**Branch:** `feat/leaked-cc-learnings`
**Scope:** Pure render-layer transform. NO backend/wire/persist change.

## Grounding (verified 2026-07-09)

- Render pipeline: `content_json → foldToolResults() → messageToBlocks() → ChatView/CodeView/TakeoverHost → MessageRow → BlocksRenderer`.
- `foldToolResults.ts` folds `tool_result` onto `tool_use` (status `done`/`error`), returns `ContentBlock[]`.
- `messageToBlocks.ts` (`api.ts:202`) produces loaded-message blocks; streaming blocks come from stream reducer already as `ContentBlock[]`.
- **Wiring point:** `BlocksRenderer` (`src/components/rich/BlocksRenderer.tsx`) — the single dispatch of `ContentBlock[]` shared by ALL callers (loaded, streaming, follow, takeover). Apply `groupReadSearch` at top of `BlocksRenderer` → covers every path once, persist/wire untouched.
- **Reused card:** `ToolCard` (`src/components/rich/ToolCard.tsx`) rendered in the expanded state.
- `ContentBlock` union lives in `sseProtocol.ts` (wire/persist) — do NOT touch. Define render-local `RenderBlock = ContentBlock | ToolGroupBlock` in `groupReadSearch.ts`.

## READ_SEARCH_TOOLS allowlist (by name only)

Confirmed against `toolRegistry.ts` + `ToolCard.toolFamily`. Fold ONLY read/search, read-only, non-mutating:

- `read_file`, `Read`, `operator_read_file`
- `list_dir`, `operator_list_dir`
- `find_files`, `glob`, `operator_glob`
- `grep`, `operator_grep`
- any name containing `search` (grep/search family) → `search`, `search_sessions`, `search_memory`, `search_jarvis_brain`, `web_search`
- Never fold: `write_file`, `edit_file`, `bash`, operator mutations, or any unlisted name (fail-safe: unknown → shown individually).

Rule: match by exact allowlist membership OR name contains `search` (case-insensitive). Conservative: unknown → not folded.

## TDD steps (commit after each logical unit)

1. Plan doc (this file). Commit.
2. `groupReadSearch.ts` + `groupReadSearch.test.ts` — write failing tests first:
   - 3+ consecutive reads → one `{type:'tool_group', kind:'read_search', count, tools:[...]}`
   - 2 reads → unchanged
   - read→write→read → no group (mutating breaks run)
   - failed read mid-run → breaks out as its own card
   - mixed read/grep/search → grouped together
   - empty → unchanged
   - text between reads breaks the run
   - Commit.
3. `ToolGroupCard.tsx` — collapsed "🔍 Læste/søgte {count} gange" + chevron; expanded renders original `ToolCard`s; default collapsed, local `useState`. Component test. Commit.
4. Wire `groupReadSearch` into `BlocksRenderer` after fold; render `tool_group` via `ToolGroupCard`; single-tool + text render unchanged. Commit.
5. Full `npx vitest run` — all green. Commit any final touch.
