import { useCallback, useEffect, useRef, useState } from 'react'
import { createAudioPlayer } from 'expo-audio'
import type { AudioPlayer } from 'expo-audio'
import * as Speech from 'expo-speech'
import { clampForSpeech, stripForSpeech } from './speechText'
import { synthesizeTtsToFile } from './voiceApi'
import type { ApiConfig } from './types'

/**
 * En kø af replikker der siges i rækkefølge, mens svaret stadig skrives.
 *
 * Køen findes for at holde ÉN ting adskilt: hvad der bliver sagt hvornår.
 * Samtale-tilstandsmaskinen skal kunne aflevere en sætning og gå videre uden at
 * vide om der stadig spilles noget, og uden at risikere at to stykker spiller
 * oven i hinanden.
 *
 * Næste stykke bliver syntetiseret MENS det forrige spiller. Uden det ville der
 * være et hul ved hver sætningsgrænse på størrelse med en netværkstur, og en
 * oplæsning med huller i lyder værre end en der bare kommer sent.
 */

export interface SpeechPlayer {
  /** Læg en replik i køen. Tom tekst ignoreres. */
  enqueue: (text: string) => void
  /** Der kommer ikke mere. Når køen er tom, meldes der færdig. */
  finish: () => void
  /** Stop alt NU og smid resten væk — bruges når han bliver afbrudt. */
  stop: () => void
  speaking: boolean
  provider: string
}

export function useSpeechPlayer(
  config: ApiConfig | null | undefined,
  onDone: () => void,
): SpeechPlayer {
  const [speaking, setSpeaking] = useState(false)
  const [provider, setProvider] = useState('')

  const queue = useRef<string[]>([])
  const busy = useRef(false)
  const noMore = useRef(false)
  const player = useRef<AudioPlayer | null>(null)
  // Stiger ved hver stop(). En syntese der var undervejs da han afbrød, må
  // ikke nå at spille bagefter — den tjekker sit eget nummer før den spiller.
  const epoch = useRef(0)
  const doneRef = useRef(onDone)
  useEffect(() => { doneRef.current = onDone }, [onDone])

  const dropPlayer = useCallback(() => {
    try { player.current?.remove() } catch { /* allerede væk */ }
    player.current = null
  }, [])

  /** Spil én fil færdig. Resolver også ved fejl — en enkelt replik der ikke
   *  kan spilles må ikke standse resten af svaret. */
  const playFile = useCallback(async (uri: string) => {
    await new Promise<void>((resolve) => {
      let settled = false
      const finish = () => { if (!settled) { settled = true; resolve() } }
      try {
        const p = createAudioPlayer({ uri })
        player.current = p
        p.addListener('playbackStatusUpdate', (s) => {
          if (s.didJustFinish) { finish() }
        })
        p.play()
      } catch { finish() }
    })
    dropPlayer()
  }, [dropPlayer])

  const speakNative = useCallback(async (text: string) => {
    setProvider('device')
    await new Promise<void>((resolve) => {
      try { Speech.speak(text, { language: 'da-DK', onDone: () => resolve(), onError: () => resolve() }) }
      catch { resolve() }
    })
  }, [])

  const pump = useCallback(async () => {
    if (busy.current) return
    busy.current = true
    const mine = epoch.current
    setSpeaking(true)

    // Syntesen af NÆSTE stykke sættes i gang før det nuværende spilles.
    let ahead: Promise<{ uri: string; provider: string } | null> | null = null
    const synth = (text: string) => {
      if (!config) return Promise.resolve(null)
      return synthesizeTtsToFile(config, clampForSpeech(stripForSpeech(text)))
        .catch(() => null)
    }

    while (queue.current.length && epoch.current === mine) {
      const text = queue.current.shift() as string
      const got = ahead ? await ahead : await synth(text)
      ahead = queue.current.length ? synth(queue.current[0] as string) : null
      if (epoch.current !== mine) break
      if (got) { setProvider(got.provider); await playFile(got.uri) }
      else { await speakNative(clampForSpeech(stripForSpeech(text))) }
    }

    busy.current = false
    if (epoch.current !== mine) return
    setSpeaking(false)
    if (noMore.current && !queue.current.length) doneRef.current()
  }, [config, playFile, speakNative])

  const enqueue = useCallback((text: string) => {
    const t = (text || '').trim()
    if (!t) return
    queue.current.push(t)
    void pump()
  }, [pump])

  const finish = useCallback(() => {
    noMore.current = true
    // Kom svaret uden en eneste replik — fx kun en kodeblok — skal der stadig
    // meldes færdig, ellers venter samtalen for evigt på en lyd der aldrig kom.
    if (!busy.current && !queue.current.length) doneRef.current()
  }, [])

  const stop = useCallback(() => {
    epoch.current += 1
    queue.current = []
    noMore.current = false
    busy.current = false
    try { player.current?.pause() } catch { /* ligegyldigt */ }
    dropPlayer()
    try { Speech.stop() } catch { /* ligegyldigt */ }
    setSpeaking(false)
  }, [dropPlayer])

  useEffect(() => () => { epoch.current += 1; dropPlayer(); try { Speech.stop() } catch { /* unmount */ } }, [dropPlayer])

  // En ny tur nulstilles gennem stop(), som samtalen kalder når den begynder
  // at lytte igen. Derfor er der ingen selvstændig reset her.

  return { enqueue, finish, stop, speaking, provider }
}
