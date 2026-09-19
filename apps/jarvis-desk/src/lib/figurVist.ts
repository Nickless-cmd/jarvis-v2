import { useEffect, useState } from 'react'

/**
 * Er Jarvis-figuren på skrivebordet? Én sandhed: main-processen
 * (electron/figur.ts, figur.json). Indstillingen i Udseende, knappen i
 * headeren og tray-menuens flueben spørger og sætter alle det samme sted.
 *
 * `null` = kører ikke i desk (en browser-fane) — så tegnes kontakterne ikke.
 */
interface FigurBro { figur?: { vist: () => Promise<boolean>; saetVist: (v: boolean) => Promise<boolean> } }
const bro = () => (window as unknown as { jarvisDesk?: FigurBro }).jarvisDesk?.figur

const EVENT = 'jarvis-figur-vist'

export async function saetFigurVist(vist: boolean): Promise<boolean> {
  const b = bro()
  if (!b) return false
  const ny = await b.saetVist(vist)
  window.dispatchEvent(new CustomEvent(EVENT, { detail: ny }))
  return ny
}

export function useFigurVist(): [boolean | null, (v: boolean) => void] {
  const [vist, setVist] = useState<boolean | null>(null)
  useEffect(() => {
    const b = bro()
    if (!b) return
    let aktiv = true
    void b.vist().then((v) => { if (aktiv) setVist(v) })
    // Tray-menuen kan ændre den uden om os — spørg igen når vinduet får fokus.
    const genlaes = () => { void b.vist().then((v) => { if (aktiv) setVist(v) }) }
    const h = (e: Event) => setVist(Boolean((e as CustomEvent).detail))
    window.addEventListener(EVENT, h)
    window.addEventListener('focus', genlaes)
    return () => { aktiv = false; window.removeEventListener(EVENT, h); window.removeEventListener('focus', genlaes) }
  }, [])
  return [vist, (v: boolean) => { setVist(v); void saetFigurVist(v) }]
}
