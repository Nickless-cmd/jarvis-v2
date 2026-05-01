import { useEffect, useState, useCallback } from 'react'

/**
 * Pinned tool-results — small client-side store so the user can keep a
 * specific result_id sticky in the UI even as the chat scrolls. Pinned
 * cards render in a top strip above the message list and stay one
 * click away.
 *
 * Phase 1 is purely visual: pinning doesn't currently inject the
 * result back into Jarvis's prompt context (that needs a backend
 * extension to prompt_contract — likely Phase 2 of this feature). For
 * now: humans can pin to keep a thing in their own short-term memory.
 *
 * Persisted to localStorage so a reload doesn't blow away pins.
 */
const STORAGE_KEY = 'jarvisx.pinned_tool_results'
const MAX_PINS = 6

export interface PinnedResult {
  resultId: string
  summary: string
  pinnedAt: number
}

function loadPins(): PinnedResult[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return parsed
      .filter((p) => p && typeof p.resultId === 'string')
      .slice(0, MAX_PINS)
  } catch {
    return []
  }
}

function savePins(pins: PinnedResult[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(pins))
  } catch {
    // ignore quota / disabled storage
  }
}

export function usePinnedResults(): {
  pins: PinnedResult[]
  isPinned: (id: string) => boolean
  pin: (id: string, summary?: string) => void
  unpin: (id: string) => void
  clearAll: () => void
} {
  const [pins, setPins] = useState<PinnedResult[]>(() => loadPins())

  // Cross-tab/window sync — if another window pins, this one updates
  useEffect(() => {
    const onStorage = (e: StorageEvent) => {
      if (e.key === STORAGE_KEY) setPins(loadPins())
    }
    window.addEventListener('storage', onStorage)
    return () => window.removeEventListener('storage', onStorage)
  }, [])

  const persist = useCallback((next: PinnedResult[]) => {
    setPins(next)
    savePins(next)
  }, [])

  const isPinned = useCallback(
    (id: string) => pins.some((p) => p.resultId === id),
    [pins],
  )

  const pin = useCallback(
    (id: string, summary: string = '') => {
      setPins((prev) => {
        if (prev.some((p) => p.resultId === id)) return prev
        const next = [
          { resultId: id, summary, pinnedAt: Date.now() },
          ...prev,
        ].slice(0, MAX_PINS)
        savePins(next)
        return next
      })
    },
    [],
  )

  const unpin = useCallback(
    (id: string) => {
      setPins((prev) => {
        const next = prev.filter((p) => p.resultId !== id)
        savePins(next)
        return next
      })
    },
    [],
  )

  const clearAll = useCallback(() => persist([]), [persist])

  return { pins, isPinned, pin, unpin, clearAll }
}
