import { useCallback, useEffect, useRef, useState } from 'react'
import {
  useAudioRecorder, setAudioModeAsync,
  requestRecordingPermissionsAsync, RecordingPresets,
} from 'expo-audio'
import type { RecordingStatus } from 'expo-audio'
import { takeSpeakable } from './speechQueue'
import { useSpeechPlayer } from './useSpeechPlayer'
import type { ApiConfig } from './types'
import type { ContentBlock } from './sseProtocol'
import { transcribeAudio } from './voiceApi'

/** Samtale-mode. Tilstandsmaskine hvile→lyt→transskriber→tænk→tal→(loop).
 *  STT→/transcribe, TTS→ElevenLabs via useSpeechPlayer. Push-to-talk + hænderfri
 *  med VAD. Fejl → idle MED en grund; brækker aldrig UI. */

export type VoiceState = 'idle' | 'listening' | 'transcribing' | 'thinking' | 'speaking'
export type VoiceMode = 'push' | 'hands-free'

const _SILENCE_MS = 1300
const _MAX_UTTERANCE_MS = 30000
const _SPEECH_DB = -35
/** Hvor mange tomme runder hænderfri prøver igen efter, før den holder inde.
 *  Nul ville betyde at én pause afsluttede samtalen — så var den ikke
 *  hænderfri. Uendeligt ville betyde en mikrofon der står åben i stuen resten
 *  af dagen. Én ekstra runde er pausen man holder når man tænker. */
const _EMPTY_ROUNDS = 1

/** Måleren kommer i dB (-160..0). Tale ligger typisk mellem -45 og -10, så
 *  det er DET spænd kuglen skal reagere på — ikke hele skalaen, hvor almindelig
 *  tale ville se ud som næsten ingenting. */
function levelFromDb(db: number): number {
  return Math.max(0, Math.min(1, (db + 48) / 38))
}

export interface VoiceStreamDeps {
  status: string
  blocks: ContentBlock[]
  sendMessage: (text: string) => void
  extractText: (blocks: ContentBlock[]) => string
}

