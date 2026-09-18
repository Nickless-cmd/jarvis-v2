/**
 * Den fælles tabel: klæbende hoved, sortering og vandret indeholdelse.
 *
 * Speccen: «Tables have sticky headers, stable column widths, sort controls,
 * filters, and responsive horizontal containment». De fire ting hører sammen
 * ét sted — tre tabeller der hver implementerer deres egen sortering ville
 * før eller siden sortere forskelligt på det samme.
 *
 * ## Hvorfor sorteringen er en komponent og ikke en `sort()`
 *
 * En kolonne kan bære tal, tekst eller ingenting. `undefined` må ikke lande
 * øverst, fordi «ved ikke» ikke er den højeste værdi — det er fraværet af en.
 * Den regel skal stå ét sted.
 */
import { useMemo, useState, type ReactNode } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'

export interface Kolonne<T> {
  id: string
  navn: string
  /** Værdien der sorteres på. `undefined` betyder «ingen værdi». */
  vaerdi?: (r: T) => string | number | undefined
  celle: (r: T) => ReactNode
  /** Sat → kolonnen er ikke sorterbar (fx en knap-kolonne). */
  fast?: boolean
}

export function CheapLaneTabel<T>({
  raekker, kolonner, noegle, tom = 'Ingen rækker.',
}: {
  raekker: T[]
  kolonner: Kolonne<T>[]
  noegle: (r: T) => string
  tom?: string
}) {
  const [sorterPaa, setSorterPaa] = useState('')
  const [faldende, setFaldende] = useState(false)

  const sorteret = useMemo(() => {
    const k = kolonner.find((c) => c.id === sorterPaa)
    if (!k?.vaerdi) return raekker
    const ud = [...raekker]
    ud.sort((a, b) => {
      const va = k.vaerdi!(a)
      const vb = k.vaerdi!(b)
      // «Ved ikke» er ikke den hoejeste vaerdi — den er fravaeret af en, og
      // staar derfor altid nederst, uanset retning.
      if (va === undefined && vb === undefined) return 0
      if (va === undefined) return 1
      if (vb === undefined) return -1
      const r = typeof va === 'number' && typeof vb === 'number'
        ? va - vb
        : String(va).localeCompare(String(vb), 'da-DK')
      return faldende ? -r : r
    })
    return ud
  }, [raekker, kolonner, sorterPaa, faldende])

  if (!raekker.length) return <p className="cl-tom">{tom}</p>

  return (
    <div className="cl-tabel-holder">
      <table className="cl-tabel cl-tabel-klaebende">
        <thead>
          <tr>
            {kolonner.map((k) => (
              <th key={k.id} scope="col"
                  aria-sort={sorterPaa === k.id ? (faldende ? 'descending' : 'ascending') : undefined}>
                {k.fast || !k.vaerdi ? k.navn : (
                  <button type="button" className="cl-sorter"
                          onClick={() => {
                            if (sorterPaa === k.id) setFaldende((f) => !f)
                            else { setSorterPaa(k.id); setFaldende(false) }
                          }}>
                    {k.navn}
                    {sorterPaa === k.id
                      ? (faldende ? <ChevronDown size={12} aria-hidden="true" />
                                  : <ChevronUp size={12} aria-hidden="true" />)
                      : null}
                  </button>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorteret.map((r, i) => (
            <tr key={noegle(r) || String(i)}>
              {kolonner.map((k, j) => (
                j === 0
                  ? <th key={k.id} scope="row">{k.celle(r)}</th>
                  : <td key={k.id}>{k.celle(r)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/**
 * Status med ikon, ord og tone — aldrig farve alene.
 *
 * Speccen siger det ligeud, og grunden er triviel og alligevel let at glemme:
 * en rød og en grøn prik ligner hinanden for den der ikke ser forskel på dem.
 */
export function Status({ status }: { status?: string }) {
  const s = String(status ?? '').toLowerCase()
  const tegn = s === 'healthy' || s === 'ok' || s === 'aktiv' ? '●'
    : s === 'cooldown' || s === 'recovering' ? '◐'
      : s === 'disabled' || s === 'slået fra' ? '○'
        : s === 'stale' ? '◌' : '·'
  return (
    <span className={`cl-status cl-status-${s || 'ukendt'}`}>
      <span aria-hidden="true">{tegn}</span>
      {status || 'ukendt'}
    </span>
  )
}
