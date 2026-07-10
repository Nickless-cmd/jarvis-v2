import { useCallback, useEffect, useRef, useState } from 'react'
import type { ApiConfig } from '../lib/api'
import { synthesizeTts, transcribeAudio } from '../lib/api'
import type { ContentBlock } from '../lib/sseProtocol'

/** Afkoblet fra StreamContext' SendOpts (kræver sessionId): kalderen giver en
 *  session-bundet sendMessage + eksponerer det aktive runs status/blocks. */
export interface VoiceStreamDeps {
  status: string
  blocks: ContentBlock[]
  sendMessage: (text: string) => void
}

/** Samtale-mode (Trin 2). Tilstandsmaskine: hvile → lyt → transskriber → tænk → tal → (loop).
 *
 *  - STT: MediaRecorder → /transcribe (whisper), samme sti som dikteringen.
 *  - Chat: stream.send() → vent på status falder fra 'working' → udtræk text-blocks.
 *  - TTS: /api/tts/synthesize (ElevenLabs primær) → afspil MP3. Fejler backend → device-native
 *    (window.speechSynthesis) som sidste fallback.
 *  - Modes: 'push' (hold/tryk) og 'hands-free' (VAD auto-stop). Wake-word = Trin 4.
 *
 *  Alt best-effort/self-safe: en fejl vender bare tilbage til 'idle', bryder aldrig UI'et. */

export type VoiceState = 'idle' | 'listening' | 'transcribing' | 'thinking' | 'speaking'
export type VoiceMode = 'push' | 'hands-free'

const _SILENCE_MS = 1200 // hands-free: så lang stilhed EFTER tale → auto-stop
const _MAX_UTTERANCE_MS = 30000 // hård kappe på én ytring
const _RMS_SPEECH = 0.015 // over dette = tale til stede

function _extractText(blocks: ContentBlock[]): string {
  return (blocks || [])
    .filter((b) => b && (b as { type?: string }).type === 'text')
    .map((b) => String((b as { text?: string }).text || ''))
    .join(' ')
    .trim()
}

