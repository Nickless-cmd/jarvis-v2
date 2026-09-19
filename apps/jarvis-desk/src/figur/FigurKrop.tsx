import { udtryk, type Handling, type Udtryk } from './figurLogik'

/**
 * Jarvis' krop: en lysende kerne med en segmenteret ring — J.A.R.V.I.S.,
 * ikke et dyr. Codex' ni kæledyr er OpenAI's egne tegninger; dem låner vi
 * ikke. Reglerne for bevægelse er derimod deres (se figurLogik).
 *
 * Farven er tilstanden, samme som linjen i sidepanelet og prikken på
 * telefonen: accent hviler/arbejder, gul venter, rød fejlede, grøn færdig.
 *
 * Ansigtet (19/9-2026) giver tilstanden et udtryk og ikke kun en farve:
 * øjnene skifter form, munden følger med, og begge kigger mod markøren når
 * den er i nærheden. Gløden ånder i takt med hvad han laver.
 */

/**
 * Øjet er tegnet omkring origo, så begge øjne deler ÉN form og kun forskydes —
 * og så blikket kan flytte dem uden at regne to former ud.
 *
 * `rot` vippes spejlet på de to øjne: ved tristhed hænger det YDRE hjørne, og
 * det kan man kun se hvis de vipper hver sin vej. `prik` var et catchlight —
 * det tegnes ikke længere (19/9-2026, se OEJE_SKALA); feltet står til Jarvis'
 * udtryk hvis det skal tilbage. Det udelodes allerede på de buede
 * glade øjne, hvor der ikke er plads til den.
 */
const ANSIGT: Record<Udtryk, { oeje: string; mund: string; rot: number; prik: boolean }> = {
  rolig: {
    oeje: 'M-3.4 -6 h6.8 a3.4 3.4 0 0 1 0 12 h-6.8 a3.4 3.4 0 0 1 0 -12 z',
    mund: 'M54.6 73.4 Q60 76.6 65.4 73.4',
    rot: 0,
    prik: true,
  },
  fokus: {
    oeje: 'M-3.4 -3.4 h6.8 a3.2 3.2 0 0 1 0 6.8 h-6.8 a3.2 3.2 0 0 1 0 -6.8 z',
    mund: 'M55.6 74.4 h8.8',
    rot: 0,
    prik: true,
  },
  venter: {
    oeje: 'M0 -6.4 a4 4 0 1 1 0 12.8 a4 4 0 1 1 0 -12.8 z',
    mund: 'M57.4 73.6 a2.6 2.6 0 1 0 5.2 0 a2.6 2.6 0 1 0 -5.2 0',
    rot: 0,
    prik: true,
  },
  noed: {
    oeje: 'M-3.4 -4.4 h6.8 a3.2 3.2 0 0 1 0 8.8 h-6.8 a3.2 3.2 0 0 1 0 -8.8 z',
    mund: 'M54.6 76.6 Q60 72.4 65.4 76.6',
    rot: 13,
    prik: true,
  },
  glad: {
    oeje: 'M-4.2 1.7 Q0 -6.6 4.2 1.7 Q0 -1.3 -4.2 1.7 z',
    mund: 'M53.6 72.4 Q60 79.2 66.4 72.4',
    rot: 0,
    prik: false,
  },
}

const OEJE_X = { venstre: 49.6, hoejre: 70.4 }
const OEJE_Y = 57.8
/**
 * Bjørn 19/9-2026: «de øjne den har er lidt creepy». Store, sorte øjne med
 * et hvidt lysglimt — det lignede solbriller der stirrede. Nu mindre, i en
 * blød mørk teal i stedet for sort, uden lysglimt, og blikket flytter sig
 * kun lidt (FigurApp). Udtrykkene pr. tilstand er Jarvis' egne og står.
 */
const OEJE_SKALA = 0.72
const OEJE_FARVE = 'rgba(12, 44, 40, 0.78)'

export function FigurKrop({ handling, ring, laener, blik, grimasse }: {
  handling: Handling
  /** Ringen drejer hurtigt mens der arbejdes — uafhængigt af kroppens tre gennemløb. */
  ring: 'rolig' | 'hurtig'
  laener: 'venstre' | 'hoejre' | null
  /** Hvor han kigger hen, i px fra øjenroen. Musen kan kun ses mens den er
   *  over vinduet — så det er når man nærmer sig at han ser op. */
  blik?: { x: number; y: number }
  grimasse?: 'smil' | 'undren' | null
}) {
  const u = udtryk(handling)
  const a = ANSIGT[u]
  const mund = handling === 'hvile' && grimasse
    ? grimasse === 'smil' ? 'M54 72.8 Q60 79.8 66 72.8' : 'M58 73.5 a2 2.7 0 1 0 4 0 a2 2.7 0 1 0 -4 0'
    : a.mund
  const b = blik ?? { x: 0, y: 0 }
  const oeje = (s: 'venstre' | 'hoejre') =>
    `translate(${OEJE_X[s] + b.x} ${OEJE_Y + b.y}) rotate(${a.rot * (s === 'venstre' ? -1 : 1)}) scale(${OEJE_SKALA})`

  return (
    <div className={`figur-krop h-${handling}${laener ? ` laener-${laener}` : ''}`} aria-hidden>
      <svg viewBox="0 0 120 120" width="112" height="112">
        <defs>
          <radialGradient id="figur-kerne" cx="50%" cy="42%" r="60%">
            <stop offset="0%" stopColor="#ffffff" stopOpacity="0.95" />
            <stop offset="35%" stopColor="var(--figur-farve)" stopOpacity="0.95" />
            <stop offset="100%" stopColor="var(--figur-farve)" stopOpacity="0.15" />
          </radialGradient>
        </defs>
        <circle className="figur-glød" cx="60" cy="60" r="44" />
        <g className={`figur-ring ring-${ring}`}>
          <circle cx="60" cy="60" r="50" fill="none" stroke="var(--figur-farve)" strokeWidth="3"
                  strokeDasharray="22 9" strokeLinecap="round" opacity="0.85" />
        </g>
        <circle cx="60" cy="60" r="34" fill="url(#figur-kerne)" />
        <g className={`figur-ansigt a-${u}`}>
          <g className="figur-oejne" fill={OEJE_FARVE}>
            {(['venstre', 'hoejre'] as const).map((s) => (
              <g key={s} transform={oeje(s)}>
                <path d={a.oeje} />
              </g>
            ))}
          </g>
          <path className="figur-mund" d={mund} fill="none" stroke={OEJE_FARVE}
                strokeWidth="1.6" strokeLinecap="round" />
        </g>
      </svg>
      <div className="figur-skygge" />
    </div>
  )
}
