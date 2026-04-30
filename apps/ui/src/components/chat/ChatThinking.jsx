import { useEffect, useRef, useState } from 'react'

/**
 * Char-by-char scramble effect: when `text` changes, each char briefly
 * flickers through random glyphs before locking. Lightweight — no rAF
 * loop, just a setInterval that snaps in stages and clears itself.
 *
 * Use anywhere a label may abruptly change (tool name, phase). Looks
 * "matrix-y" but only triggers on actual transitions, so it stays calm
 * when nothing changes.
 */
const SCRAMBLE_GLYPHS = '!@#$%&*?+=<>/\\|~-_'.split('')

export function ScrambleText({ text, durationMs = 280, className = '' }) {
  const [chars, setChars] = useState(() => (text || '').split(''))
  const lastTextRef = useRef(text)
  const timerRef = useRef(null)

  useEffect(() => {
    if (text === lastTextRef.current) return
    lastTextRef.current = text
    const target = (text || '').split('')
    const start = performance.now()

    if (timerRef.current) clearInterval(timerRef.current)
    timerRef.current = setInterval(() => {
      const elapsed = performance.now() - start
      const progress = Math.min(1, elapsed / durationMs)
      const lockBoundary = Math.floor(progress * target.length)
      setChars(
        target.map((c, i) => {
          if (i < lockBoundary || c === ' ') return c
          return SCRAMBLE_GLYPHS[Math.floor(Math.random() * SCRAMBLE_GLYPHS.length)]
        })
      )
      if (progress >= 1) {
        clearInterval(timerRef.current)
        timerRef.current = null
        setChars(target)
      }
    }, 32)

    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [text, durationMs])

  const target = (text || '').split('')
  return (
    <span className={`scramble-text ${className}`}>
      {chars.map((c, i) => {
        const locked = c === target[i]
        return (
          <span
            key={i}
            className={`scramble-char ${locked ? 'locked' : 'scrambling'}`}
          >
            {c || '\u00A0'}
          </span>
        )
      })}
    </span>
  )
}

/**
 * Replaces the three bouncing dots in the chat with a slim track + glowing
 * rider that bounces left↔right while a phase label cycles. The phase
 * follows real activity when available (running working step), otherwise
 * rotates through generic "thinking" phases on a timer.
 */
const FALLBACK_PHASES = [
  'tænker',
  'samler kontekst',
  'vurderer',
  'komponerer',
]

export function ThinkingBar({ workingSteps, isStreaming }) {
  const running = (workingSteps || []).filter((s) => s.status === 'running')
  const latest = running[running.length - 1] || null

  // Cycle fallback phases every ~1.6s so the label feels alive even when
  // no tool has fired yet (early LLM thinking phase).
  const [phaseIdx, setPhaseIdx] = useState(0)
  useEffect(() => {
    if (latest) return // real label takes over
    const id = setInterval(() => {
      setPhaseIdx((i) => (i + 1) % FALLBACK_PHASES.length)
    }, 1600)
    return () => clearInterval(id)
  }, [latest])

  const label = latest
    ? (latest.detail || latest.action || 'arbejder')
    : FALLBACK_PHASES[phaseIdx]

  return (
    <div className="thinking-bar" aria-label={`Jarvis ${label}`}>
      <div className="thinking-bar-track">
        <span className="thinking-bar-rider" />
      </div>
      <span className="thinking-bar-label">
        <ScrambleText text={String(label)} />
        {running.length > 1 && (
          <span style={{ opacity: 0.55, marginLeft: 6 }}>
            (+{running.length - 1})
          </span>
        )}
      </span>
    </div>
  )
}
