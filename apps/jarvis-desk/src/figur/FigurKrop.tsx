import type { Handling } from './figurLogik'

/**
 * Jarvis' krop: en lysende kerne med en segmenteret ring — J.A.R.V.I.S.,
 * ikke et dyr. Codex' ni kæledyr er OpenAI's egne tegninger; dem låner vi
 * ikke. Reglerne for bevægelse er derimod deres (se figurLogik).
 *
 * Farven er tilstanden, samme som linjen i sidepanelet og prikken på
 * telefonen: accent hviler/arbejder, gul venter, rød fejlede, grøn færdig.
 */
export function FigurKrop({ handling, ring, laener }: {
  handling: Handling
  /** Ringen drejer hurtigt mens der arbejdes — uafhængigt af kroppens tre gennemløb. */
  ring: 'rolig' | 'hurtig'
  laener: 'venstre' | 'hoejre' | null
}) {
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
        <g className="figur-oejne">
          <rect x="46" y="52" width="7" height="12" rx="3.5" fill="#0d1413" />
          <rect x="67" y="52" width="7" height="12" rx="3.5" fill="#0d1413" />
        </g>
      </svg>
      <div className="figur-skygge" />
    </div>
  )
}
