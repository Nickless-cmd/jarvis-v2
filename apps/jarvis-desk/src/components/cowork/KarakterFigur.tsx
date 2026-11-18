import { karakterFigur, type KarakterAccessory, type KarakterShape } from '../../lib/karakterFigur'

/**
 * Én Matrix-karakters figur, tegnet som SVG.
 *
 * ## Hvorfor SVG og ikke et ikon
 *
 * Huset har ingen ikon-font, og et biblioteks-ikon kan ikke bære en
 * sammensætning (form × farve × accessory × øjne). Figuren skal kunne tegnes i
 * enhver størrelse uden at sløre — derfor vektorer, ingen PNG.
 *
 * ## Hvad figuren IKKE viser
 *
 * Tilstand. Om karakteren har kørt, og hvad den svarede, bæres af prikken og
 * udfaldskolonnen i `MatrixKarakterer.tsx`. Farven her er karakterens
 * IDENTITET — derfor er paletten i `karakterFigur.ts` holdt uden om husets
 * signal-farver. Blander man de to, ser en violet karakter ud som en tilstand
 * nogen har valgt.
 */

/** ViewBox er 48×48 for alle former; figuren fylder ca. 28 px i højden. */
const VIEWBOX = '0 0 48 48'

/** Tilbehør tegnes i en neutral, så det læses som tilbehør og ikke som krop. */
const ACCESSORY_FARVE = '#ded8cc'
const OEJE_FARVE = '#12161f'

/**
 * Blomst-formerne som matematik frem for 18 håndskrevne cirkler.
 *
 * `six_lobed_flower` og `twelve_scalloped_rosette` er de samme to tal med
 * forskellige værdier — at skrive dem som to paths ville være den samme form
 * skrevet to gange, og den ene ville drive.
 */
function lober(antal: number, ringRadius: number, lappeRadius: number) {
  return Array.from({ length: antal }, (_, i) => {
    const vinkel = (i / antal) * Math.PI * 2 - Math.PI / 2
    return (
      <circle
        key={i}
        cx={24 + Math.cos(vinkel) * ringRadius}
        cy={24 + Math.sin(vinkel) * ringRadius}
        r={lappeRadius}
      />
    )
  })
}

/** Kropsformen. Alle elementer er fyldt med `currentColor` via gruppen udenom. */
function Kropsform({ shape }: { shape: KarakterShape }) {
  switch (shape) {
    case 'capsule':
      return <rect x="14" y="8" width="20" height="32" rx="10" />
    case 'circle_two_ears':
      return (
        <>
          <circle cx="15.5" cy="13" r="4.6" />
          <circle cx="32.5" cy="13" r="4.6" />
          <circle cx="24" cy="27" r="12" />
        </>
      )
    case 'four_lobed_butterfly':
      return (
        <>
          <circle cx="16" cy="17" r="7.5" />
          <circle cx="32" cy="17" r="7.5" />
          <circle cx="16" cy="31" r="7.5" />
          <circle cx="32" cy="31" r="7.5" />
          <circle cx="24" cy="24" r="7" />
        </>
      )
    case 'heart':
      return (
        <path d="M24 39 C9 28.5 10.5 13 24 17.5 C37.5 13 39 28.5 24 39 Z" />
      )
    case 'rounded_cube':
      return <rect x="13" y="11" width="22" height="26" rx="7" />
    case 'rounded_diamond':
      return (
        <path d="M24 9 Q26.4 9 28 11.6 L36.4 21.6 Q38.6 24 36.4 26.4 L28 36.4 Q26.4 39 24 39 Q21.6 39 20 36.4 L11.6 26.4 Q9.4 24 11.6 21.6 L20 11.6 Q21.6 9 24 9 Z" />
      )
    case 'rounded_head_two_ears':
      return (
        <>
          <ellipse cx="12.5" cy="22" rx="5" ry="6.4" />
          <ellipse cx="35.5" cy="22" rx="5" ry="6.4" />
          <circle cx="24" cy="25" r="12" />
        </>
      )
    case 'rounded_triangle':
      return (
        <path d="M24 10 Q26.6 10 28.1 14.2 L37.6 32.4 Q40 37 34.8 37 L13.2 37 Q8 37 10.4 32.4 L19.9 14.2 Q21.4 10 24 10 Z" />
      )
    case 'six_lobed_flower':
      return <>{lober(6, 8.5, 7.4)}</>
    case 'twelve_scalloped_rosette':
      return (
        <>
          {lober(12, 10.4, 4.6)}
          <circle cx="24" cy="24" r="9" />
        </>
      )
    default:
      // Ukendt form skal stadig give en figur, ikke en tom plads i listen.
      return <circle cx="24" cy="24" r="12" />
  }
}

