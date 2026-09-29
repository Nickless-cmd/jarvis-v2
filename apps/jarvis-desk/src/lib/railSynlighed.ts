import { useEffect, useState, type RefObject } from 'react'

/**
 * Hvornaar navigations-skinnen maa staa fremme.
 *
 * Skinnen ligger `position: absolute` i transcriptets venstre kant og folder
 * ved hover en tekstblok ud paa op til 230 px. I en smal rude laegger den sig
 * dermed hen over selve samtalen — den flade den skal hjaelpe med at laese.
 *
 * **Kriteriet er transcriptets egen tilgaengelige bredde, ikke vinduets.**
 * Vinduet siger intet om hvor meget plads samtalen faktisk har: aabner man
 * kode-panelet eller aendringer-ruden, krymper transcriptet uden at vinduet
 * roerer sig. En `@media`-regel ville derfor svare rigtigt i et maksimeret
 * vindue og forkert i det oejeblik man aabner et panel.
 *
 * 900 px er DSH's graense (spec punkt 3.5).
 */
export const SKINNE_MIN_BREDDE = 900

/**
 * Hvor meget plads der er til INDHOLD i et element — bredden uden dens egen
 * vandrette padding.
 *
 * `.transcript` har `padding: 32px 24px 8px`, saa `clientWidth` er 48 px mere
 * end det samtalen faktisk raader over. Maalt paa den raa bredde ville
 * graensen ligge 48 px forkert, og det er praecis i det interval hvor skinnen
 * begynder at genere.
 */
export function tilgaengeligBredde(el: HTMLElement | null): number {
  if (!el) return 0
  const s = getComputedStyle(el)
  const px = (v: string) => Number.parseFloat(v) || 0
  return Math.max(0, el.clientWidth - px(s.paddingLeft) - px(s.paddingRight))
}

/**
 * Sand naar der er plads nok til at skinnen ikke daekker samtalen.
 *
 * **0 betyder «ikke maalt», ikke «ingen plads».** Et element der endnu ikke er
 * layoutet — foerste frame, en skjult flade, jsdom — svarer 0 paa clientWidth.
 * Ville vi skjule paa det, forsvandt skinnen i praecis det oejeblik hvor vi
 * intet ved, og kom tilbage et billede senere. Vi skjuler kun paa en RIGTIG
 * maaling der er for smal.
 */
export function erDerPladsTilSkinnen(bredde: number): boolean {
  if (bredde <= 0) return true
  return bredde > SKINNE_MIN_BREDDE
}

/**
 * Foelger transcriptets bredde og siger om skinnen maa vises.
 *
 * Starter paa `true`: skinnen har vaeret synlig indtil nu, og en skinne der
 * blinker vaek og tilbage ved hver montering er vaerre end en der staar et
 * oejeblik for meget. Foerste maaling falder i samme frame som monteringen.
 */
export function useSkinneSynlig(ref: RefObject<HTMLElement | null>): boolean {
  const [synlig, setSynlig] = useState(true)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const maal = () => setSynlig(erDerPladsTilSkinnen(tilgaengeligBredde(el)))
    maal()
    // ResizeObserver og ikke `window.resize`: transcriptet krymper ogsaa naar
    // et panel aabner, og da flytter vinduet sig ikke.
    if (typeof ResizeObserver === 'undefined') return
    const ro = new ResizeObserver(maal)
    ro.observe(el)
    return () => ro.disconnect()
  }, [ref])
  return synlig
}
