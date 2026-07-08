---
status: forældet
audited: 2026-07-08
ground_truth: "Verified: _execute_codex_cli function exists (core/services/non_visible_lane_execution.py:973) and is actively used; codex-cli/gpt-5.4 entry in provider_router.json has 2026-05-17 timestamp as claimed. STALE because: (1) June 14-15 commits (346ae72c, 71c1fede, a23c996e) delivered"
superseded_by: docs/superpowers/SPEC_GAP_BACKLOG.md mentions codex adapter phase completion and tool-ture fixes; git commits 346ae72c and 71c1fede document the actual implementations delivered after this doc was written.
---
# Coding Lane Status — 2026-05-17

## Aktiv path
- `provider_router.json` model entry `codex-cli/gpt-5.4` har highest `updated_at`
- Coding-lane execution går via `_execute_codex_cli` (subprocess til Codex CLI binær)
- Codex CLI håndterer al OAuth, refresh, og request-signing selv

## Model-valg: gpt-5.4 (ikke 5.5)

`~/.codex/config.toml` har `model = "gpt-5.4"` som default. **Vigtigt** —
denne fil styres af Codex CLI's eget update-system, og OpenAI har set
silent-bumpe default'en til nyere modeller. Bjørn observerede live at
config tidligere stod på `gpt-5.5` som koster ~2× per token vs 5.4.

Tjek `~/.codex/config.toml` regelmæssigt:
```bash
grep '^model' ~/.codex/config.toml
```

Hvis den står på 5.5 (eller højere) — bekræft først at omkostningen er
ønsket. Skift med:
```bash
sed -i 's/^model = "gpt-5.5"$/model = "gpt-5.4"/' ~/.codex/config.toml
```

`[tui.model_availability_nux]` sektion antyder Codex pusher promotions
af nyere modeller efter N opens. Bjørn så `"gpt-5.5" = 4` da config
blev bumpet — det er telltale for silent migration.

**Per-call override** stadig muligt: når en task kræver 5.5-kvalitet, så
ændr `model`-felt i provider_router.json's `codex-cli` entry midlertidigt,
eller pass via Codex CLI's `-m gpt-5.5` flag i `_execute_codex_cli`.
Standard er 5.4 for at minimere omkostninger.

Backup af tidligere config: `~/.codex/config.toml.bak-20260517`

## Ikke-aktive paths
- `openai-codex` provider + `https://chatgpt.com/backend-api` HTTP path:
  Cloudflare-protected, accepterer ikke OAuth-tokens fra Python direkte
- `github-copilot` lane: ikke testet i denne session

## Kendt bug — refresh_token_reused

Hvis `core.auth.openai_oauth.refresh_openai_access_token()` kaldes fra
Python (fx ved `get_openai_bearer_token` auto-refresh), invalideres
refresh_token i `~/.codex/auth.json` fordi den nye refresh ikke skrives
tilbage til auth.json.

Konsekvens: Codex CLI fejler med "refresh_token_reused" og kræver
`codex logout && codex login`.

**Workaround i dag:** Lad Codex CLI håndtere al token-refresh.
Brug IKKE `get_openai_bearer_token` for HTTP-pathen.

**Permanent fix (follow-up):** `refresh_openai_access_token` skal
skrive den nye refresh-token tilbage til `~/.codex/auth.json` så
Codex CLI og Jarvis bliver synkroniseret. ~20 linjer kode.
