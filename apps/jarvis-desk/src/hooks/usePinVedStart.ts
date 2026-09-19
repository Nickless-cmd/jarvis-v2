import { useEffect, useRef, type RefObject } from 'react'

/**
 * Når DIT svar begynder, hopper tråden til bund og bliver der — Claude
 * Desktops pin (§10): `scrollToBottom("instant"); setPinToBottom(true)` ved
 * start, sluppet igen når svaret er færdigt.
 *
 * Kun ved overgangen til «arbejder» — ikke hver gang der kommer indhold. Har
 * man scrollet op MENS svaret kører, respekteres det (useFastholdBund holder
 * kun i bund når man er der).
 */
export function usePinVedStart(ref: RefObject<HTMLElement | null>, arbejder: boolean, onBund: () => void): void {
  const foer = useRef(arbejder)
  useEffect(() => {
    const startede = arbejder && !foer.current
    foer.current = arbejder
    if (!startede) return
    const el = ref.current
    if (el) el.scrollTop = el.scrollHeight
    onBund()
  }, [arbejder]) // eslint-disable-line react-hooks/exhaustive-deps
}
