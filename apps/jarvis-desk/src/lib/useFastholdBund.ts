import { useEffect, type RefObject } from 'react'

/** Hvor ofte ruden pinnes til bund mens der arbejdes. */
export const PIN_INTERVAL_MS = 250

/**
 * Hold transcript'en i bund mens Jarvis arbejder — uanset HVOR indholdet
 * kommer fra.
 *
 * Bjørn 17/9-2026: «auto scroll virker ikk i chatview når han genoptager efter
 * en agent har afsluttet ... det var tæt på jeg ikk havde set det».
 *
 * Auto-scroll hang på React-opdateringer vi selv kendte: `stream.blocks`,
 * `followState.blocks` og ANTALLET af beskeder. Et svar der lander ad en anden
 * vej — serverens gemte besked der erstatter en linje (antallet ændrer sig
 * ikke), eller et autonomt run hentet ind ved refresh — voksede indholdet uden
 * at nogen af de tre ændrede sig. ResizeObserveren så det heller ikke: den
 * kigger på selve scroll-containeren, og DEN ændrer ikke højde når dens
 * indhold vokser.
 *
 * Derfor et lille interval, og KUN mens der arbejdes: så længe `aktiv`, pinnes
 * ruden til bund hver 250 ms. Har brugeren scrollet op (`atBottom` falsk),
 * røres den ikke — den ulæste-tæller tager over.
 */
export function useFastholdBund(
  ref: RefObject<HTMLElement | null>,
  aktiv: boolean,
  atBottom: boolean,
): void {
  useEffect(() => {
    if (!aktiv || !atBottom) return
    const pin = () => {
      const el = ref.current
      if (!el) return
      // Kun hvis den faktisk er rykket. En tildeling der ikke ændrer noget
      // udløser stadig et scroll-event, og det ville nulstille brugerens
      // «jeg har scrollet op» hvert kvarte sekund.
      if (el.scrollTop !== el.scrollHeight - el.clientHeight) {
        el.scrollTop = el.scrollHeight
      }
    }
    pin()
    const id = setInterval(pin, PIN_INTERVAL_MS)
    return () => clearInterval(id)
  }, [ref, aktiv, atBottom])
}
