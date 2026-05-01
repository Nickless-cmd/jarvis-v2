import { useEffect, useRef, useState } from 'react'
import { Mic, MicOff } from 'lucide-react'

/**
 * Push-to-talk voice button. Uses the browser's SpeechRecognition API
 * (available in Chromium and therefore Electron) for STT — no backend
 * roundtrip needed. Result text is dispatched as a CustomEvent that
 * the composer (or anything listening) can append to its draft.
 *
 * Hold the button to record. Release to stop and insert the
 * transcript. Esc cancels mid-recording.
 *
 * Privacy note: SpeechRecognition in Chromium routes audio to Google's
 * servers. For local-only voice we'd swap to a backend Whisper endpoint
 * — that's a v2 upgrade.
 */

declare global {
  interface Window {
    webkitSpeechRecognition?: new () => SpeechRecognition
    SpeechRecognition?: new () => SpeechRecognition
  }
  interface SpeechRecognition extends EventTarget {
    lang: string
    continuous: boolean
    interimResults: boolean
    start: () => void
    stop: () => void
    onresult: ((this: SpeechRecognition, ev: SpeechRecognitionEvent) => void) | null
    onerror: ((this: SpeechRecognition, ev: Event) => void) | null
    onend: ((this: SpeechRecognition) => void) | null
  }
  interface SpeechRecognitionEvent extends Event {
    results: SpeechRecognitionResultList
  }
}

function getRecognition(): SpeechRecognition | null {
  const Ctor = window.SpeechRecognition || window.webkitSpeechRecognition
  if (!Ctor) return null
  const rec = new Ctor()
  rec.lang = 'da-DK'  // default Danish since that's primary
  rec.continuous = true
  rec.interimResults = true
  return rec
}

export function VoiceButton() {
  const [recording, setRecording] = useState(false)
  const [interim, setInterim] = useState('')
  const [unsupported, setUnsupported] = useState(false)
  const recRef = useRef<SpeechRecognition | null>(null)
  const finalRef = useRef('')

  useEffect(() => {
    if (!getRecognition()) setUnsupported(true)
  }, [])

  const start = () => {
    if (recording || unsupported) return
    const rec = getRecognition()
    if (!rec) return
    finalRef.current = ''
    setInterim('')
    rec.onresult = (e: SpeechRecognitionEvent) => {
      let final = ''
      let live = ''
      // Iterate via index — can't use spread on a SpeechRecognitionResultList
      for (let i = 0; i < e.results.length; i++) {
        const r = e.results[i] as unknown as { 0: { transcript: string }; isFinal: boolean }
        const text = r[0].transcript
        if (r.isFinal) final += text
        else live += text
      }
      if (final) finalRef.current += final
      setInterim(live)
    }
    rec.onerror = () => {
      setRecording(false)
    }
    rec.onend = () => {
      setRecording(false)
    }
    try {
      rec.start()
      recRef.current = rec
      setRecording(true)
    } catch { /* already running */ }
  }

  const stop = (commit = true) => {
    const rec = recRef.current
    if (rec) {
      try {
        rec.stop()
      } catch { /* ignore */ }
      recRef.current = null
    }
    setRecording(false)
    if (commit) {
      const text = (finalRef.current + ' ' + interim).trim()
      if (text) {
        window.dispatchEvent(
          new CustomEvent('jarvisx:voice-transcript', { detail: { text } }),
        )
      }
    }
    finalRef.current = ''
    setInterim('')
  }

  // Esc cancels without committing
  useEffect(() => {
    if (!recording) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        stop(false)
      }
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [recording])

  if (unsupported) return null

  return (
    <button
      onPointerDown={(e) => {
        e.preventDefault()
        start()
      }}
      onPointerUp={() => stop(true)}
      onPointerLeave={() => recording && stop(true)}
      onContextMenu={(e) => e.preventDefault()}
      title={recording ? 'Slip for at sende — Esc for at fortryde' : 'Hold for at tale'}
      className={[
        'flex h-6 w-6 items-center justify-center rounded transition-all select-none',
        recording
          ? 'animate-pulse bg-danger/20 text-danger ring-2 ring-danger/40'
          : 'text-fg3 hover:bg-bg2 hover:text-accent',
      ].join(' ')}
    >
      {recording ? <Mic size={12} /> : <MicOff size={12} />}
    </button>
  )
}
