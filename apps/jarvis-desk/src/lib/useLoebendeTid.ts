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
export function useLoebendeTid(live: boolean): number | undefined {
  const start = useRef<number>(Date.now())
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
