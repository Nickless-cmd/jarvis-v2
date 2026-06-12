import { useCallback, useEffect, useRef, useState } from 'react'
import type { ApiConfig } from '../lib/api'
import { transcribeAudio } from '../lib/api'

/** Dikterings-hook via MediaRecorder + backend /transcribe (lokal faster-
 *  whisper). webkitSpeechRecognition virker IKKE i Electron (mangler Googles
 *  cloud-nøgle), så vi optager lyd lokalt og transskriberer server-side.
 *
 *  Tilstande: idle → recording → transcribing → idle. Transkriberet tekst
 *  leveres via onResult (append til composer). supported=false hvis browseren
 *  ikke har getUserMedia/MediaRecorder, eller hvis config mangler. */
export function useDictation(
  onResult: (text: string) => void,
  config?: ApiConfig,
) {
  const [listening, setListening] = useState(false)
  const [transcribing, setTranscribing] = useState(false)
  const recRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const streamRef = useRef<MediaStream | null>(null)

  const supported =
    !!config &&
    typeof navigator !== 'undefined' &&
    !!navigator.mediaDevices?.getUserMedia &&
    typeof MediaRecorder !== 'undefined'

  const cleanupStream = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null
  }, [])

  const stop = useCallback(() => {
    // Stopper optagelsen; onstop-handleren transskriberer.
    if (recRef.current && recRef.current.state !== 'inactive') {
      recRef.current.stop()
    }
    setListening(false)
  }, [])

  const start = useCallback(async () => {
    if (!supported || !config) return
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream
      chunksRef.current = []
      const rec = new MediaRecorder(stream)
      rec.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) chunksRef.current.push(e.data)
      }
      rec.onstop = async () => {
        cleanupStream()
        const blob = new Blob(chunksRef.current, { type: rec.mimeType || 'audio/webm' })
        chunksRef.current = []
        if (blob.size === 0) return
        setTranscribing(true)
        try {
          const r = await transcribeAudio(config, blob)
          if (r.status === 'ok' && r.text.trim()) onResult(r.text.trim())
        } catch {
          // best-effort: fejl svælges (knappen vender bare tilbage til idle)
        } finally {
          setTranscribing(false)
        }
      }
      recRef.current = rec
      rec.start()
      setListening(true)
    } catch {
      // mic-adgang nægtet eller ingen enhed → forbliv idle
      cleanupStream()
      setListening(false)
    }
  }, [supported, config, onResult, cleanupStream])

  useEffect(
    () => () => {
      if (recRef.current && recRef.current.state !== 'inactive') recRef.current.stop()
      cleanupStream()
    },
    [cleanupStream],
  )

  return { supported, listening, transcribing, start, stop }
}
