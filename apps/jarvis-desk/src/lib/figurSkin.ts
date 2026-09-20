import { useEffect, useState } from 'react'

/**
 * Hvilken krop Jarvis-figuren tegnes med (20/9-2026).
 *
 * To skins, og forskellen er ikke pynt:
 *
 * - `ansigt` er den oprindelige (19/9). En lysende kerne med segmenteret ring
 *   og et ansigt der viser HVORDAN det føles — øjnene skifter form, munden
 *   følger med, blikket går mod markøren.
 * - `puls` er mærket fra ikonet: tre bjælker der slår. Samme form som
 *   favicon, app-ikon og systray, så figuren bærer samme mærke som resten af
 *   fladerne.
 *
 * Bjørn valgte 20/9 at beholde BEGGE — derfor et skin og ikke en erstatning.
 * Ansigtet viser en sindsstemning; Puls viser et signal.
 */
export type FigurSkin = 'ansigt' | 'puls'

export const SKIN_VALG: { key: FigurSkin; label: string }[] = [
  { key: 'ansigt', label: 'Ansigtet' },
  { key: 'puls', label: 'Puls' },
]

/**
 * Én sandhed: main-processen (electron/figur.ts, figur.json) — samme sted som
 * til/fra. `null` = kører ikke i desk (en browser-fane), så der tegnes ingen
 * vælger. Samme kontrakt som `useFigurVist`.
 */
interface FigurBro {
  figur?: {
    skin?: () => Promise<FigurSkin>
    saetSkin?: (skin: FigurSkin) => Promise<FigurSkin>
    paaSkin?: (cb: (skin: FigurSkin) => void) => () => void
  }
}
const bro = () => (window as unknown as { jarvisDesk?: FigurBro }).jarvisDesk?.figur

const EVENT = 'jarvis-figur-skin'

export async function saetFigurSkin(skin: FigurSkin): Promise<FigurSkin> {
  const b = bro()
  if (!b?.saetSkin) return skin
  const ny = await b.saetSkin(skin)
  window.dispatchEvent(new CustomEvent(EVENT, { detail: ny }))
  return ny
}

export function useFigurSkin(): [FigurSkin | null, (s: FigurSkin) => void] {
  const [skin, setSkin] = useState<FigurSkin | null>(null)
  useEffect(() => {
    const b = bro()
    if (!b?.skin) return
    let aktiv = true
    void b.skin().then((s) => { if (aktiv) setSkin(s) })
    // Figur-vinduet er en ANDEN renderer. Skiftes der derfra — eller fra
    // tray'en — kommer det som en IPC-besked, ikke som et DOM-event her.
    const afmeld = b.paaSkin?.((s) => { if (aktiv) setSkin(s) })
    const h = (e: Event) => setSkin((e as CustomEvent).detail as FigurSkin)
    // Sidste sikkerhedsnet: hvis beskeden faldt i gulvet, genlæs ved fokus.
    const genlaes = () => { void b.skin?.().then((s) => { if (aktiv) setSkin(s) }) }
    window.addEventListener(EVENT, h)
    window.addEventListener('focus', genlaes)
    return () => {
      aktiv = false
      afmeld?.()
      window.removeEventListener(EVENT, h)
      window.removeEventListener('focus', genlaes)
    }
  }, [])
  return [skin, (s: FigurSkin) => { setSkin(s); void saetFigurSkin(s) }]
}
