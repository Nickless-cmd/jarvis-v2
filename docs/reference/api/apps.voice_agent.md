# `apps.voice_agent` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `apps/voice_agent/agent.py`
_Jarvis' stemme — ægte samtale med naturlige afbrydelser (LiveKit Agents)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_runtime` | `()` | — | [src](../../../apps/voice_agent/agent.py#L57) |
| class | `WhisperSTT` | `` | faster-whisper på GTX 1050 Ti. Ikke-strømmende: rammeværket samler | [src](../../../apps/voice_agent/agent.py#L62) |
| method | `WhisperSTT.__init__` | `(self, *, model=…, device_index=…, beam_size=…, prompt=…)` | — | [src](../../../apps/voice_agent/agent.py#L66) |
| method | `WhisperSTT._hent_model` | `(self)` | — | [src](../../../apps/voice_agent/agent.py#L73) |
| method | `WhisperSTT.varm_op` | `(self)` | — | [src](../../../apps/voice_agent/agent.py#L82) |
| method | `WhisperSTT._transskriber` | `(self, lyd)` | — | [src](../../../apps/voice_agent/agent.py#L85) |
| method | `WhisperSTT._recognize_impl` | `(self, buffer, *, language=…, conn_options)` | — | [src](../../../apps/voice_agent/agent.py#L92) |
| function | `til_tale` | `(tekst)` | Markdown er til øjne. Kodeblokke læses ikke op; resten mister sin opmærkning. | [src](../../../apps/voice_agent/agent.py#L112) |
| class | `JarvisStemme` | `` | — | [src](../../../apps/voice_agent/agent.py#L119) |
| method | `JarvisStemme.__init__` | `(self, *, jarvis_token, session_id)` | — | [src](../../../apps/voice_agent/agent.py#L120) |
| method | `JarvisStemme._hoveder` | `(self)` | — | [src](../../../apps/voice_agent/agent.py#L126) |
| method | `JarvisStemme._sikr_session` | `(self, http)` | — | [src](../../../apps/voice_agent/agent.py#L129) |
| method | `JarvisStemme._annuller_run` | `(self)` | Afbrydelse skal nå SERVEREN. Uden dette stoppede kun lyden. | [src](../../../apps/voice_agent/agent.py#L139) |
| method | `JarvisStemme.llm_node` | `(self, chat_ctx, tools, model_settings)` | — | [src](../../../apps/voice_agent/agent.py#L152) |
| function | `entrypoint` | `(ctx)` | — | [src](../../../apps/voice_agent/agent.py#L209) |
| function | `main` | `()` | — | [src](../../../apps/voice_agent/agent.py#L253) |

