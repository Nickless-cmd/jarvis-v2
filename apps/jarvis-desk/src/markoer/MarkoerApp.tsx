/**
 * Markør-laget — renderer'en. Se electron/markoer.ts for hvornår og hvorfor.
 *
 * Fladen har to opgaver, og de er uafhængige:
 *
 * 1. **Markøren** — et kortlivet spor + en ring, der viser HVOR Jarvis peger.
 *    Det tegnes kun mens der faktisk peges, og ryddes op igen.
 * 2. **Halo'en** — en glød langs kanten af hver skærm, der viser AT han har
 *    overtaget skrivebordet. Den tændes af broens handlende kald og bliver
 *    stående et stykke tid efter det sidste (se `OVERTAG_MS`).
 *
 * Vinduet er ALTID åbent og dækker hele skrivebordet, så komponenten må ikke
 * koste noget når der ikke peges: ingen evig animations-loop, ingen timere der
 * tikker på en tom skærm. Sporet ryddes kun mens det findes, og halo'en har
 * præcis én timer — den der slukker den.
 */
import { useEffect, useRef, useState } from 'react'
import {
  FADE_MS,
  OVERTAG_MS,
  aktivSkærm,
  fjernAeldre,
  sporStoerrelse,
  tilfoejPeg,
  type Peg,
  type Rektangel,
} from './markoerLogik'
import './markoer.css'

interface MarkoerBro {
  markoer?: {
    paaPeg: (cb: (p: { x: number; y: number }) => void) => () => void
    paaOvertag?: (cb: (p: { x: number; y: number } | null) => void) => () => void
    skærme?: () => Promise<Rektangel[]>
    paaSkærme?: (cb: (s: Rektangel[]) => void) => () => void
  }
}

const bro = () => (window as unknown as { jarvisDesk?: MarkoerBro }).jarvisDesk

/** Så tit rydder vi op i sporet. Kun mens der ER et spor. */
export const RYD_MS = 150

export function MarkoerApp() {
  const [spor, setSpor] = useState<Peg[]>([])
  const [overtag, setOvertag] = useState(false)
  // Hvor Jarvis stod da han overtog. `null` = ukendt, og så lyser alle skærme.
  const [overtagPos, setOvertagPos] = useState<{ x: number; y: number } | null>(null)
  const [skaerme, setSkaerme] = useState<Rektangel[]>([])
  const naesteId = useRef(1)
  const liste = useRef<Peg[]>([])
  const slukTimer = useRef<number | null>(null)
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

  // Skærm-layoutet: hent det ved mount, og følg med hvis opsætningen ændrer
  // sig (skærm til/fra, ny opløsning). Halo'en lægger én kant pr. rektangel.
  useEffect(() => {
    const b = bro()
    if (!b?.markoer) return
    void b.markoer.skærme?.().then((s) => {
      if (s?.length) setSkaerme(s)
    }).catch(() => {
      // Uden layout tegner halo'en én kant over hele laget i stedet (se nedenfor).
    })
    return b.markoer.paaSkærme?.((s) => {
      if (s?.length) setSkaerme(s)
    })
  }, [])

  // Halo'en: tænd ved første handlende kald, og sluk et stykke tid efter det
  // sidste. Timeren nulstilles ved hvert nyt kald, så en sekvens af klik og
  // tastetryk står som ÉN synlig overtagelse i stedet for at blinke.
  useEffect(() => {
    const b = bro()
    if (!b?.markoer?.paaOvertag) return
    const af = b.markoer.paaOvertag((p) => {
      setOvertagPos(p)
      setOvertag(true)
      if (slukTimer.current !== null) window.clearTimeout(slukTimer.current)
      slukTimer.current = window.setTimeout(() => {
        setOvertag(false)
        slukTimer.current = null
      }, OVERTAG_MS)
    })
    return () => {
      af()
      if (slukTimer.current !== null) window.clearTimeout(slukTimer.current)
    }
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

  // Hvilken skærm halo'en skal lyse på. -1 betyder «ved det ikke» — enten
  // fordi positionen ikke kunne læses, eller fordi han står uden for alle
  // skærme. Begge tegner kanten rundt om alle, som er et ærligt svar frem for
  // at gætte på én.
  const aktiv = overtagPos ? aktivSkærm(skaerme, overtagPos.x, overtagPos.y) : -1

  return (
    <div className="markoer-lag" aria-hidden="true">
      {/* Halo'en ligger UNDER sporet og markøren, så ringen altid er skarpest.
          Den lyser på den skærm Jarvis står på — ikke på alle tre, som den
          gjorde før 21/9. Alle kanterne bliver i DOM'en og slukkes med en
          klasse i stedet for at blive fjernet: så bliver et skift mellem
          skærme en overgang i stedet for et blink. Har vi ikke fået
          skærm-layoutet endnu, tegnes én kant over hele laget — hellere en
          grov indikation end ingen. */}
      {overtag &&
        (skaerme.length === 0 ? (
          <span className="markoer-kant markoer-kant--alt" />
        ) : (
          skaerme.map((s, i) => (
            <span
              key={`kant-${s.x}-${s.y}-${s.width}`}
              className={`markoer-kant${aktiv === i || aktiv < 0 ? '' : ' markoer-kant--slukket'}`}
              style={{
                left: `${s.x}px`,
                top: `${s.y}px`,
                width: `${s.width}px`,
                height: `${s.height}px`,
              }}
            />
          ))
        ))}

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
