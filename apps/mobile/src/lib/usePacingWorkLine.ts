import { useEffect, useState } from 'react'

/** Bevarer linjen monteret, men skjuler den efter en kort pacing-tærskel. */
export function usePacingWorkLine(pacing: boolean, runId?: string | null, delayMs = 420): boolean {
  const [hidden, setHidden] = useState(false)

  useEffect(() => {
    setHidden(false)
    if (!pacing) return
    const timer = setTimeout(() => setHidden(true), delayMs)
    return () => clearTimeout(timer)
  }, [pacing, runId, delayMs])

  return hidden
}
