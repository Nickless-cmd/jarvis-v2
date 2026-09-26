import { useCallback, useEffect, useRef, useState } from 'react'
import {
  anvendBredde, gemBredde, klem, laesBredde, MAKS_BREDDE, MIN_BREDDE,
  STANDARD_BREDDE,
} from '../../lib/skinneBredde'

/**
 * Trækgrebet på skinnens VENSTRE kant.
 *
 * Bjørn 26/9-2026: «i højre side af desk de 3 paneler… jeg mangler træk/slip
 * altså at kunne udvide dem til siden.. lige som man kan med venstre panel.»
 *
 * Forskellen fra `SidebarGreb` er retningen. Sidepanelet står i vinduets
 * venstre kant og vokser mod højre, så dér ER musens x bredden. Skinnen står
 * i den HØJRE kant og vokser mod venstre — bredden er derfor afstanden fra
 * musen til skinnens egen højre kant. Derfor måles der mod elementets rect og
 * ikke mod vinduet: skinnen har 12 px luft til kanten (`.code-right-stack`
 * har `right: 12px`), og et vindues-mål ville ramme 12 px forkert hele vejen.
 *
 * De tre ting fra `SidebarGreb` gælder uændret, og af samme grunde:
 *
 *  1. TASTATUR. Grebet er en `separator` med piletaster (og Home/End). Et
 *     greb der kun kan bruges med mus lukker panelet for den der ikke bruger
 *     mus — og det er en bredde, ikke en finurlighed.
 *
 *  2. LYTTERNE SIDDER PÅ WINDOW, ikke på grebet. Trækker man hurtigt, løber
 *     musen foran elementet, og en lytter på grebet ville miste den midt i
 *     trækket. `setPointerCapture` alene rækker ikke når vinduet mister fokus.
 *
 *  3. DER GEMMES FØRST VED SLIP. Et `localStorage`-skriv pr. musebevægelse er
 *     hundredvis af skrivninger for ét træk.
 *
 * Den højre kant måles ved pointerdown og ikke undervejs: skinnen er forankret
 * i højre, så kanten står stille hele trækket igennem. At måle hver gang ville
 * læse layout i hver musebevægelse — en reflow pr. pixel for et tal der ikke
 * ændrer sig.
 */
export function SkinneGreb() {
  const [traekker, setTraekker] = useState(false)
  const bredde = useRef(laesBredde())
  const hoejreKant = useRef(0)

  // Den gemte bredde skal sidde FØR første maling, ellers ser man skinnen
  // hoppe fra standarden til sin egen bredde.
  useEffect(() => { anvendBredde(bredde.current) }, [])

  const flyt = useCallback((x: number) => {
    bredde.current = klem(hoejreKant.current - x)
    anvendBredde(bredde.current)
  }, [])

  useEffect(() => {
    if (!traekker) return
    const paaFlyt = (e: PointerEvent) => { e.preventDefault(); flyt(e.clientX) }
    const slip = () => { setTraekker(false); gemBredde(bredde.current) }
    window.addEventListener('pointermove', paaFlyt)
    window.addEventListener('pointerup', slip)
    // Mister vinduet musen (ud af appen, alt-tab), skal trækket slutte —
    // ellers sidder skinnen fast i musen når man kommer tilbage.
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
    // Modsat sidepanelet: her vokser panelet mod VENSTRE, så pil-venstre gør
    // det BREDERE. At vende det ville være at vende brugerens forventning til
    // hvad pilen peger på — og det er den eneste vej til grebet uden mus.
    if (e.key === 'ArrowLeft') ny += skridt
    else if (e.key === 'ArrowRight') ny -= skridt
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
      className={`skinne-greb${traekker ? ' er-aktiv' : ''}`}
      role="separator"
      aria-orientation="vertical"
      aria-label="Træk for at ændre skinnens bredde"
      aria-valuemin={MIN_BREDDE}
      aria-valuemax={MAKS_BREDDE}
      aria-valuenow={bredde.current}
      tabIndex={0}
      onPointerDown={(e) => {
        e.preventDefault()
        const skinn = (e.currentTarget as HTMLElement).parentElement
        hoejreKant.current = skinn
          ? skinn.getBoundingClientRect().right
          : window.innerWidth - 12
        setTraekker(true)
      }}
      onKeyDown={tast}
      onDoubleClick={() => {
        // Dobbeltklik nulstiller. Har man trukket den helt smal og ikke kan
        // ramme grebet igen, er det vejen tilbage.
        bredde.current = klem(STANDARD_BREDDE)
        anvendBredde(bredde.current)
        gemBredde(bredde.current)
      }}
    />
  )
}
