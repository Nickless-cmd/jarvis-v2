# Voice / Samtale-mode i begge apps (2026-07-10)

Naturlig tale-samtale med Jarvis i desk + mobil. ElevenLabs (hans danske stemme) primær,
native fallback. Motorer + endpoints findes allerede — mangler ElevenLabs-wire + app-UI.

## Arkitektur: tynd delt server, smart klient
- **Server-side (delt backend):** STT `/transcribe` (whisper, findes) · TTS `/tts/synthesize`
  (skal: ElevenLabs primær + edge-tts fallback) · Chat (findes, streaming).
- **Klient-side (hver app):** mic-capture · de 3 input-modes · samtale-tilstandsmaskine
  (hvile→vågn→lyt→transskriber→tænk→tal→lyt) · afspilning + device-native TTS-fallback.
- **Hvorfor klient-tungt loop:** wake-word + VAD kræver kontinuerlig LOKAL lyd (kan ikke
  streame rå mic 24/7). Turn-taking bedst lokalt. Server forbliver simpel + delt.

## Fallback-lag ("native som fallback")
- TTS: ElevenLabs → edge-tts (backend) → device-native (Web Speech / expo-speech) hvis backend nede.
- STT: whisper (`/transcribe`) → device-native STT hvis backend nede.

## De 3 input-modes (alle klient-side, samme loop)
1. **Push-to-talk:** knap start/stop optagelse.
2. **Hænderfri (VAD):** auto-detektér tale-slut → send selv.
3. **Wake-word ("Hey Jarvis"):** kontinuerlig lytning → så VAD. SVÆREST: Electron kan ikke
   Web Speech → kræver native lib (Picovoice Porcupine, access-key) i BEGGE apps. Sidst.

## Trin (begge apps, alle 3 modes)
### Trin 1 — Backend: ElevenLabs-wire i `/tts/synthesize` (DENNE commit)
- ElevenLabs primær (Jarvis' "Mathias" da-voice, model eleven_flash_v2_5) → edge-tts fallback.
- Robust: hvis ingen nøgle / credits ude / fejl → auto-fallback edge-tts (ingen breakage —
  routen erstattede ELEVENLABS pga credits-out; nu ELEVENLABS-først-med-fallback).
- `provider` request-felt: auto (default) | elevenlabs | edge. Runtime-flag `tts_prefer_elevenlabs`
  (default True) så credits kan spares uden kode-ændring. `X-TTS-Provider`-header i svar.
- Genbruger `core.skills.voice.tts._get_elevenlabs_key` + voice_id (ingen dobbelt nøgle-læsning).

### Trin 2 — Delt loop + desk-UI (push-to-talk + VAD)
- `useVoiceConversation()` hook: tilstandsmaskine + mic (MediaRecorder) + /transcribe + chat + /tts.
- Samtale-mode-skærm/toggle i desk. VAD via lyd-metering (hark el. AudioContext-analyser).

### Trin 3 — Mobil-UI (expo-av): samme loop.
### Trin 4 — Wake-word-lag (Picovoice) i begge — separat, sidst.

## Governance / sikkerhed
- ElevenLabs-nøgle forbliver server-side (runtime.json) — aldrig i app.
- TTS-tekst er Jarvis' synlige svar (ikke privat-lag) → egress OK (det er allerede vist i chat).
- Mic-audio: sendes til `/transcribe` (owner-auth). Device-native STT/TTS holder lyd lokalt.

## Test
- Trin 1: curl /tts/synthesize → audio/mpeg + X-TTS-Provider=elevenlabs (nøgle sat) el. edge (fallback).
  Verificér ægte bytes + at fallback udløses når ElevenLabs fejler.
