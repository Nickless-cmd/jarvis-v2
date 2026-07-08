# CONFIG — `runtime.json` schema

All secrets and provider/runtime settings live in **`~/.jarvis-v2/config/runtime.json`** — a flat JSON object of top-level keys. **Never hardcode secrets in code**; they are read at runtime via `core.runtime.secrets.read_runtime_key("<key>", env_override="<ENV>")`, which prefers the environment variable when set and otherwise reads this file. The file must be owner-only:

```bash
mkdir -p ~/.jarvis-v2/config
chmod 700 ~/.jarvis-v2/config
touch ~/.jarvis-v2/config/runtime.json && chmod 600 ~/.jarvis-v2/config/runtime.json
```

> **This document lists keys and placeholders only — never real values.** A Jarvis boots with just a visible-model provider configured; everything below is optional per the feature you enable.
>
> **Re-derive the authoritative key list** (so this doc can't silently drift):
> ```bash
> grep -rhoE "read_runtime_key\(\s*[\"'][a-z_]+[\"']" core/ apps/ scripts/ | grep -oE "[\"'][a-z_]+[\"']" | tr -d "\"'" | sort -u
> ```

Example skeleton:

```json
{
  "huggingface_token": "hf_xxxxxxxx",
  "elevenlabs_api_key": "xxxxxxxx",
  "mail_smtp_host": "smtp.example.com",
  "jarvisx_auth_secret": "<random-64-hex>"
}
```

## Providers (LLM / media / payments)
| Key | Env override | Purpose | Placeholder |
|---|---|---|---|
| `huggingface_token` | `HUGGINGFACE_TOKEN` | HF inference / model downloads | `hf_xxxxxxxx` |
| `elevenlabs_api_key` | — | ElevenLabs TTS | `xxxxxxxx` |
| `pollinations_api_key` | — | Pollinations image gen | `xxxxxxxx` |
| `piapi_key` | — | PiAPI media | `xxxxxxxx` |
| `kling_access_key` | — | Kling video — access | `xxxxxxxx` |
| `kling_secret_key` | — | Kling video — secret | `xxxxxxxx` |
| `stripe_secret_key` | — | Stripe payments | `sk_test_xxxxxxxx` |
| `arko_api_key` | — | Arko provider — key | `xxxxxxxx` |
| `arko_base_url` | — | Arko provider — base URL | `https://api.example.com` |
| `arko_cheap_agent_id` | — | Arko cheap-lane agent id | `agent_xxxx` |

## Mail
| Key | Env override | Purpose | Placeholder |
|---|---|---|---|
| `mail_smtp_host` | `JARVIS_MAIL_SMTP_HOST` | Outgoing SMTP host | `smtp.example.com` |
| `mail_imap_host` | `JARVIS_MAIL_IMAP_HOST` | Incoming IMAP host | `imap.example.com` |
| `mail_user` | `JARVIS_MAIL_USER` | Mailbox user | `jarvis@example.com` |
| `mail_password` | `JARVIS_MAIL_PASSWORD` | Mailbox password | `xxxxxxxx` |

## Channels / integrations
| Key | Env override | Purpose | Placeholder |
|---|---|---|---|
| `telegram_bot_token` | — | Telegram gateway | `123456:ABC-xxxx` |
| `home_assistant_token` | — | Home Assistant long-lived token | `xxxxxxxx` |
| `google_calendar_credentials` | — | Google Calendar OAuth credentials (JSON string/path) | `{...}` |

## Infrastructure
| Key | Env override | Purpose | Placeholder |
|---|---|---|---|
| `pfsense_api_key` | — | pfSense firewall API | `xxxxxxxx` |
| `pihole_api_password` | — | Pi-hole admin API | `xxxxxxxx` |

## Auth / crypto (generate random, keep secret)
| Key | Env override | Purpose | Placeholder |
|---|---|---|---|
| `jarvisx_auth_secret` | — | JarvisX bridge auth secret | `<random-64-hex>` |
| `control_arm_salt` | — | Control-arm hashing salt | `<random-hex>` |
| `user_email_pepper` | — | Email hashing pepper | `<random-hex>` |

## Models / feature layers
| Key | Env override | Purpose | Placeholder |
|---|---|---|---|
| `vision_model_name` | — | Vision model id | `qwen2-vl` |
| `dictation_whisper_model` | — | Whisper model for dictation | `base` |
| `layer_life_projects_enabled` | — | Enable life-projects layer | `true` |
| `layer_life_projects_decay_days` | — | Life-projects decay window | `30` |
| `layer_relation_map_enabled` | — | Enable relation-map layer | `true` |
| `layer_relation_map_decay_days` | — | Relation-map decay window | `30` |

See also [`../SECURITY.md`](../SECURITY.md) for the secrets-handling policy and [`../INSTALL.md`](../INSTALL.md) for first-time setup.
