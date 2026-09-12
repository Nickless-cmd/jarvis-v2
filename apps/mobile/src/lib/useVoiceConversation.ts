import { useCallback, useEffect, useRef, useState } from 'react'
import { Animated } from 'react-native'
import {
  useAudioRecorder, setAudioModeAsync,
  requestRecordingPermissionsAsync, RecordingPresets,
} from 'expo-audio'
import {
  bargeStep, freshLoud, freshWatch, levelFromDb, utteranceStep,
} from './voiceActivity'
import { takeSpeakable } from './speechQueue'
import { useSpeechPlayer } from './useSpeechPlayer'
import type { ApiConfig } from './types'
import type { ContentBlock } from './sseProtocol'
import { transcribeAudio } from './voiceApi'

/** Hænderfri samtale. Tilstandsmaskine hvile→lyt→transskriber→tænk→tal→(loop).
 *  STT→/transcribe, TTS→ElevenLabs via useSpeechPlayer. Fejl → idle MED en
 *  grund; brækker aldrig UI. Composer-diktering ejes af en separat hook. */

export type VoiceState = 'idle' | 'listening' | 'transcribing' | 'thinking' | 'speaking'

const _SILENCE_MS = 1300
const _MAX_UTTERANCE_MS = 30000
const _SPEECH_DB = -35
/** Hvor tit niveauet aflæses. Det SKAL hentes selv med getStatus(): status-
 *  tilbagekaldet på useAudioRecorder bærer ikke metering og fyrer først når
 *  optagelsen slutter — hænderfri var bygget på det og stoppede derfor aldrig. */
const _POLL_MS = 120
/** Afbrydelses-grænsen ligger HØJERE end tale-grænsen, fordi mikrofonen også
 *  hører Jarvis' egen stemme fra højttaleren. */
const _BARGE_DB = -22
const _BARGE_HOLD_MS = 420
/** Hvor mange tomme runder hænderfri prøver igen efter, før den holder inde.
 *  Nul ville betyde at én pause afsluttede samtalen — så var den ikke
 *  hænderfri. Uendeligt ville betyde en mikrofon der står åben i stuen resten
 *  af dagen. Én ekstra runde er pausen man holder når man tænker. */
const _EMPTY_ROUNDS = 1

export interface VoiceStreamDeps {
  status: string
  blocks: ContentBlock[]
  sendMessage: (text: string) => void
  extractText: (blocks: ContentBlock[]) => string
  /** Læs alle svar i den valgte samtale højt, også når de blev skrevet. */
  readAllResponses?: boolean
}

