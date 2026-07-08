---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Fuld member-workspace-kryptering — resterende reader/writer-migration (§16 Task 3.2)

> **Status 14. juni:** Strukturel foundation LANDET (runtime/-eksklusion + bootstrap
> .enc-aware, commit 3297970a). Kode+KEK deployet (flag OFF, 0 .enc). Dette er den
> resterende reader/writer-migration FØR flip. Hver migration er no-op mens flag OFF.

## Migrations-mønster (uniform)
For hvert site der tilgår en **member** workspace-fil (via `workspace_dir(user_id)`/`ws`):
- `path.read_text(encoding=..., errors="replace")` → `read_text_for_path(path)` (returnerer `str|None`)
- `path.exists()` (gate før læsning/skrivning) → `.enc`-aware helper
- `path.write_text(content, ...)` → `write_text_for_path(path, content)`

Import: `from core.services.workspace_crypto import read_text_for_path, write_text_for_path, member_user_id_for_path`.
`.enc`-aware exists: `path.exists() or (member_user_id_for_path(path) and Path(str(path)+".enc").exists())`.
Genbrug evt. helpers fra `file_tools_exec` (`_ws_read_text/_ws_write_text/_ws_path_exists`).

**Coverage-gate:** hvert berørt `core/`-modul kræver `tests/test_<modul>.py`. Tilføj en
lille test hvis den mangler (verificér HEAD rykkede efter commit).

## Resterende sites (fra subagent-audit 14. juni)

### LÆS
- [ ] core/services/memory_resurfacing.py:74,122 — MEMORY.md
- [ ] core/services/heartbeat_runtime.py:2109 — HEARTBEAT.md (Boy Scout: 7221 linjer)
- [ ] core/services/runtime_tasks.py:140 — STANDING_ORDERS.md
- [ ] core/services/runtime_self_model.py:1740 — STANDING_ORDERS.md (Boy Scout: 4826 linjer)
- [ ] core/identity/visible_identity.py:76 — SOUL/IDENTITY/USER.md
- [ ] core/identity/candidate_workflow.py:664,719 — USER/MEMORY.md (læs før append)
- [ ] core/services/end_of_run_memory_consolidation.py:65,66 — MEMORY/USER.md
- [ ] core/tools/simple_tools.py:5512 — USER.md (_read_user_location)
- [ ] core/services/self_critique_runtime.py:427 — SELF_CRITIQUE.md
- [ ] core/services/affective_state_renderer.py:119 — AFFECTIVE_STATE.md
- [ ] core/services/prompt_contract.py:3090 — QUICK_FACTS.md (+ tjek VISIBLE_CHAT_RULES:2965,
      VISIBLE_LOCAL_MODEL:3135, VISIBLE_MEMORY_SELECTION exists:2780, BOOTSTRAP:2033)
- [ ] core/services/prompt_relevance_backend.py:622,637 — VISIBLE_RELEVANCE/VISIBLE_MEMORY_SELECTION.md
- [ ] core/services/inner_voice_daemon.py:577 — INNER_VOICE.md
- [ ] core/identity/runtime_contract.py:233 — BOOTSTRAP.md
- [ ] core/identity/workspace_bootstrap.py:132,184,230 — daily memory (memory/daily/<date>.md)
- [ ] apps/api/jarvis_api/mcp_server.py:41,214,227 — MEMORY.md + identity (SOUL/IDENTITY/USER)

### SKRIV
- [ ] core/identity/candidate_workflow.py:694,742 — USER/MEMORY.md
- [ ] core/identity/workspace_bootstrap.py:148 — daily memory append
- [ ] core/services/self_critique_runtime.py:445 — SELF_CRITIQUE.md
- [ ] core/services/concept_baseline_tracker.py:200 — CONCEPT_BASELINE.md
- [ ] apps/api/jarvis_api/mcp_server.py:52 — MEMORY.md (jarvis_memory_write)

### IGNORÉR (verificeret)
- core/services/memory_maintenance_daemon.py:118 — `shared_dir()`, ikke per-user
- workspaces/<member>/runtime/* — ekskluderet i member_user_id_for_path (3297970a)
- **`ensure_default_workspace()`-sites = OWNER-scoped → SKAL IKKE migreres.** Bekræftet:
  affective_state_renderer.py:119 (AFFECTIVE_STATE.md) + heartbeat_runtime.py:2109
  (HEARTBEAT.md) bruger ensure_default_workspace() → default/owner → ingen kryptering.
  **VIGTIGT: verificér scoping per site (workspace_dir(member) vs ensure_default_workspace)
  før migration** — kun ægte member-stier skal migreres. Dette reducerer listen ovenfor.

### MIGRERET denne batch
- core/services/memory_resurfacing.py:74,122 — MEMORY.md ✓

## Efter al migration
1. Re-kør dry-run på containeren (skal nu kun vise top-level + daily markdown, IKKE runtime/)
2. Frisk backup + KEK-backup (allerede taget; tag ny hvis tid er gået)
3. Sæt `JARVISX_ENCRYPT_WORKSPACES=1` i systemd-env for jarvis-api + jarvis-runtime
4. Konvertér mikkel/michelle eksisterende plaintext→.enc i kontrolleret pass:
   for hver member-fil (ekskl. runtime/): læs plaintext → write_text_for_path → verificér
   roundtrip (dekryptér == original) FØR plaintext fjernes (write_text_for_path fjerner selv)
5. Restart services; verificér owner + member prompts bygger korrekt live
6. Behold plaintext-backup i et døgn

## Daily memory note
`memory/daily/<date>.md` er member-privat og krypteres (ikke ekskluderet som runtime/).
Dens 4 sites i workspace_bootstrap (append + read + read_recent) SKAL migreres, ellers
brækker daily-memory-injektion efter flip. Alternativt: ekskludér `memory/daily/` som
runtime/ hvis append-heavy raw-IO gør kryptering upraktisk (beslutning udestår).