/** Tilbehøret. Tegnes over kroppen, i den neutrale farve. */
function Tilbehoer({ accessory }: { accessory: KarakterAccessory }) {
  switch (accessory) {
    case 'beanie':
      return (
        <>
          <path d="M12 18 A12 12 0 0 1 36 18 Z" />
          <rect x="11" y="16.6" width="26" height="4" rx="2" />
        </>
      )
    case 'beret':
      return (
        <>
          <ellipse cx="25" cy="13" rx="13" ry="5.4" transform="rotate(-8 25 13)" />
          <circle cx="34" cy="8.6" r="1.9" />
        </>
      )
    case 'bow':
      return (
        <>
          <path d="M33 12 L40 8.4 L40 16 L33 12.6 Z" />
          <path d="M33 12 L26 8.4 L26 16 L33 12.6 Z" />
          <circle cx="33" cy="12.2" r="2.1" />
        </>
      )
    case 'crown':
      return (
        <path d="M12 17 L16.5 9.5 L20.6 15 L24 7.5 L27.4 15 L31.5 9.5 L36 17 Z" />
      )
    case 'hat':
      return (
        <>
          <rect x="17" y="5" width="14" height="12" rx="2.4" />
          <rect x="9.5" y="15.4" width="29" height="4" rx="2" />
        </>
      )
    case 'headphones':
      return (
        <>
          <path
            d="M12 24 A12 12 0 0 1 36 24"
            fill="none"
            stroke={ACCESSORY_FARVE}
            strokeWidth="3.4"
            strokeLinecap="round"
          />
          <rect x="9.2" y="21.5" width="6" height="10" rx="3" />
          <rect x="32.8" y="21.5" width="6" height="10" rx="3" />
        </>
      )
    case 'orb':
      return (
        <>
          <circle cx="24" cy="7" r="4.6" opacity="0.75" />
          <circle cx="24" cy="7" r="2.2" />
        </>
      )
    case 'three_lobe':
      return (
        <>
          <ellipse cx="18" cy="9" rx="4" ry="5.6" transform="rotate(-22 18 9)" />
          <ellipse cx="24" cy="6.6" rx="4" ry="5.6" />
          <ellipse cx="30" cy="9" rx="4" ry="5.6" transform="rotate(22 30 9)" />
        </>
      )
    default:
      return null
  }
}

export function KarakterFigur({
  navn,
  stoerrelse = 24,
  className,
}: {
  navn: string
  stoerrelse?: number
  className?: string
}) {
  const figur = karakterFigur(navn)
  const oejeY = figur.oejeHoejde
  return (
    <svg
      className={className}
      width={stoerrelse}
      height={stoerrelse}
      viewBox={VIEWBOX}
      // Figuren er identitet, ikke information: den gentager navnet der står
      // ved siden af. For skærmlæsere ville den bare læse det samme to gange,
      // så den skjules helt — intet går tabt.
      aria-hidden="true"
      focusable="false"
    >
      <g fill={figur.farve} opacity="0.9">
        <Kropsform shape={figur.shape} />
      </g>
      {figur.accessory && (
        <g fill={ACCESSORY_FARVE} opacity="0.92">
          <Tilbehoer accessory={figur.accessory} />
        </g>
      )}
      {/* Øjnene sidst, så de aldrig skjules af en lap eller et tilbehør. */}
      <g fill={OEJE_FARVE}>
        <circle cx={24 - figur.oejeAfstand} cy={oejeY} r="1.9" />
        <circle cx={24 + figur.oejeAfstand} cy={oejeY} r="1.9" />
      </g>
    </svg>
  )
}