export function useVoiceConversation(config: ApiConfig | null | undefined, deps: VoiceStreamDeps) {
  const [state, setState] = useState<VoiceState>('idle')
  const [active, setActive] = useState(false)
  const [problem, setProblem] = useState<string>('')
  // Niveauet er en Animated.Value og ikke React-tilstand: det opdateres ~8
  // gange i sekundet, og at rendre hele skærmen så tit for at puste en kugle op
  // ville koste mere end den er værd.
  const level = useRef(new Animated.Value(0)).current

  const awaitingRef = useRef(false)
  const sawWorkingRef = useRef(false)
  const activeRef = useRef(active)
  // Optageren KØRER (native), uafhængigt af hvad React har nået at rendere.
  // Og: brugeren HOLDER knappen. De to skal spørges med refs, ikke med state —
  // se startListening for hvorfor.
  const recordingRef = useRef(false)
  const wantRef = useRef(false)
  const startedAtRef = useRef(0)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const bargeRef = useRef<ReturnType<typeof setInterval> | null>(null)
  // Blev overvågeren faktisk sat i gang? Uden dette ville stop() blive kaldt på
  // en optager der aldrig kørte, hver gang samtalen skiftede tilstand.
  const monitorOnRef = useRef(false)
  const interruptRef = useRef<(() => void) | undefined>(undefined)
  const emptyRoundsRef = useRef(0)
  const stopListeningRef = useRef<(() => Promise<void>) | undefined>(undefined)
  const startListeningRef = useRef<(() => Promise<void>) | undefined>(undefined)

  useEffect(() => { activeRef.current = active }, [active])

  // Talen er færdig. I hænderfri lytter vi igen med det samme — det er dét der
  // gør det til en samtale frem for en række enkeltbeskeder.
  const onSpoken = useCallback(() => {
    setState('idle')
    if (activeRef.current) {
      setTimeout(() => { void startListeningRef.current?.() }, 350)
    }
  }, [])
  const speech = useSpeechPlayer(config, onSpoken)

  // Optageren der fanger DET DU SIGER. Androids kilde til TALEGENKENDELSE:
  // standardkilden («mic») kører niveaustyring beregnet på musik og pumper
  // baggrundsstøj op i pauserne — netop dét whisper tager fejl af.
  const recorder = useAudioRecorder({
    ...RecordingPresets.HIGH_QUALITY,
    isMeteringEnabled: true,
    android: { ...RecordingPresets.HIGH_QUALITY.android, audioSource: 'voice_recognition' },
  })

  // En ANDEN optager, der kun lytter efter om du taler hen over ham. Den bruger
  // `voice_communication`, som tænder telefonens ekkoannullering — uden den
  // ville mikrofonen høre Jarvis' egen stemme fra højttaleren og afbryde ham
  // konstant. De to kører aldrig samtidig: den ene mens du taler, den anden
  // mens han taler. Derfor to instanser i stedet for én med skiftende kilde,
  // som ikke kan ændres efter oprettelsen.
  const monitor = useAudioRecorder({
    ...RecordingPresets.HIGH_QUALITY,
    isMeteringEnabled: true,
    android: { ...RecordingPresets.HIGH_QUALITY.android, audioSource: 'voice_communication' },
  })

  const meterOf = (r: unknown): number =>
    (r as { getStatus?: () => { metering?: number } }).getStatus?.().metering ?? -160

  const stopPoll = useCallback(() => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null }
  }, [])
  const stopBarge = useCallback(() => {
    if (bargeRef.current) { clearInterval(bargeRef.current); bargeRef.current = null }
    if (!monitorOnRef.current) return
    monitorOnRef.current = false
    try { void monitor.stop() } catch { /* nåede at stoppe af sig selv */ }
  }, [monitor])

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
    if (!deps.readAllResponses || activeRef.current || deps.status !== 'working') return
    if (!awaitingRef.current) {
      awaitingRef.current = true
      sawWorkingRef.current = false
      takenRef.current = 0
      lastTextRef.current = ''
    }
  }, [deps.readAllResponses, deps.status])

  useEffect(() => {
    if (!awaitingRef.current) return
    const full = deps.extractText(deps.blocks)
    if (deps.status === 'working') {
      sawWorkingRef.current = true
      if (full) {
        // Et svar med værktøjskald kommer i FLERE runder, og hver runde
        // nulstiller blokkene (`message_start` → `blocks: []`). Teksten
        // begynder altså forfra, mens min optælling af «hvor langt er jeg
        // nået» pegede ind i den forrige runde. Resultatet var at intet blev
        // sagt undervejs — og at slutningen kunne blive læst op fra midten.
        //
        // Kendetegnet er at den nye tekst ikke er en forlængelse af den gamle.
        if (!full.startsWith(lastTextRef.current.slice(0, takenRef.current))) {
          takenRef.current = 0
        }
        lastTextRef.current = full
      }
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
      const final = full || lastTextRef.current
      // Samme vagt ved afslutningen: peger optællingen ud over den tekst der
      // faktisk står her, ville resten blive sprunget over i stilhed.
      const from = final.startsWith(lastTextRef.current.slice(0, takenRef.current))
        ? takenRef.current : 0
      const r = takeSpeakable(final, from, true)
      r.chunks.forEach(speech.enqueue)
      takenRef.current = 0
      lastTextRef.current = ''
      speech.finish()
    }
  }, [deps.status, deps.blocks, deps, speech])

  /**
   * Pulsslaget mens DU taler. Det henter niveauet selv, fordi optagerens
   * status-tilbagekald ikke bærer metering — se voiceActivity.ts.
   *
   * Maks-længden ligger her og gælder BEGGE tilstande: også et fastholdt tryk
   * skal have en ende, ellers kan mikrofonen stå åben ubemærket.
   */
  const startCapturePoll = useCallback(() => {
    stopPoll()
    let watch = freshWatch()
    let smooth = 0
    pollRef.current = setInterval(() => {
      if (!recordingRef.current) { stopPoll(); return }
      const db = meterOf(recorder)
      // Udjævnet, fordi målingerne kommer i spring — et spring i kuglens
      // størrelse ville læses som en fejl frem for som din stemme.
      smooth += (levelFromDb(db) - smooth) * 0.4
      level.setValue(smooth)
      const now = Date.now()
      const r = utteranceStep(watch, db, now, { speechDb: _SPEECH_DB, silenceMs: _SILENCE_MS })
      watch = r.watch
      if (r.ended) { void stopListeningRef.current?.(); return }
      if (now - startedAtRef.current > _MAX_UTTERANCE_MS) void stopListeningRef.current?.()
    }, _POLL_MS)
  }, [recorder, stopPoll, level])

  /** Pulsslaget mens HAN taler: hører efter om du taler hen over ham. */
  const startBargePoll = useCallback(async () => {
    if (bargeRef.current) return
    try {
      await monitor.prepareToRecordAsync()
      monitor.record()
      monitorOnRef.current = true
    } catch { return }   // kan ikke lytte imens — så kan man trykke i stedet
    let watch = freshLoud()
    bargeRef.current = setInterval(() => {
      const r = bargeStep(watch, meterOf(monitor), Date.now(), {
        bargeDb: _BARGE_DB, holdMs: _BARGE_HOLD_MS,
      })
      watch = r.watch
      if (r.hit) interruptRef.current?.()
    }, _POLL_MS)
  }, [monitor])

  const stopListening = useCallback(async () => {
    wantRef.current = false
    if (!recordingRef.current) return
    recordingRef.current = false
    stopPoll()
    level.setValue(0)
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
        if (activeRef.current && emptyRoundsRef.current < _EMPTY_ROUNDS) {
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
  }, [config, deps, recorder, stopPoll, level])
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
    stopBarge()
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
      await setAudioModeAsync({
        allowsRecording: true,
        playsInSilentMode: true,
        // Svaret skal ud af HØJTTALEREN. Uden dette kan lyden havne i
        // øresneglen, når sessionen står i optage-tilstand — hørbart som «han
        // svarer ikke», selv når alt andet virker.
        shouldRouteThroughEarpiece: false,
      })
      startedAtRef.current = Date.now()
      await recorder.prepareToRecordAsync()
      recorder.record()
      recordingRef.current = true
      setState('listening')
      startCapturePoll()
      // Nået at slippe imens? Så stop nu — ellers hænger optagelsen.
      if (!wantRef.current) void stopListeningRef.current?.()
    } catch (e) {
      wantRef.current = false
      recordingRef.current = false
      setProblem(`Kunne ikke starte optagelsen (${(e as Error)?.name || 'ukendt fejl'}).`)
      setState('idle')
    }
  }, [config, recorder, speech, startCapturePoll, stopBarge])
  useEffect(() => { startListeningRef.current = startListening }, [startListening])

  // Lyt efter afbrydelse mens han taler i hænderfri samtale.
  useEffect(() => {
    if (speech.speaking && active) void startBargePoll()
    else stopBarge()
  }, [speech.speaking, active, startBargePoll, stopBarge])

  useEffect(() => () => { stopPoll(); stopBarge() }, [stopPoll, stopBarge])

  /** Afbryd ham midt i et svar. I hænderfri går vi direkte over til at lytte —
   *  det er dét man vil, når man afbryder nogen. */
  const interrupt = useCallback(() => {
    stopBarge()
    speech.stop()
    awaitingRef.current = false
    sawWorkingRef.current = false
    takenRef.current = 0
    lastTextRef.current = ''
    setState('idle')
    void startListeningRef.current?.()
  }, [speech, stopBarge])
  useEffect(() => { interruptRef.current = interrupt }, [interrupt])

  const enter = useCallback(() => {
    setActive(true)
    setProblem('')
    setState('idle')
    // Samtalen skal begynde af sig selv. Uden dette åbner overlayet i 'idle',
    // og man skal først trykke på kuglen før mikrofonen overhovedet tændes —
    // så et tryk på lydbølge-ikonet ser ud som om der ikke skete noget.
    // Kort ventetid, så overlayet (og mikrofon-tilladelsen) når at vise sig.
    setTimeout(() => {
      // Lukkede han igen inden da, må mikrofonen ikke tændes bag et lukket
      // overlay. Tjekket ligger EFTER ventetiden — det er hele pointen med den.
      if (activeRef.current) void startListeningRef.current?.()
    }, 350)
  }, [])
  const exit = useCallback(() => {
    setActive(false)
    stopPoll()
    stopBarge()
    awaitingRef.current = false
    sawWorkingRef.current = false
    takenRef.current = 0
    lastTextRef.current = ''
    speech.stop()
    void stopListeningRef.current?.()
    setState('idle')
  }, [speech, stopPoll, stopBarge])

  // Afspilningen ejer 'speaking'. Uden dette ville kuglen falde til ro mellem
  // to sætninger, selv om han stadig er midt i et svar.
  const shown: VoiceState = speech.speaking && state !== 'listening' ? 'speaking' : state

  return {
    active, state: shown, level, problem,
    lastProvider: speech.provider,
    enter, exit, interrupt, startListening, stopListening,
  }
}
