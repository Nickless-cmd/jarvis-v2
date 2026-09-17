# `apps.api.jarvis_api.routes.03` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `apps/api/jarvis_api/routes/sensory.py`
_Sansernes Arkiv HTTP endpoints._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `SensoryRecordPayload` | `` | — | [src](../../../apps/api/jarvis_api/routes/sensory.py#L23) |
| function | `list_memories` | `(modality=…, limit=…, offset=…, since=…)` | — | [src](../../../apps/api/jarvis_api/routes/sensory.py#L31) |
| function | `search_memories` | `(q=…, modality=…, limit=…)` | — | [src](../../../apps/api/jarvis_api/routes/sensory.py#L44) |
| function | `summary` | `()` | — | [src](../../../apps/api/jarvis_api/routes/sensory.py#L54) |
| function | `get_memory` | `(memory_id)` | — | [src](../../../apps/api/jarvis_api/routes/sensory.py#L59) |
| function | `record_memory` | `(payload)` | — | [src](../../../apps/api/jarvis_api/routes/sensory.py#L67) |

## `apps/api/jarvis_api/routes/status.py`
_Public-safe /status endpoint._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_format_uptime` | `(seconds)` | — | [src](../../../apps/api/jarvis_api/routes/status.py#L22) |
| function | `_daemon_count` | `()` | — | [src](../../../apps/api/jarvis_api/routes/status.py#L36) |
| function | `_visible_model_label` | `()` | — | [src](../../../apps/api/jarvis_api/routes/status.py#L44) |
| function | `status` | `()` | — | [src](../../../apps/api/jarvis_api/routes/status.py#L54) |

## `apps/api/jarvis_api/routes/system_health.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `system_health` | `()` | — | [src](../../../apps/api/jarvis_api/routes/system_health.py#L19) |
| function | `system_git` | `()` | Return current git branch and diff stats (insertions/deletions since HEAD). | [src](../../../apps/api/jarvis_api/routes/system_health.py#L39) |
| class | `CommitRequest` | `` | — | [src](../../../apps/api/jarvis_api/routes/system_health.py#L85) |
| function | `system_git_commit` | `(body)` | Stage tracked changes and commit with the given message. | [src](../../../apps/api/jarvis_api/routes/system_health.py#L90) |

## `apps/api/jarvis_api/routes/tool_router.py`
_MC observability for tool_router._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_bucket_count` | `(values, n_buckets=…)` | — | [src](../../../apps/api/jarvis_api/routes/tool_router.py#L14) |
| function | `get_state` | `()` | — | [src](../../../apps/api/jarvis_api/routes/tool_router.py#L25) |

## `apps/api/jarvis_api/routes/totp.py`
_TOTP-setup for owner-override (spec §6.2). Armerer bagdøren: generér nøgle,_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_owner_or_403` | `()` | Returnér owner-User eller rejs 403. Ubundet (no-auth) → owner. | [src](../../../apps/api/jarvis_api/routes/totp.py#L16) |
| function | `totp_status` | `()` | — | [src](../../../apps/api/jarvis_api/routes/totp.py#L30) |
| function | `_do_setup` | `()` | — | [src](../../../apps/api/jarvis_api/routes/totp.py#L35) |
| function | `totp_setup` | `()` | Generér + gem en ny TOTP-seed for owner. Returnér secret + otpauth-URI | [src](../../../apps/api/jarvis_api/routes/totp.py#L52) |
| function | `totp_revoke` | `()` | Fjern owners TOTP-seed (deaktivér override til ny setup, §9 kompromittering). | [src](../../../apps/api/jarvis_api/routes/totp.py#L59) |

## `apps/api/jarvis_api/routes/transcribe.py`
_POST /transcribe — diktering-transskription til jarvis-desk's mic-knap._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `transcribe` | `(file, language=…)` | — | [src](../../../apps/api/jarvis_api/routes/transcribe.py#L22) |

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

## `apps/api/jarvis_api/routes/voice_live.py`
_POST /voice/samtale — åbn en ægte stemme-samtale med Jarvis (LiveKit/WebRTC)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `SamtaleRequest` | `` | — | [src](../../../apps/api/jarvis_api/routes/voice_live.py#L44) |
| function | `_livekit_noegler` | `()` | — | [src](../../../apps/api/jarvis_api/routes/voice_live.py#L48) |
| function | `livekit_billet` | `(api_key, api_secret, *, identitet, rum, navn=…, admin=…, ttl=…)` | LiveKit-adgangsbillet (JWT HS256, LiveKits eget format). | [src](../../../apps/api/jarvis_api/routes/voice_live.py#L56) |
| function | `_send_agent` | `(api_key, api_secret, rum, metadata)` | Bed LiveKit sende voice-agenten ind i rummet med sin hemmelige metadata. | [src](../../../apps/api/jarvis_api/routes/voice_live.py#L70) |
| function | `aabn_samtale` | `(body, request)` | — | [src](../../../apps/api/jarvis_api/routes/voice_live.py#L86) |

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

