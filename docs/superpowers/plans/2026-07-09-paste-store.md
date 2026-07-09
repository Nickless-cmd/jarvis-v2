# Plan: Paste-store (eksternalisér store bruger-pastes med reference)

**Spec:** `docs/superpowers/specs/2026-07-09-paste-store-design.md`
**Dato:** 2026-07-09
**Mønster:** spejler `core/services/tool_result_store.py` (fil-I/O), men id er **hash-baseret** (sha256[:16]) for idempotens — IKKE uuid4.

## Task-liste (TDD, commit pr. enhed)

### 1. Plan-doc (dette dokument). ✅

### 2. `core/services/paste_store.py` + `tests/test_paste_store.py`
- `PASTE_STORE_DIR` i `core/runtime/config.py` (spejl `TOOL_RESULTS_DIR`).
- `save_paste(text) -> id` — hash-baseret (sha256(text.encode)[:16]), idempotent,
  atomisk write (tmp → replace). Samme tekst → samme id → én fil.
- `get_paste(id) -> {id, text, line_count, created_at} | None`.
- `build_paste_reference(id, *, line_count) -> "[paste:<id> +N linjer]"`.
- `parse_paste_reference(content) -> {paste_id, line_count} | None`.
- `expand_paste_references(content) -> str` — erstat `[paste:<id> +N linjer]` med fuld
  tekst via `get_paste`; ukendt id → behold referencen (degradér, aldrig crash).
- `cleanup_old_pastes(max_age_days)`.
- Tests: save→get round-trip; idempotens (samme tekst → samme id, én fil);
  build/parse symmetri; ukendt id → None; parse ikke-reference → None;
  expand ON/ukendt-id.

### 3. Routes `apps/api/jarvis_api/routes/paste.py`
- `POST /paste` `{text}` → `{paste_id, reference}`.
- `GET /paste/{id}` → fuld tekst; 404 på ukendt.
- Registrér i `app.py` som de andre routers.
- Test via app test-client.

### 4. Kontekst-ekspansion (model ser fuld tekst — default ON)
- Flag `paste_inline_to_model` (default ON via `get_runtime_state_value`).
- I `chat_stream_v2.py` (+ `chat.py` v1): persistér `effective_message` (med reference,
  kompakt historik) MEN send en ekspanderet `model_message` til runnet når flag ON.
- Ukendt id → behold reference (degradér).
- GUARDRAIL: dette er den ENESTE model-facing wiring. Composer-eksternalisering (step 5)
  gates bag `paste_store_enabled` (default OFF) indtil verificeret, så modellen aldrig
  tavst mister paste-tekst.

### 5. Desk composer `onPaste`
- `shouldExternalizePaste(text)` ren fn: >20 linjer eller >2000 tegn.
- onPaste over tærskel → hold tekst lokalt, vis fjernelig reference-chip; ved send
  POST `/paste` → `[paste:<id> +N linjer]`. Under tærskel → inline uændret.
- vitest for tærskel-fn.
- Gated bag `paste_store_enabled` (default OFF) til manuel verifikation.

### 6. Desk render
- Besked med `[paste:<id> +N linjer]` → reference-chip; klik → lazy `GET /paste/{id}`.

## Verify
- `conda activate ai && python -m pytest tests/test_paste_store.py -v`
- `python -m compileall -q core/services/paste_store.py apps/api/jarvis_api/routes/paste.py`
- `cd apps/jarvis-desk && npx vitest run`
