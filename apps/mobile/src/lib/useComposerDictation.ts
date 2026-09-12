import { useCallback, useEffect, useRef, useState } from 'react'
import { Animated } from 'react-native'
import {
  RecordingPresets,
  requestRecordingPermissionsAsync,
  setAudioModeAsync,
  useAudioRecorder,
} from 'expo-audio'
import type { ApiConfig } from './types'
import { transcribeAudio } from './voiceApi'
import { levelFromDb } from './voiceActivity'

export type DictationState = 'idle' | 'recording' | 'transcribing' | 'error'

export function useComposerDictation(config: ApiConfig | null | undefined) {
  const [state, setState] = useState<DictationState>('idle')
  const [elapsedMs, setElapsedMs] = useState(0)
  const [text, setText] = useState('')
  const [error, setError] = useState('')
  const level = useRef(new Animated.Value(0)).current
  const recording = useRef(false)
  const startedAt = useRef(0)
  // Generation: bumpes ved annullering. En transskription der er i luften når
  // brugeren annullerer, må IKKE skrive sit resultat ind bagefter — den ville
  // ellers genoplive et svar brugeren netop afviste. (Samme klasse som et sent
  // STT-svar efter stop; her er cancel det der trækker tæppet væk.)
  const generation = useRef(0)
  const poll = useRef<ReturnType<typeof setInterval> | null>(null)
  const recorder = useAudioRecorder({
    ...RecordingPresets.HIGH_QUALITY,
    isMeteringEnabled: true,
    android: { ...RecordingPresets.HIGH_QUALITY.android, audioSource: 'voice_recognition' },
  })

  const stopPoll = useCallback(() => {
    if (poll.current) clearInterval(poll.current)
    poll.current = null
    level.setValue(0)
  }, [level])

  const start = useCallback(async () => {
    if (!config || recording.current || state === 'transcribing') return
    setText('')
    setError('')
    const permission = await requestRecordingPermissionsAsync()
    if (!permission.granted) {
      setError('Mikrofonadgang er slået fra.')
      setState('error')
      return
    }
    try {
      await setAudioModeAsync({ allowsRecording: true, playsInSilentMode: true })
      await recorder.prepareToRecordAsync()
      recorder.record()
      recording.current = true
      startedAt.current = Date.now()
      setElapsedMs(0)
      setState('recording')
      poll.current = setInterval(() => {
        setElapsedMs(Date.now() - startedAt.current)
        const db = (recorder as { getStatus?: () => { metering?: number } })
          .getStatus?.().metering ?? -160
        level.setValue(levelFromDb(db))
      }, 120)
    } catch (cause) {
      recording.current = false
      stopPoll()
      setError(`Kunne ikke starte diktering (${(cause as Error)?.message || 'ukendt fejl'}).`)
      setState('error')
    }
  }, [config, level, recorder, state, stopPoll])

  const stop = useCallback(async () => {
    if (!recording.current || !config) return
    recording.current = false
    stopPoll()
    setState('transcribing')
    const minGeneration = generation.current
    try {
      await recorder.stop()
      const uri = recorder.uri
      if (!uri) throw new Error('mangler lydfil')
      const result = await transcribeAudio(config, uri)
      // Annulleret (eller ny optagelse) mens vi ventede: resultatet er forældet.
      if (generation.current !== minGeneration) return
      if (result.status !== 'ok') throw new Error(result.error || 'transskription fejlede')
      setText(String(result.text || '').trim())
      setState('idle')
    } catch (cause) {
      if (generation.current !== minGeneration) return
      setError(`Kunne ikke transskribere (${(cause as Error)?.message || 'ukendt fejl'}).`)
      setState('error')
    }
  }, [config, recorder, stopPoll])

  const cancel = useCallback(async () => {
    generation.current += 1
    const wasRecording = recording.current
    recording.current = false
    stopPoll()
    if (wasRecording) {
      try { await recorder.stop() } catch { /* optageren kan allerede være stoppet */ }
    }
    setText('')
    setError('')
    setElapsedMs(0)
    setState('idle')
  }, [recorder, stopPoll])

  const clearResult = useCallback(() => {
    setText('')
    setError('')
    setState((current) => current === 'error' ? 'idle' : current)
  }, [])

  useEffect(() => () => {
    stopPoll()
    if (recording.current) {
      recording.current = false
      try { void recorder.stop() } catch { /* native optager er allerede lukket */ }
    }
  }, [recorder, stopPoll])

  return {
    state, level, elapsedMs, text, error,
    start, stop, cancel,
    clearResult,
  }
}