export function useVoiceConversation(config: ApiConfig | null | undefined, deps: VoiceStreamDeps) {
  const [state, setState] = useState<VoiceState>('idle')
  const [mode, setMode] = useState<VoiceMode>('hands-free')
  const [active, setActive] = useState(false)
  const [level, setLevel] = useState(0)
  const [problem, setProblem] = useState<string>('')

  const awaitingRef = useRef(false)
  const sawWorkingRef = useRef(false)
  const activeRef = useRef(active)
  const modeRef = useRef(mode)
  const sawSpeechRef = useRef(false)
  // Optageren KØRER (native), uafhængigt af hvad React har nået at rendere.
  // Og: brugeren HOLDER knappen. De to skal spørges med refs, ikke med state —
  // se startListening for hvorfor.
  const recordingRef = useRef(false)
  const wantRef = useRef(false)
  const silenceAtRef = useRef(0)
  const startedAtRef = useRef(0)
  const emptyRoundsRef = useRef(0)
  const stopListeningRef = useRef<(() => Promise<void>) | undefined>(undefined)
  const startListeningRef = useRef<(() => Promise<void>) | undefined>(undefined)

  useEffect(() => { activeRef.current = active }, [active])
  useEffect(() => { modeRef.current = mode }, [mode])

  // Talen er færdig. I hænderfri lytter vi igen med det samme — det er dét der
  // gør det til en samtale frem for en række enkeltbeskeder.
  const onSpoken = useCallback(() => {
    setState('idle')
    if (activeRef.current && modeRef.current === 'hands-free') {
      setTimeout(() => { void startListeningRef.current?.() }, 350)
    }
  }, [])
  const speech = useSpeechPlayer(config, onSpoken)

  // VAD-status-listener (hænderfri): auto-stop efter tale + stilhed. Samme
  // strøm giver niveauet til kuglen.
  const onRecStatus = useCallback((status: RecordingStatus) => {
    if (!recordingRef.current) return
    const db = (status as unknown as { metering?: number }).metering ?? -160
    setLevel(levelFromDb(db))
    if (modeRef.current !== 'hands-free') return
    const now = Date.now()
    if (db > _SPEECH_DB) { sawSpeechRef.current = true; silenceAtRef.current = 0 }
    else if (sawSpeechRef.current) {
      if (!silenceAtRef.current) silenceAtRef.current = now
      else if (now - silenceAtRef.current > _SILENCE_MS) { void stopListeningRef.current?.() }
    }
    if (startedAtRef.current && now - startedAtRef.current > _MAX_UTTERANCE_MS) void stopListeningRef.current?.()
  }, [])

  const recorder = useAudioRecorder(
    {
      ...RecordingPresets.HIGH_QUALITY,
      isMeteringEnabled: true,
      // Androids optagekilde til TALEGENKENDELSE. Standardkilden («mic») kører
      // automatisk niveaustyring beregnet på musik og optagelser, og den
      // pumper baggrundsstøj op i pauserne — netop dét whisper tager fejl af.
      // `voice_recognition` slår den styring fra og lader støjreduktionen stå.
      android: { ...RecordingPresets.HIGH_QUALITY.android, audioSource: 'voice_recognition' },
    },
    onRecStatus,
  )

  // Svaret læses højt MENS det skrives. Det er ikke pynt: på et langt svar er
  // ventetiden ellers mange sekunders tavshed, og i en samtale ligner tavshed
  // at noget er gået i stykker.
  //
  // Teksten skal opsamles undervejs, for klienten rydder blokkene i SAMME
  // opdatering som den sætter status til 'done' (persistAssistantSnapshot:
  // `{ ...prev, status, blocks: [] }`) — svaret flyttes over i den persisterede
  // historik. Læser man først dér, er der intet tilbage.
  const lastTextRef = useRef('')
  const takenRef = useRef(0)
  useEffect(() => {
    if (!awaitingRef.current) return
    const full = deps.extractText(deps.blocks)
    if (deps.status === 'working') {
      sawWorkingRef.current = true
      if (full) lastTextRef.current = full
      const r = takeSpeakable(lastTextRef.current, takenRef.current, false)
      takenRef.current = r.taken
      if (r.chunks.length) {
        r.chunks.forEach(speech.enqueue)
        setState('speaking')
      }
      return
    }
    // ALT andet end 'working' er slut. Kun 'done' og 'idle' ville efterlade
    // stemmen ventende for evigt på et afbrudt eller fejlet run — og NÆSTE
    // svar ville så blive talt i stedet for dette.
    if (sawWorkingRef.current) {
      awaitingRef.current = false
      sawWorkingRef.current = false
      const r = takeSpeakable(full || lastTextRef.current, takenRef.current, true)
      r.chunks.forEach(speech.enqueue)
      takenRef.current = 0
      lastTextRef.current = ''
      speech.finish()
    }
  }, [deps.status, deps.blocks, deps, speech])

  const stopListening = useCallback(async () => {
    wantRef.current = false
    if (!recordingRef.current) return
    recordingRef.current = false
    setLevel(0)
    try {
      await recorder.stop()
      const uri = recorder.uri
      if (!uri || !config) {
        setProblem('Der kom ingen optagelse ud af mikrofonen.')
        setState('idle'); return
      }
      setState('transcribing')
      const r = await transcribeAudio(config, uri)
      // «Tom optagelse» og «du sagde ikke noget» så ens ud, og det er netop
      // forskellen på en fejl og på stilhed. Serveren skelner allerede.
      if (r.status !== 'ok') {
        setProblem(`Lyden nåede frem, men kunne ikke bruges (${r.error || 'ukendt grund'}).`)
        setState('idle'); return
      }
      const text = (r.text || '').trim()
      if (!text) {
        setProblem('Jeg hørte ikke noget.')
        setState('idle')
        // En pause må ikke afslutte samtalen — men mikrofonen må heller ikke
        // stå åben i det uendelige, så der er en grænse.
        if (activeRef.current && modeRef.current === 'hands-free'
            && emptyRoundsRef.current < _EMPTY_ROUNDS) {
          emptyRoundsRef.current += 1
          setTimeout(() => { void startListeningRef.current?.() }, 400)
        } else {
          emptyRoundsRef.current = 0
        }
        return
      }
      emptyRoundsRef.current = 0
      setState('thinking')
      takenRef.current = 0
      lastTextRef.current = ''
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
    // tryk kunne nå at blive sluppet inden da. stopListening spurgte før React'
    // tilstand, som endnu stod på 'idle', og gjorde derfor ingenting — så
    // optagelsen kørte videre for evigt bag et overlay der sagde «Lytter…».
    // Et hurtigt tryk er den mest almindelige måde at trykke på en knap.
    wantRef.current = true
    // At begynde at lytte er også at afbryde. Køen smides væk her, så et svar
    // han er blevet træt af ikke fortsætter oven i det næste spørgsmål.
    speech.stop()
    awaitingRef.current = false
    sawWorkingRef.current = false
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
  }, [config, recorder, speech])
  useEffect(() => { startListeningRef.current = startListening }, [startListening])

  /** Afbryd ham midt i et svar. I hænderfri går vi direkte over til at lytte —
   *  det er dét man vil, når man afbryder nogen. */
  const interrupt = useCallback(() => {
    speech.stop()
    awaitingRef.current = false
    sawWorkingRef.current = false
    takenRef.current = 0
    lastTextRef.current = ''
    setState('idle')
    if (modeRef.current === 'hands-free') void startListeningRef.current?.()
  }, [speech])

  const enter = useCallback(() => { setActive(true); setProblem(''); setState('idle') }, [])
  const exit = useCallback(() => {
    setActive(false)
    awaitingRef.current = false
    sawWorkingRef.current = false
    takenRef.current = 0
    lastTextRef.current = ''
    speech.stop()
    void stopListeningRef.current?.()
    setState('idle')
  }, [speech])

  // Afspilningen ejer 'speaking'. Uden dette ville kuglen falde til ro mellem
  // to sætninger, selv om han stadig er midt i et svar.
  const shown: VoiceState = speech.speaking && state !== 'listening' ? 'speaking' : state

  return {
    active, state: shown, mode, level, problem,
    lastProvider: speech.provider,
    setMode, enter, exit, interrupt, startListening, stopListening,
  }
}
