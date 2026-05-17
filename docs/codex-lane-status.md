# Coding Lane Status — 2026-05-17

## Aktiv path
- `provider_router.json` model entry `codex-cli/gpt-5.4` har highest `updated_at`
- Coding-lane execution går via `_execute_codex_cli` (subprocess til Codex CLI binær)
- Codex CLI håndterer al OAuth, refresh, og request-signing selv

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
