import { useCallback, useEffect, useRef, useState } from 'react'
import {
  useAudioRecorder, createAudioPlayer, setAudioModeAsync,
  requestRecordingPermissionsAsync, RecordingPresets,
} from 'expo-audio'
import type { AudioPlayer, RecordingStatus } from 'expo-audio'
import * as Speech from 'expo-speech'
import { clampForSpeech, stripForSpeech } from './speechText'
import type { ApiConfig } from './types'
import type { ContentBlock } from './sseProtocol'
import { transcribeAudio, synthesizeTtsToFile } from './voiceApi'

/** Samtale-mode (Trin 3, mobil). expo-audio (New-Arch-kompatibel — expo-av crashede under
 *  newArchEnabled). Tilstandsmaskine hvile→lyt→transskriber→tænk→tal→(loop). STT→/transcribe,
 *  TTS-fil→/api/tts (ElevenLabs), expo-speech da-DK som device-fallback. Push-to-talk + VAD.
 *  Self-safe: fejl → idle, brækker aldrig UI. */

export type VoiceState = 'idle' | 'listening' | 'transcribing' | 'thinking' | 'speaking'
export type VoiceMode = 'push' | 'hands-free'

const _SILENCE_MS = 1300
const _MAX_UTTERANCE_MS = 30000
const _SPEECH_DB = -35

export interface VoiceStreamDeps {
  status: string
  blocks: ContentBlock[]
  sendMessage: (text: string) => void
  extractText: (blocks: ContentBlock[]) => string
}

