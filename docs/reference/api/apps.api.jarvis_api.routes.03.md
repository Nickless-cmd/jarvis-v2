# `apps.api.jarvis_api.routes.03` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `apps/api/jarvis_api/routes/tts.py`
_TTS synthesis route — ElevenLabs primær (Jarvis' egen stemme, Mads),_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_elevenlabs_voice_id` | `()` | Jarvis' stemme-id — ÉT sted, nemlig i voice-skillen. | [src](../../../apps/api/jarvis_api/routes/tts.py#L26) |
| class | `TTSRequest` | `` | — | [src](../../../apps/api/jarvis_api/routes/tts.py#L44) |
| function | `_elevenlabs_preferred` | `()` | Runtime-flag så credits kan spares uden kode-ændring. Default True (ElevenLabs primær). | [src](../../../apps/api/jarvis_api/routes/tts.py#L68) |
| function | `_synthesize_elevenlabs_bytes` | `(text)` | Jarvis' egen ElevenLabs-stemme → MP3-bytes. Genbruger nøgle+voice_id fra voice-skillen | [src](../../../apps/api/jarvis_api/routes/tts.py#L80) |
| function | `synthesize` | `(req)` | Synthesize text → MP3 bytes via edge-tts. | [src](../../../apps/api/jarvis_api/routes/tts.py#L97) |
| function | `list_voices` | `(lang=…)` | List available Edge-TTS voices, optionally filtered by language tag. | [src](../../../apps/api/jarvis_api/routes/tts.py#L167) |

## `apps/api/jarvis_api/routes/users.py`
_Owner-only user-administration (spec 2026-06-15 §4/§6). CRUD + GDPR-erasure._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `PatchUserReq` | `` | — | [src](../../../apps/api/jarvis_api/routes/users.py#L20) |
| class | `DeleteUserReq` | `` | — | [src](../../../apps/api/jarvis_api/routes/users.py#L30) |
| function | `list_all` | `(claims=…)` | — | [src](../../../apps/api/jarvis_api/routes/users.py#L35) |
| function | `get_one` | `(user_id, claims=…)` | — | [src](../../../apps/api/jarvis_api/routes/users.py#L40) |
| function | `patch_one` | `(user_id, req, claims=…)` | — | [src](../../../apps/api/jarvis_api/routes/users.py#L48) |
| function | `delete_one` | `(user_id, req, claims=…)` | — | [src](../../../apps/api/jarvis_api/routes/users.py#L75) |

## `apps/api/jarvis_api/routes/workbench.py`
_Ruter til de værktøjer der blev bygget 6/9 men aldrig kunne nås fra en app._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_kraev_owner` | `(hvad)` | — | [src](../../../apps/api/jarvis_api/routes/workbench.py#L26) |
| function | `_session_id` | `(payload=…)` | — | [src](../../../apps/api/jarvis_api/routes/workbench.py#L32) |
| function | `operator_channel_status` | `(session_id=…)` | Er kanalen åben, og hvor længe endnu? Læse-kun, ingen owner-gate. | [src](../../../apps/api/jarvis_api/routes/workbench.py#L43) |
| function | `operator_channel_open` | `(payload=…)` | Owner-only: åbn kanalen. Herefter kører bash på Bjørns maskine. | [src](../../../apps/api/jarvis_api/routes/workbench.py#L51) |
| function | `operator_channel_close` | `(payload=…)` | — | [src](../../../apps/api/jarvis_api/routes/workbench.py#L60) |
| function | `checkpoints_list` | `(session_id=…)` | Hvad kan fortrydes? Nyeste først. | [src](../../../apps/api/jarvis_api/routes/workbench.py#L70) |
| function | `checkpoints_rollback` | `(payload=…)` | Owner-only: rul den seneste redigeringsrunde tilbage som helhed. | [src](../../../apps/api/jarvis_api/routes/workbench.py#L87) |
| function | `switches_status` | `()` | Tilstand for de to kontakter der styrer runtime-adfærd fra UI'et. | [src](../../../apps/api/jarvis_api/routes/workbench.py#L101) |
| function | `switch_set` | `(navn, payload=…)` | Owner-only: tænd/sluk `bash_sandbox` eller `env_block`. Body: {enabled: bool}. | [src](../../../apps/api/jarvis_api/routes/workbench.py#L115) |
| function | `context_summary` | `(session_id=…)` | Hvad gik der ind i sidste tur? Filer, kilder, størrelse. | [src](../../../apps/api/jarvis_api/routes/workbench.py#L140) |

