import { useEffect, useState } from 'react'

/**
 * Skjul først arbejdslinjen når en syntese faktisk har pacet længe nok til,
 * at et skift kan nå at opleves. Korte synteser når derfor aldrig at blinke
 * linjen væk. Linjen afmonteres ikke; dens ur og lokale fold-state lever videre.
 */
export function usePacingWorkLine(pacing: boolean, runId?: string | null, delayMs = 420): boolean {
  const [hidden, setHidden] = useState(false)

  useEffect(() => {
    setHidden(false)
    if (!pacing) return
    const timer = window.setTimeout(() => setHidden(true), delayMs)
    return () => window.clearTimeout(timer)
  }, [pacing, runId, delayMs])

  return hidden
}
