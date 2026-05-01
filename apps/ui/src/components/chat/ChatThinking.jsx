import { useEffect, useRef, useState } from 'react'
import {
  Brain,
  Eye,
  FileSearch,
  FolderOpen,
  Globe,
  Pencil,
  ScanSearch,
  Terminal,
} from 'lucide-react'

/**
 * Resolve a working step (or capability activity) to a lucide icon.
 * Shared by ThinkingBar in chat and the workspace scan rail so both
 * use the same vocabulary: run-command → terminal, read → magnifier,
 * edit/write → pencil, browse → globe, generic search → scansearch.
 */
export function resolveStepIcon(step) {
  if (!step) return Brain
  const text = `${step.action || ''} ${step.detail || ''} ${step.step || ''}`.toLowerCase()
  if (/run|exec|bash|shell|command|terminal|invoke/.test(text)) return Terminal
  if (/edit|write|patch|apply|modify/.test(text)) return Pencil
  if (/read|inspect|cat|view|search_memory|search/.test(text)) return FileSearch
  if (/dir|folder|path|workspace|repo|list/.test(text)) return FolderOpen
  if (/web|browse|http|url|fetch|google/.test(text)) return Globe
  if (/scan|trace|monitor|watch/.test(text)) return ScanSearch
  if (/think|reason|consider|plan/.test(text)) return Brain
  if (/look|see|read.*file/.test(text)) return Eye
  return ScanSearch
}

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

export function ThinkingBar({ workingSteps, isStreaming, compact = false }) {
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
  const Icon = latest ? resolveStepIcon(latest) : Brain

  return (
    <div
      className={`thinking-bar ${compact ? 'thinking-bar-compact' : ''}`}
      aria-label={`Jarvis ${label}`}
    >
      <div className="thinking-bar-track">
        <span className="thinking-bar-rider" />
      </div>
      <span
        key={`icon-${latest?.step ?? latest?.action ?? 'idle'}`}
        className="thinking-bar-icon"
      >
        <Icon size={11} />
      </span>
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