export function useVoiceConversation(config: ApiConfig | undefined, deps: VoiceStreamDeps) {
  const [state, setState] = useState<VoiceState>('idle')
  const [mode, setMode] = useState<VoiceMode>('push')
  const [active, setActive] = useState(false)
  const [lastProvider, setLastProvider] = useState<string>('')

  const recRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const streamRef = useRef<MediaStream | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const awaitingRef = useRef(false)
  const sawWorkingRef = useRef(false)
  const activeRef = useRef(active)
  const modeRef = useRef(mode)
  const vadRafRef = useRef<number | null>(null)
  const acRef = useRef<AudioContext | null>(null)

  useEffect(() => { activeRef.current = active }, [active])
  useEffect(() => { modeRef.current = mode }, [mode])

  const supported =
    !!config &&
    typeof navigator !== 'undefined' &&
    !!navigator.mediaDevices?.getUserMedia &&
    typeof MediaRecorder !== 'undefined'

  const _cleanupMic = useCallback(() => {
    if (vadRafRef.current != null) { cancelAnimationFrame(vadRafRef.current); vadRafRef.current = null }
    try { acRef.current?.close() } catch { /* noop */ }
    acRef.current = null
    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null
  }, [])

  // ── TTS-afspilning (ElevenLabs → device-native fallback) ──────────────────
  const _speak = useCallback(async (text: string) => {
    if (!text) { setState('idle'); return }
    setState('speaking')
    const onDone = () => {
      setState('idle')
      // hands-free: loop tilbage til at lytte hvis stadig aktiv
      if (activeRef.current && modeRef.current === 'hands-free') {
        setTimeout(() => { void startListeningRef.current?.() }, 250)
      }
    }
    try {
      if (!config) throw new Error('no config')
      const { blob, provider } = await synthesizeTts(config, text)
      setLastProvider(provider)
      const url = URL.createObjectURL(blob)
      const audio = new Audio(url)
      audioRef.current = audio
      audio.onended = () => { URL.revokeObjectURL(url); onDone() }
      audio.onerror = () => { URL.revokeObjectURL(url); _speakNative(text, onDone) }
      await audio.play()
    } catch {
      _speakNative(text, onDone)
    }
  }, [config])

  const _speakNative = (text: string, onDone: () => void) => {
    try {
      const synth = window.speechSynthesis
      if (!synth) { onDone(); return }
      synth.cancel()
      const u = new SpeechSynthesisUtterance(text)
      u.lang = 'da-DK'
      u.onend = onDone
      u.onerror = onDone
      setLastProvider('device')
      synth.speak(u)
    } catch { onDone() }
  }

  // ── Completion-watch: når et run vi startede falder fra 'working' → tal svaret ─
  useEffect(() => {
    if (!awaitingRef.current) return
    // Kræv at vi HAR set 'working' før vi behandler idle/done som fuldførelse —
    // ellers ville den korte idle-periode LIGE efter send tale det gamle svar.
    if (deps.status === 'working') { sawWorkingRef.current = true; return }
    if (sawWorkingRef.current && (deps.status === 'done' || deps.status === 'idle')) {
      awaitingRef.current = false
      sawWorkingRef.current = false
      void _speak(_extractText(deps.blocks))
    }
  }, [deps.status, deps.blocks, _speak])

  // ── STT: send optaget lyd → transskriber → send til chat ──────────────────
  const _onRecordingStop = useCallback(async () => {
    _cleanupMic()
    const blob = new Blob(chunksRef.current, { type: recRef.current?.mimeType || 'audio/webm' })
    chunksRef.current = []
    if (blob.size === 0 || !config) { setState('idle'); return }
    setState('transcribing')
    try {
      const r = await transcribeAudio(config, blob)
      const text = (r.status === 'ok' ? r.text : '').trim()
      if (!text) { setState('idle'); return }
      setState('thinking')
      awaitingRef.current = true
      deps.sendMessage(text)
    } catch {
      setState('idle')
    }
  }, [config, _cleanupMic, deps])

  // ── VAD (hands-free): auto-stop efter tale + stilhed ──────────────────────
  const _startVad = useCallback((mediaStream: MediaStream) => {
    try {
      const AC = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
      const ac = new AC()
      acRef.current = ac
      const src = ac.createMediaStreamSource(mediaStream)
      const analyser = ac.createAnalyser()
      analyser.fftSize = 512
      src.connect(analyser)
      const buf = new Uint8Array(analyser.fftSize)
      let sawSpeech = false
      let silenceStart = 0
      const startedAt = Date.now()
      const tick = () => {
        analyser.getByteTimeDomainData(buf)
        let sum = 0
        for (let i = 0; i < buf.length; i++) { const v = ((buf[i] ?? 128) - 128) / 128; sum += v * v }
        const rms = Math.sqrt(sum / buf.length)
        const now = Date.now()
        if (rms > _RMS_SPEECH) { sawSpeech = true; silenceStart = 0 }
        else if (sawSpeech) { if (!silenceStart) silenceStart = now; else if (now - silenceStart > _SILENCE_MS) { stopListening(); return } }
        if (now - startedAt > _MAX_UTTERANCE_MS) { stopListening(); return }
        vadRafRef.current = requestAnimationFrame(tick)
      }
      vadRafRef.current = requestAnimationFrame(tick)
    } catch { /* VAD er best-effort; push-to-talk virker uden */ }
  }, [])

  const startListening = useCallback(async () => {
    if (!supported || !config || state === 'listening') return
    // afbryd evt. igangværende tale
    try { audioRef.current?.pause() } catch { /* noop */ }
    try { window.speechSynthesis?.cancel() } catch { /* noop */ }
    try {
      const ms = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = ms
      chunksRef.current = []
      const rec = new MediaRecorder(ms)
      rec.ondataavailable = (e) => { if (e.data && e.data.size > 0) chunksRef.current.push(e.data) }
      rec.onstop = () => { void _onRecordingStop() }
      recRef.current = rec
      rec.start()
      setState('listening')
      if (modeRef.current === 'hands-free') _startVad(ms)
    } catch {
      _cleanupMic()
      setState('idle')
    }
  }, [supported, config, state, _onRecordingStop, _startVad, _cleanupMic])

  const stopListening = useCallback(() => {
    if (recRef.current && recRef.current.state !== 'inactive') recRef.current.stop()
  }, [])

  // stabile refs så VAD/timeout kan kalde uden stale closures
  const startListeningRef = useRef(startListening)
  useEffect(() => { startListeningRef.current = startListening }, [startListening])

  const enter = useCallback(() => { setActive(true); setState('idle') }, [])
  const exit = useCallback(() => {
    setActive(false)
    awaitingRef.current = false
    try { audioRef.current?.pause() } catch { /* noop */ }
    try { window.speechSynthesis?.cancel() } catch { /* noop */ }
    stopListening()
    _cleanupMic()
    setState('idle')
  }, [stopListening, _cleanupMic])

  useEffect(() => () => { _cleanupMic() }, [_cleanupMic])

  return {
    supported, active, state, mode, lastProvider,
    setMode, enter, exit, startListening, stopListening,
  }
}
