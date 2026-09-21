/**
 * Markør-laget — renderer'en. Se electron/markoer.ts for hvornår og hvorfor.
 *
 * Vinduet er ALTID åbent og dækker hele skrivebordet, så denne komponent må
 * ikke koste noget når der ikke peges: ingen evig animations-loop, ingen
 * timere der tikker på en tom skærm. Der tegnes kun mens der er et spor, og
 * oprydningen stopper i det øjeblik sporet er væk.
 */
import { useEffect, useRef, useState } from 'react'
import { FADE_MS, fjernAeldre, sporStoerrelse, tilfoejPeg, type Peg } from './markoerLogik'
import './markoer.css'

interface MarkoerBro {
  markoer?: {
    paaPeg: (cb: (p: { x: number; y: number }) => void) => () => void
  }
}

const bro = () => (window as unknown as { jarvisDesk?: MarkoerBro }).jarvisDesk

/** Så tit rydder vi op i sporet. Kun mens der ER et spor. */
export const RYD_MS = 150

export function MarkoerApp() {
  const [spor, setSpor] = useState<Peg[]>([])
  const naesteId = useRef(1)
  const liste = useRef<Peg[]>([])
  const harSpor = spor.length > 0

  useEffect(() => {
    const b = bro()
    if (!b?.markoer) return
    return b.markoer.paaPeg(({ x, y }) => {
      const ny = tilfoejPeg(liste.current, {
        id: naesteId.current++,
        x,
        y,
        t: performance.now(),
      })
      // Uændret liste = mikro-bevægelse vi bevidst springer over.
      if (ny === liste.current) return
      liste.current = ny
      setSpor(ny)
    })
  }, [])

  useEffect(() => {
    if (!harSpor) return
    const t = window.setInterval(() => {
      const tilbage = fjernAeldre(liste.current, performance.now())
      if (tilbage.length !== liste.current.length) {
        liste.current = tilbage
        setSpor(tilbage)
      }
    }, RYD_MS)
    return () => window.clearInterval(t)
  }, [harSpor])

  const sidste = spor[spor.length - 1]

  return (
    <div className="markoer-lag" aria-hidden="true">
      {/* Sporet: hver position bliver en prik der falmer, så man kan se ruten
          og ikke bare hvor han står nu. */}
      {spor.map((p, i) => (
        <span
          key={p.id}
          className="markoer-prik"
          style={{
            left: `${p.x}px`,
            top: `${p.y}px`,
            width: `${sporStoerrelse(i, spor.length)}px`,
            height: `${sporStoerrelse(i, spor.length)}px`,
            animationDuration: `${FADE_MS}ms`,
          }}
        />
      ))}
      {/* Ringen sidder på den nyeste position. Nyt id hver gang → ny node →
          CSS-animationen kører forfra, uden at vi rører JS-timere. */}
      {sidste && (
        <span key={`ring-${sidste.id}`} className="markoer-ring" style={{ left: `${sidste.x}px`, top: `${sidste.y}px`, animationDuration: `${FADE_MS}ms` }}>
          <span className="markoer-kerne" />
        </span>
      )}
    </div>
  )
}
