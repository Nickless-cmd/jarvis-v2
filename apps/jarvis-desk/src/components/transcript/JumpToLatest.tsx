import { ArrowDown } from 'lucide-react'

/**
 * «Hop til nyeste» — Claude Desktops `jump-to-latest` (cc-desktop-chatview.md
 * §10), fælles for ChatView og CodeView.
 *
 * Forskellen fra den gamle knap: den er ALTID i DOM'en og toner ind/ud på
 * 200 ms i stedet for at poppe; er man i bund, er den `inert` (usynlig og
 * ikke til at tabbe til); og mens svaret strømmer har den accent-kant — den
 * siger at der KOMMER noget, ikke kun at man er scrollet væk.
 */
export function JumpToLatest({ synlig, live, ulaeste, onClick }: {
  synlig: boolean
  live: boolean
  ulaeste: number
  onClick: () => void
}) {
  return (
    <button
      type="button"
      data-testid="jump-to-latest"
      className={`scroll-bottom-btn jump-to-latest${synlig ? ' er-synlig' : ''}${live ? ' er-live' : ''}`}
      onClick={onClick}
      aria-label="Hop til nyeste"
      aria-hidden={!synlig}
      inert={!synlig}
      tabIndex={synlig ? 0 : -1}
    >
      <ArrowDown size={16} />
      {ulaeste > 0 && <span className="scroll-badge">{ulaeste} ny{ulaeste > 1 ? 'e' : ''}</span>}
    </button>
  )
}
