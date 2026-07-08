# `core.skills.voice` — reference

> Generated 2026-07-08 from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/skills/voice/__init__.py`
_Voice interaction skill — wake word, STT, TTS._

_(no top-level classes or functions)_

## `core/skills/voice/stt.py`
_Speech-to-text using faster-whisper with VAD-gated recording._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_debug` | `(msg)` | Append a timestamped message to the voice debug log. | [src](../../../core/skills/voice/stt.py#L28) |
| function | `_drain_nonblocking` | `(fd)` | Drain all available bytes from a file descriptor. Returns bytes dropped. | [src](../../../core/skills/voice/stt.py#L39) |
| function | `get_model` | `(model_size=…, device=…, compute_type=…)` | Load or return cached Whisper model. | [src](../../../core/skills/voice/stt.py#L59) |
| function | `record_audio` | `(duration=…, sample_rate=…)` | Record audio from USB mic via parec and return as float32 at 16 kHz. | [src](../../../core/skills/voice/stt.py#L67) |
| function | `record_audio_vad` | `(max_duration=…, silence_ms=…, startup_ms=…, min_speech_ms=…)` | Record until user stops speaking or max_duration. | [src](../../../core/skills/voice/stt.py#L85) |
| function | `_normalize` | `(audio, target_rms=…)` | RMS-normalize float32 audio to target_rms. | [src](../../../core/skills/voice/stt.py#L213) |
| function | `_transcribe_local` | `(audio, model, language)` | Local faster-whisper-tiny — kept as offline-degradation tier. | [src](../../../core/skills/voice/stt.py#L229) |
| function | `_transcribe_via_hf` | `(audio, language)` | Primary: HF Whisper-large-v3 cloud. None on error/rate-limit. | [src](../../../core/skills/voice/stt.py#L247) |
| function | `_transcribe_via_elevenlabs` | `(audio, language)` | Fallback: ElevenLabs Scribe (paid SLA). None on error. | [src](../../../core/skills/voice/stt.py#L290) |
| function | `transcribe` | `(audio, model=…, language=…)` | ElevenLabs Scribe primary, local tiny offline fallback. | [src](../../../core/skills/voice/stt.py#L327) |
| function | `listen_and_transcribe` | `(duration=…, language=…)` | Record command from mic (VAD-gated) and return transcribed text. | [src](../../../core/skills/voice/stt.py#L355) |

## `core/skills/voice/tts.py`
_Text-to-speech — ElevenLabs (primary) with edge-tts fallback._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_get_elevenlabs_key` | `()` | — | [src](../../../core/skills/voice/tts.py#L32) |
| function | `_synthesize_elevenlabs` | `(text)` | Generate MP3 via ElevenLabs API. Returns path to temp file. | [src](../../../core/skills/voice/tts.py#L42) |
| function | `_synthesize_edge` | `(text)` | Generate MP3 via edge-tts. Returns path to temp file. | [src](../../../core/skills/voice/tts.py#L62) |
| function | `_pipewire_env` | `()` | — | [src](../../../core/skills/voice/tts.py#L71) |
| function | `play_audio` | `(path)` | Play an audio file through PipeWire/PulseAudio default sink. | [src](../../../core/skills/voice/tts.py#L76) |
| function | `_run_edge_tts_in_thread` | `(text)` | Run edge-tts in a dedicated thread+loop (handles both sync/async callers). | [src](../../../core/skills/voice/tts.py#L107) |
| function | `_edge_fallback` | `(text)` | Synthesize via edge-tts, handling both sync and async callers. | [src](../../../core/skills/voice/tts.py#L131) |
| function | `say` | `(text, blocking=…)` | Synthesize and play text. ElevenLabs primary, edge-tts fallback. | [src](../../../core/skills/voice/tts.py#L142) |

## `core/skills/voice/voice_daemon_worker.py`
_Voice daemon worker — runs the Hey Jarvis loop, called by voice_daemon.py._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_set_phase` | `(phase)` | Write current voice pipeline phase for the desktop orb to read. | [src](../../../core/skills/voice/voice_daemon_worker.py#L16) |
| function | `get_active_session_id` | `()` | — | [src](../../../core/skills/voice/voice_daemon_worker.py#L32) |
| function | `ask_jarvis` | `(session_id, text)` | — | [src](../../../core/skills/voice/voice_daemon_worker.py#L41) |
| function | `_capture_user_utterance` | `(duration)` | Listen N seconds, return cleaned utterance or '' if silence/noise. | [src](../../../core/skills/voice/voice_daemon_worker.py#L79) |
| function | `_handle_turn` | `(text)` | Process one utterance through ask_jarvis + speak. Returns False if | [src](../../../core/skills/voice/voice_daemon_worker.py#L86) |
| function | `on_wake_word` | `(word)` | — | [src](../../../core/skills/voice/voice_daemon_worker.py#L113) |
| function | `main` | `()` | — | [src](../../../core/skills/voice/voice_daemon_worker.py#L142) |

## `core/skills/voice/voice_loop.py`
_Main voice interaction loop — wake word → listen → respond._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `VoiceLoop` | `` | Full voice interaction cycle: | [src](../../../core/skills/voice/voice_loop.py#L11) |
| method | `VoiceLoop.__init__` | `(self, response_fn=…, wake_words=…)` | Args: | [src](../../../core/skills/voice/voice_loop.py#L20) |
| method | `VoiceLoop._default_response` | `(text)` | Fallback response if no callback provided. | [src](../../../core/skills/voice/voice_loop.py#L33) |
| method | `VoiceLoop._on_wake_word` | `(self, word)` | Handle wake word detection. | [src](../../../core/skills/voice/voice_loop.py#L37) |
| method | `VoiceLoop.run` | `(self)` | Start the voice loop (blocking). | [src](../../../core/skills/voice/voice_loop.py#L57) |
| method | `VoiceLoop.stop` | `(self)` | Stop the voice loop. | [src](../../../core/skills/voice/voice_loop.py#L67) |
| function | `quick_test` | `()` | Quick test: detect wake word, then record + transcribe one command. | [src](../../../core/skills/voice/voice_loop.py#L72) |

## `core/skills/voice/voice_test_full.py`
_Full voice pipeline test:_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `get_first_session_id` | `()` | — | [src](../../../core/skills/voice/voice_test_full.py#L25) |
| function | `ask_jarvis` | `(session_id, text)` | Send message to Jarvis via SSE stream, return full response text. | [src](../../../core/skills/voice/voice_test_full.py#L34) |
| function | `run_voice_loop` | `(session_id)` | — | [src](../../../core/skills/voice/voice_test_full.py#L65) |

## `core/skills/voice/wake_word.py`
_Wake word detection using webrtcvad + local Whisper (cloud fallback)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_get_elevenlabs_key` | `()` | — | [src](../../../core/skills/voice/wake_word.py#L52) |
| function | `_get_local_whisper` | `()` | Load faster-whisper once and cache. Returns None if import fails. | [src](../../../core/skills/voice/wake_word.py#L62) |
| function | `_transcribe_local` | `(frames)` | Transcribe with local faster-whisper. Returns None on error. | [src](../../../core/skills/voice/wake_word.py#L82) |
| function | `_transcribe_elevenlabs` | `(frames)` | Fallback: send audio to ElevenLabs STT. Returns None on error. | [src](../../../core/skills/voice/wake_word.py#L100) |
| function | `_clean_transcript` | `(text)` | Strip sound-effect artefacts like '(background noise)'. | [src](../../../core/skills/voice/wake_word.py#L126) |
| function | `_frames_to_wav_bytes` | `(frames)` | Encode raw PCM frames as a WAV byte string (for HF inference). | [src](../../../core/skills/voice/wake_word.py#L134) |
| function | `_transcribe_hf` | `(frames)` | Primary: HF Whisper-large-v3 (free, best quality). None on error. | [src](../../../core/skills/voice/wake_word.py#L145) |
| function | `_transcribe` | `(frames)` | ElevenLabs Scribe primary, local tiny offline fallback. | [src](../../../core/skills/voice/wake_word.py#L179) |
| function | `_is_wake_word` | `(text)` | — | [src](../../../core/skills/voice/wake_word.py#L199) |
| function | `get_shared_stdout` | `()` | Return the currently open parec stdout pipe, or None if not listening. | [src](../../../core/skills/voice/wake_word.py#L206) |
| function | `listen` | `(callback=…, interrupt_event=…)` | Continuously listen for 'Hey Jarvis'. | [src](../../../core/skills/voice/wake_word.py#L215) |
| function | `_trigger` | `(proc, callback, interrupt_event)` | Handle wake word: run callback while keeping parec stream alive. | [src](../../../core/skills/voice/wake_word.py#L291) |
| function | `_drain_pipe` | `(stdout)` | Non-blocking drain of any pending bytes in stdout. Returns bytes dropped. | [src](../../../core/skills/voice/wake_word.py#L305) |

## `core/skills/voice/wake_word_parec.py`
_Wake word detection using parec (PipeWire/PulseAudio) for audio capture._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `listen` | `(callback=…, interrupt_event=…, wake_words=…)` | Stream mic audio via parec and run openwakeword on each 80ms frame. | [src](../../../core/skills/voice/wake_word_parec.py#L18) |

