# `apps.voice_agent` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `apps/voice_agent/agent.py`
_Jarvis' stemme — ægte samtale med naturlige afbrydelser (LiveKit Agents)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_runtime` | `()` | — | [src](../../../apps/voice_agent/agent.py#L57) |
| class | `WhisperSTT` | `` | faster-whisper på GTX 1070. Ikke-strømmende: rammeværket samler | [src](../../../apps/voice_agent/agent.py#L62) |
| method | `WhisperSTT.__init__` | `(self, *, model=…, device_index=…, beam_size=…, prompt=…)` | — | [src](../../../apps/voice_agent/agent.py#L70) |
| method | `WhisperSTT._hent_model` | `(self)` | — | [src](../../../apps/voice_agent/agent.py#L77) |
| method | `WhisperSTT.varm_op` | `(self)` | — | [src](../../../apps/voice_agent/agent.py#L86) |
| method | `WhisperSTT._transskriber` | `(self, lyd)` | — | [src](../../../apps/voice_agent/agent.py#L89) |
| method | `WhisperSTT._recognize_impl` | `(self, buffer, *, language=…, conn_options)` | — | [src](../../../apps/voice_agent/agent.py#L96) |
| function | `til_whisper_lyd` | `(ramme)` | int16 i vilkårlig rate/kanaler → float32 mono 16 kHz, som whisper vil have. | [src](../../../apps/voice_agent/agent.py#L110) |
| function | `til_tale` | `(tekst)` | Markdown er til øjne. Kodeblokke læses ikke op; resten mister sin opmærkning. | [src](../../../apps/voice_agent/agent.py#L126) |
| class | `JarvisMarkoer` | `` | Tom markør. Rammeværket springer HELT over at svare, hvis sessionen ikke | [src](../../../apps/voice_agent/agent.py#L133) |
| method | `JarvisMarkoer.chat` | `(self, **kwargs)` | — | [src](../../../apps/voice_agent/agent.py#L139) |
| class | `JarvisStemme` | `` | — | [src](../../../apps/voice_agent/agent.py#L143) |
| method | `JarvisStemme.__init__` | `(self, *, jarvis_token, session_id)` | — | [src](../../../apps/voice_agent/agent.py#L144) |
| method | `JarvisStemme._hoveder` | `(self)` | — | [src](../../../apps/voice_agent/agent.py#L151) |
| method | `JarvisStemme._sikr_session` | `(self, http)` | — | [src](../../../apps/voice_agent/agent.py#L154) |
| method | `JarvisStemme._annuller_run` | `(self)` | Afbrydelse skal nå SERVEREN. Uden dette stoppede kun lyden. | [src](../../../apps/voice_agent/agent.py#L164) |
| method | `JarvisStemme._vent_til_forrige_er_stoppet` | `(self, http, sid)` | Et annulleret run er ikke straks væk. Sendes den nye besked før, ser | [src](../../../apps/voice_agent/agent.py#L177) |
| method | `JarvisStemme.llm_node` | `(self, chat_ctx, tools, model_settings)` | — | [src](../../../apps/voice_agent/agent.py#L198) |
| function | `entrypoint` | `(ctx)` | — | [src](../../../apps/voice_agent/agent.py#L256) |
| function | `main` | `()` | — | [src](../../../apps/voice_agent/agent.py#L305) |

## `apps/voice_agent/proeve.py`
_Syntetisk samtale-prøve: stil et spørgsmål, afbryd Jarvis midt i svaret, mål._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `t` | `()` | — | [src](../../../apps/voice_agent/proeve.py#L27) |
| function | `tale` | `(tekst, navn)` | — | [src](../../../apps/voice_agent/proeve.py#L31) |
| function | `afspil` | `(kilde, lyd)` | — | [src](../../../apps/voice_agent/proeve.py#L40) |
| function | `stilhed` | `(kilde, sek)` | — | [src](../../../apps/voice_agent/proeve.py#L47) |
| function | `main` | `()` | — | [src](../../../apps/voice_agent/proeve.py#L51) |

