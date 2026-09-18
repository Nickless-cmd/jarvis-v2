import { useEffect, useRef, useState } from 'react'

/**
 * Sekunder siden linjen blev live — tæller mens `live`, fryser når den slutter.
 *
 * Streamen bærer ingen varighed for tanker eller værktøjskald, så linjen må
 * selv holde uret. To regler:
 *  - Hele sekunder mens den løber; «1,2 s … 1,3 s» ville flimre hvert tick.
 *  - Kun en linje der HAR været live har en tid. En gemt blok der monteres som
 *    færdig ville ellers få «0 s».
 */
/**
 * Klokken på en linje der KØRER vises først efter så mange sekunder.
 *
 * Claude Desktop gør det samme (målt til 5 i deres CSS). Et kald på to
 * sekunder skal ikke nå at vise «0 s» og skifte til «1 s» — tallet er
 * information, ikke støj. En linje der er FÆRDIG viser sit målte tal med det
 * samme; der er ingen flimren at undgå.
 *
 * Gælder bevidst IKKE tanke- og skill-linjen: der bad Bjørn 17/9-2026 om at
 * tallet står der med det samme (se ThinkingLine).
 */
export const KLOKKE_EFTER_S = 5

export function useLoebendeTid(live: boolean, startet?: number): number | undefined {
  // `startet` fra blokken vinder: komponenten kan monteres om midt i en tanke
  // (runderne grupperes om), og så ville et ur født ved montering starte forfra.
  const start = useRef<number>(startet ?? Date.now())
  if (startet != null && start.current !== startet) start.current = startet
  const varLive = useRef(live)
  const [nu, setNu] = useState(() => Date.now())
  const [frosset, setFrosset] = useState<number | undefined>(undefined)
  useEffect(() => {
    if (!live) {
      if (varLive.current) setFrosset((f) => f ?? (Date.now() - start.current) / 1000)
      return
    }
    varLive.current = true
    const t = setInterval(() => setNu(Date.now()), 1000)
    return () => clearInterval(t)
  }, [live])
  return live ? (nu - start.current) / 1000 : frosset
}
