import { useEffect, useState } from 'react'
import { AccessibilityInfo } from 'react-native'

/**
 * True hvis brugeren har slået "reducér bevægelse" til (tilgængelighed).
 * Animations-komponenter bør da springe loops over og vise en statisk slut-tilstand.
 */
export function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false)
  useEffect(() => {
    let mounted = true
    AccessibilityInfo.isReduceMotionEnabled().then((v) => {
      if (mounted) setReduced(v)
    })
    const sub = AccessibilityInfo.addEventListener('reduceMotionChanged', setReduced)
    return () => {
      mounted = false
      sub.remove()
    }
  }, [])
  return reduced
}
