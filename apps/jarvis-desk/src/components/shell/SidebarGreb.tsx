import { useCallback, useEffect, useRef, useState } from 'react'
import {
  anvendBredde, gemBredde, klem, laesBredde, MAKS_BREDDE, MIN_BREDDE,
} from '../../lib/sidebarBredde'

/**
 * Trækgrebet på sidepanelets højre kant.
 *
 * Bjørn 16/9-2026: «venstre panel mangler træk og slip til breden».
 *
 * Tre ting der ikke er til pynt:
 *
 *  1. TASTATUR. Grebet er en `separator` med piletaster (og Home/End).
 *     Et greb der kun kan bruges med mus lukker panelet for den der ikke
 *     bruger mus — og det er en bredde, ikke en finurlighed.
 *
 *  2. LYTTERNE SIDDER PÅ WINDOW, ikke på grebet. Trækker man hurtigt, løber
 *     musen foran elementet, og en lytter på grebet ville miste den midt i
 *     trækket. `setPointerCapture` alene rækker ikke når vinduet mister fokus.
 *
 *  3. DER GEMMES FØRST VED SLIP. Et `localStorage`-skriv pr. musebevægelse er
 *     hundredvis af skrivninger for ét træk.
 */
export function SidebarGreb() {
  const [traekker, setTraekker] = useState(false)
  const bredde = useRef(laesBredde())

  // Den gemte bredde skal sidde FØR første maling, ellers ser man panelet
  // hoppe fra standarden til sin egen bredde.
  useEffect(() => { anvendBredde(bredde.current) }, [])

  const flyt = useCallback((x: number) => {
    // Sidepanelet starter i vinduets venstre kant, så musens x ER bredden.
    bredde.current = klem(x)
    anvendBredde(bredde.current)
  }, [])

  useEffect(() => {
    if (!traekker) return
    const paaFlyt = (e: PointerEvent) => { e.preventDefault(); flyt(e.clientX) }
    const slip = () => { setTraekker(false); gemBredde(bredde.current) }
    window.addEventListener('pointermove', paaFlyt)
    window.addEventListener('pointerup', slip)
    // Mister vinduet musen (ud af appen, alt-tab), skal trækket slutte —
    // ellers sidder panelet fast i musen når man kommer tilbage.
    window.addEventListener('pointercancel', slip)
    window.addEventListener('blur', slip)
    return () => {
      window.removeEventListener('pointermove', paaFlyt)
      window.removeEventListener('pointerup', slip)
      window.removeEventListener('pointercancel', slip)
      window.removeEventListener('blur', slip)
    }
  }, [traekker, flyt])

  const tast = (e: React.KeyboardEvent) => {
    const skridt = e.shiftKey ? 32 : 8
    let ny = bredde.current
    if (e.key === 'ArrowLeft') ny -= skridt
    else if (e.key === 'ArrowRight') ny += skridt
    else if (e.key === 'Home') ny = MIN_BREDDE
    else if (e.key === 'End') ny = MAKS_BREDDE
    else return
    e.preventDefault()
    bredde.current = klem(ny)
    anvendBredde(bredde.current)
    gemBredde(bredde.current)
  }

  return (
    <div
      className={`sidebar-greb${traekker ? ' er-aktiv' : ''}`}
      role="separator"
      aria-orientation="vertical"
      aria-label="Træk for at ændre panelets bredde"
      aria-valuemin={MIN_BREDDE}
      aria-valuemax={MAKS_BREDDE}
      aria-valuenow={bredde.current}
      tabIndex={0}
      onPointerDown={(e) => { e.preventDefault(); setTraekker(true) }}
      onKeyDown={tast}
      onDoubleClick={() => {
        // Dobbeltklik nulstiller. Har man trukket den helt smal og ikke kan
        // ramme grebet igen, er det vejen tilbage.
        bredde.current = klem(290)
        anvendBredde(bredde.current)
        gemBredde(bredde.current)
      }}
    />
  )
}