export function useVoiceConversation(config: ApiConfig | null | undefined, deps: VoiceStreamDeps) {
  const [state, setState] = useState<VoiceState>('idle')
  const [mode, setMode] = useState<VoiceMode>('push')
  const [active, setActive] = useState(false)
  const [lastProvider, setLastProvider] = useState('')

  const playerRef = useRef<AudioPlayer | null>(null)
  const awaitingRef = useRef(false)
  const sawWorkingRef = useRef(false)
  const activeRef = useRef(active)
  const modeRef = useRef(mode)
  const stateRef = useRef<VoiceState>(state)
  const sawSpeechRef = useRef(false)
  // Optageren KØRER (native), uafhængigt af hvad React har nået at rendere.
  // Og: brugeren HOLDER knappen. De to skal spørges med refs, ikke med state —
  // se startListening for hvorfor.
  const recordingRef = useRef(false)
  const wantRef = useRef(false)
  const silenceAtRef = useRef(0)
  const startedAtRef = useRef(0)
  const stopListeningRef = useRef<(() => Promise<void>) | undefined>(undefined)
  const startListeningRef = useRef<(() => Promise<void>) | undefined>(undefined)

  useEffect(() => { activeRef.current = active }, [active])
  useEffect(() => { modeRef.current = mode }, [mode])
  useEffect(() => { stateRef.current = state }, [state])

  // VAD-status-listener (hænderfri): auto-stop efter tale + stilhed. Best-effort.
  const onRecStatus = useCallback((status: RecordingStatus) => {
    if (modeRef.current !== 'hands-free' || !recordingRef.current) return
    const now = Date.now()
    const db = (status as unknown as { metering?: number }).metering ?? -160
    if (db > _SPEECH_DB) { sawSpeechRef.current = true; silenceAtRef.current = 0 }
    else if (sawSpeechRef.current) {
      if (!silenceAtRef.current) silenceAtRef.current = now
      else if (now - silenceAtRef.current > _SILENCE_MS) { void stopListeningRef.current?.() }
    }
    if (startedAtRef.current && now - startedAtRef.current > _MAX_UTTERANCE_MS) void stopListeningRef.current?.()
  }, [])

  const recorder = useAudioRecorder(
    { ...RecordingPresets.HIGH_QUALITY, isMeteringEnabled: true },
    onRecStatus,
  )

  // HVORFOR det gik i stå. Hver fejl-gren satte før bare state='idle', så
  // overlayet blinkede tilbage uden et ord — og «det virker ikke» er den
  // eneste konklusion man kan drage af tavshed. Nu står grunden på skærmen.
  const [problem, setProblem] = useState<string>('')

  const _speakNative = useCallback((text: string, onDone: () => void) => {
    try { setLastProvider('device'); Speech.speak(text, { language: 'da-DK', onDone, onError: onDone }) }
    catch { onDone() }
  }, [])

  const _speak = useCallback(async (text: string) => {
    if (!text) { setState('idle'); return }
    setState('speaking')
    const onDone = () => {
      setState('idle')
      if (activeRef.current && modeRef.current === 'hands-free') {
        setTimeout(() => { void startListeningRef.current?.() }, 300)
      }
    }
    try {
      if (!config) throw new Error('no config')
      // Renset FØR syntesen. Uden dette siger han «stjerne stjerne vigtigt» og
      // staver kodeblokke — samme fejl som oplæsningsknappen havde.
      // Slip optage-tilstanden FØR afspilning. Bliver allowsRecording stående
      // på true, holder systemet lydsessionen i optage-mode, og svaret kommer
      // ud af øresneglen i stedet for højttaleren — hørbart som «han svarer
      // ikke», selv når alt andet virker.
      try { await setAudioModeAsync({ allowsRecording: false, playsInSilentMode: true }) }
      catch { /* ikke fatalt — afspil alligevel */ }
      const { uri, provider } = await synthesizeTtsToFile(config, clampForSpeech(stripForSpeech(text)))
      setLastProvider(provider)
      try { playerRef.current?.remove() } catch { /* noop */ }
      const player = createAudioPlayer({ uri })
      playerRef.current = player
      player.addListener('playbackStatusUpdate', (s) => {
        if (s.didJustFinish) { try { player.remove() } catch { /* noop */ } onDone() }
      })
      player.play()
    } catch {
      _speakNative(clampForSpeech(stripForSpeech(text)), onDone)
    }
  }, [config, _speakNative])

  // Completion-watch: tal svaret når et run vi startede falder fra 'working'.
  useEffect(() => {
    if (!awaitingRef.current) return
    if (deps.status === 'working') { sawWorkingRef.current = true; return }
    if (sawWorkingRef.current && (deps.status === 'done' || deps.status === 'idle')) {
      awaitingRef.current = false
      sawWorkingRef.current = false
      void _speak(deps.extractText(deps.blocks))
    }
  }, [deps.status, deps.blocks, deps, _speak])

  const stopListening = useCallback(async () => {
    wantRef.current = false
    if (!recordingRef.current) return
    recordingRef.current = false
    try {
      await recorder.stop()
      const uri = recorder.uri
      if (!uri || !config) {
        setProblem('Der kom ingen optagelse ud af mikrofonen.')
        setState('idle'); return
      }
      setState('transcribing')
      const r = await transcribeAudio(config, uri)
      // «Tom optagelse» og «du sagde ikke noget» så ens ud herinde, og det er
      // netop forskellen på en fejl og på stilhed. Serveren skelner allerede —
      // den svarer status='error' med en grund når filen intet indeholder —
      // så den grund skal med op, ellers fejlsøger man i blinde.
      if (r.status !== 'ok') {
        setProblem(`Lyden nåede frem, men kunne ikke bruges (${r.error || 'ukendt grund'}).`)
        setState('idle'); return
      }
      const text = (r.text || '').trim()
      if (!text) {
        // Tomt resultat er IKKE en fejl — man kan have tiet. Men brugeren skal
        // vide at der ikke blev opfattet noget, ellers ligner det en død knap.
        setProblem('Jeg hørte ikke noget. Prøv igen.')
        setState('idle'); return
      }
      setState('thinking')
      awaitingRef.current = true
      deps.sendMessage(text)
    } catch (e) {
      setProblem(`Kunne ikke forstå lyden (${(e as Error)?.message || 'ukendt fejl'}).`)
      setState('idle')
    }
  }, [config, deps, recorder])
  useEffect(() => { stopListeningRef.current = stopListening }, [stopListening])

  const startListening = useCallback(async () => {
    if (!config || recordingRef.current) return
    // Trykket registreres FØR den asynkrone opstart. At bede om
    // mikrofon-tilladelse og forberede optageren tager et øjeblik, og et kort
    // tryk kunne nå at blive sluppet inden da. stopListening spurgte React'
    // tilstand, som endnu stod på 'idle', og gjorde derfor ingenting — så
    // optagelsen kørte videre for evigt bag et overlay der sagde «Lytter…».
    // Et hurtigt tryk er den mest almindelige måde at trykke på en knap.
    wantRef.current = true
    try { playerRef.current?.pause() } catch { /* noop */ }
    try { Speech.stop() } catch { /* noop */ }
    setProblem('')
    try {
      const perm = await requestRecordingPermissionsAsync()
      if (!perm.granted) {
        wantRef.current = false
        setProblem('Jeg må ikke bruge mikrofonen. Giv appen adgang i telefonens indstillinger.')
        setState('idle'); return
      }
      await setAudioModeAsync({ allowsRecording: true, playsInSilentMode: true })
      sawSpeechRef.current = false
      silenceAtRef.current = 0
      startedAtRef.current = Date.now()
      await recorder.prepareToRecordAsync()
      recorder.record()
      recordingRef.current = true
      setState('listening')
      // Nået at slippe imens? Så stop nu — ellers hænger optagelsen.
      if (!wantRef.current && modeRef.current === 'push') void stopListeningRef.current?.()
    } catch (e) {
      wantRef.current = false
      recordingRef.current = false
      setProblem(`Kunne ikke starte optagelsen (${(e as Error)?.name || 'ukendt fejl'}).`)
      setState('idle')
    }
  }, [config, recorder])
  useEffect(() => { startListeningRef.current = startListening }, [startListening])

  const enter = useCallback(() => { setActive(true); setProblem(''); setState('idle') }, [])
  const exit = useCallback(() => {
    setActive(false)
    awaitingRef.current = false
    try { playerRef.current?.pause() } catch { /* noop */ }
    try { Speech.stop() } catch { /* noop */ }
    void stopListeningRef.current?.()
    setState('idle')
  }, [])

  return { active, state, mode, lastProvider, problem, setMode, enter, exit, startListening, stopListening }
}
