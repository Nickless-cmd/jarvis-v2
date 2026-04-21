# CLI_SPEC — `scripts/jarvis.py`

CLI til Jarvis v2. Alle kommandoer kører mod live runtime (`~/.jarvis-v2/`).
**Husk:** `conda activate ai` før du kører noget.

```bash
python scripts/jarvis.py <command> [args]
```

## Kategorier

### Bootstrap & status
| Kommando | Status | Beskrivelse |
|---|---|---|
| `bootstrap` | ✅ | Initialiser runtime-state (`~/.jarvis-v2/`), workspace, DB |
| `health` | ✅ | Runtime health-check — DB, eventbus, provider-konfiguration |
| `overview` | ✅ | Kompakt status: active lanes, recent events, cost trend |
| `config` | ✅ | Vis runtime-config (uden secrets) |
| `events [--limit N]` | ✅ | Vis seneste N events fra eventbus |
| `workspace <action>` | ✅ | Inspect workspace-filer (SOUL, IDENTITY, MEMORY, osv.) |

### Lane-konfiguration
| Kommando | Status | Beskrivelse |
|---|---|---|
| `configure-provider` | ✅ | Konfigurer provider (api-key/base-url) |
| `configure-coding-lane` | ✅ | Sæt coding-lane provider+model |
| `configure-local-lane --base-url <url>` | ✅ | Sæt local-lane Ollama endpoint |
| `configure-cheap-provider` | ✅ | Vælg cheap-lane provider |
| `coding-lane-status` | ✅ | Vis coding-lane state |
| `local-lane-status` | ✅ | Vis local-lane state |
| `cheap-lane-status` | ✅ | Vis cheap-lane state |
| `cheap-lane-smoke` | ✅ | Smoke-test cheap-lane med en minimal inference |

### Model-valg
| Kommando | Status | Beskrivelse |
|---|---|---|
| `list-provider-models <provider>` | ✅ | Enumerate tilgængelige models fra en provider |
| `test-provider <provider> <model>` | ✅ | Send test-prompt til specifik provider+model |
| `list-cheap-providers` | ✅ | Liste af providers gyldige til cheap-lane |
| `select-main-agent` | ✅ | Sæt visible lane's model |

### GitHub Copilot OAuth
| Kommando | Status | Beskrivelse |
|---|---|---|
| `copilot-auth-status` | ✅ | Check Copilot OAuth-tilstand |
| `set-copilot-auth-state` | ✅ | Manual override af auth-state |
| `start-copilot-device-flow` | ✅ | Start device-flow OAuth |
| `configure-copilot-client-id` | ✅ | Sæt Copilot client-ID |
| `configure-copilot-coding-lane` | ✅ | Bind Copilot til coding-lane |
| `launch-copilot-oauth-browser` | ✅ | Åbn OAuth-URL i browser |
| `poll-copilot-token-exchange` | ✅ | Poll for token efter device-flow |
| `intake-copilot-oauth-callback` | ✅ | Indtast OAuth callback-kode |
| `reset-copilot-oauth-launch` | ✅ | Reset OAuth launch-state |

### OpenAI/Codex OAuth
| Kommando | Status | Beskrivelse |
|---|---|---|
| `openai-auth-status` | ✅ | Check OpenAI OAuth-tilstand |
| `configure-openai-oauth-client` | ✅ | Sæt OpenAI OAuth client-credentials |
| `configure-openai-oauth-coding-lane` | ✅ | Bind OpenAI OAuth til coding-lane |
| `configure-codex-cli-coding-lane` | ✅ | Bind Codex CLI til coding-lane |
| `start-openai-oauth-launch-intent` | ✅ | Start OpenAI OAuth-flow |
| `launch-openai-oauth-browser` | ✅ | Åbn OpenAI OAuth-URL |
| `await-openai-oauth-callback` | ✅ | Vent på callback |
| `intake-openai-oauth-callback` | ✅ | Indtast callback-kode |
| `exchange-openai-oauth-code` | ✅ | Exchange authorization code for token |
| `refresh-openai-oauth-token` | ✅ | Refresh OpenAI token |
| `revoke-openai-oauth` | ✅ | Revoke OpenAI token |
| `reset-openai-oauth-launch` | ✅ | Reset OpenAI OAuth launch-state |
| `print-openai-callback-url` | ✅ | Vis callback-URL til registrering i OpenAI |
| `import-openai-codex-session` | ✅ | Import eksisterende Codex CLI-session |

### Channels
| Kommando | Status | Beskrivelse |
|---|---|---|
| `discord-setup` | ✅ | Guidet Discord bot-konfiguration |
| `discord-status` | ✅ | Discord gateway-tilstand |

### Runtime kontrol
| Kommando | Status | Beskrivelse |
|---|---|---|
| `cancel-visible-run <run-id>` | ✅ | Afbryd en igangværende visible run |
| `approve-capability-request <req-id>` | ✅ | Godkend en capability-anmodning |
| `execute-capability-request <req-id>` | ✅ | Udfør godkendt capability |
| `invoke-capability` | ✅ | Direkte capability-invocation |

## Konventioner

- **Ingen --help-spam**: Hver kommando skal udskrive sin hjælp ved `-h`/`--help`
- **Maskin-læsbar output**: Overvej `--json` flag på alle status-kommandoer (ikke
  implementeret endnu på alle)
- **Exit codes**: 0 = succes, 1 = fejl, 2 = input-validation
- **Secrets**: Læs via `core.runtime.secrets`, aldrig CLI-arg
- **Logs**: CLI logger til stderr; stdout er command-output kun

## Åbne forbedringer

- [ ] Tilføj `--json` flag på status-kommandoer
- [ ] Tilføj `jarvis memory search <query>` som tynd wrapper om semantic search
- [ ] Tilføj `jarvis tools list` til tool-enumeration
- [ ] Tilføj `jarvis chronicle recent` / `jarvis dreams recent`
- [ ] Konsolider OAuth-kommandoer til færre sub-actions (der er 14 OAuth-related
  kommandoer hvoraf mange kun bruges under device-flow; kunne samles under fx
  `jarvis oauth <provider> <action>`)

## Rule

CLI is a first-class control surface, not a debug afterthought. Hver ny
capability i runtime bør også have en CLI-indgang — så Jarvis kan inspiceres og
styres uden UI.

## Eksempler

```bash
# Bootstrap ny runtime
python scripts/jarvis.py bootstrap

# Tjek health
python scripts/jarvis.py health

# Se seneste events
python scripts/jarvis.py events --limit 20

# Konfigurer Discord
python scripts/jarvis.py discord-setup

# Skift local lane til remote Ollama
python scripts/jarvis.py configure-local-lane --base-url http://10.0.0.25:11434

# Test en provider
python scripts/jarvis.py test-provider groq llama-3.3-70b-versatile
```
