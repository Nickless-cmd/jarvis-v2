import { useEffect } from 'react'

/** Globale tastaturgenveje (analyse §14.2). Prop-drevet → testbar uden kontekst.
 *  - Esc: stop igangværende generering (kun når der arbejdes)
 *  - Ctrl/Cmd+,: åbn Indstillinger
 *  Ignorerer ikke input-felter for Esc/genvej — stop skal virke overalt. */
export function GlobalShortcuts({
  working,
  onStop,
  onSettings,
}: {
  working: boolean
  onStop: () => void
  onSettings: () => void
}) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && working) {
        onStop()
        return
      }
      if ((e.ctrlKey || e.metaKey) && e.key === ',') {
        e.preventDefault()
        onSettings()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [working, onStop, onSettings])

  return null
}
