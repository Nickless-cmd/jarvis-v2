import { useEffect, useMemo, useRef, useState } from 'react'
import { Check, GitBranch, Loader2, Plus, Search } from 'lucide-react'
import type { ApiConfig } from '../../lib/api'
import { hentBranches, skiftBranch, type BranchListe } from '../../lib/gitWorkspace'
import { mappeNavn } from '../../lib/arbejdsmapper'

/**
 * Branch-vælger (Bjørn 18/9-2026: «main skal osse være dropdown med søgefelt
 * øverst og et view med alle branches og i bunden et + ikon til opret og
 * udcheck ny branch»).
 *
 * Før stod branchen som ren tekst. API'et kunne heller ikke svare på andet end
 * «hvilken branch er jeg på» — listen og skiftet er nye ruter.
 *
 * Listen hentes FØRST når menuen åbnes. Et repo kan have hundredvis af
 * branches (dette har 40+ lokale og lige så mange fjerne), og de skal ikke
 * hentes for at tegne en etiket der som regel bare siger «main».
 */
export function BranchVaelger({
  config, kind, root, aktuel, onSkiftet,
}: {
  config?: ApiConfig
  kind: 'container' | 'workstation'
  root: string
  aktuel: string
  onSkiftet?: (branch: string) => void
}) {
  const [åben, setÅben] = useState(false)
  const [søg, setSøg] = useState('')
  const [liste, setListe] = useState<BranchListe | null>(null)
  const [henter, setHenter] = useState(false)
  const [fejl, setFejl] = useState('')
  const [arbejder, setArbejder] = useState('')
  const rod = useRef<HTMLDivElement>(null)
  const søgeFelt = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (!åben) return
    const luk = (e: MouseEvent) => { if (!rod.current?.contains(e.target as Node)) setÅben(false) }
    const tast = (e: KeyboardEvent) => { if (e.key === 'Escape') setÅben(false) }
    window.addEventListener('mousedown', luk)
    window.addEventListener('keydown', tast)
    return () => { window.removeEventListener('mousedown', luk); window.removeEventListener('keydown', tast) }
  }, [åben])

  useEffect(() => {
    if (!åben || !config) return
    setHenter(true); setFejl('')
    hentBranches(config, kind, root)
      .then((r) => { setListe(r); if (!r.ok) setFejl('Kunne ikke læse branches') })
      .catch(() => setFejl('Kunne ikke læse branches'))
      .finally(() => { setHenter(false); søgeFelt.current?.focus() })
  }, [åben, config, kind, root])

  const filtreret = useMemo(() => {
    const q = søg.trim().toLowerCase()
    const alle = [...(liste?.local ?? []), ...(liste?.remote ?? [])]
    return q ? alle.filter((b) => b.toLowerCase().includes(q)) : alle
  }, [liste, søg])

  // Skrives noget der ikke findes, er det et NYT branch-navn. Så bliver
  // plus-knappen konkret i stedet for at spørge i endnu en dialog.
  const nytNavn = søg.trim()
  const kanOprette = nytNavn.length > 0 && !filtreret.includes(nytNavn)

  const vælg = async (navn: string, opret: boolean) => {
    if (!config || arbejder) return
    setArbejder(navn); setFejl('')
    try {
      const r = await skiftBranch(config, { kind, root, name: navn, create: opret })
      if (r.ok) { setÅben(false); setSøg(''); onSkiftet?.(r.current || navn) }
      else setFejl(r.error || 'Skiftet lykkedes ikke')
    } catch {
      setFejl('Skiftet lykkedes ikke')
    } finally {
      setArbejder('')
    }
  }

  return (
    <div className="env-dd" ref={rod}>
      <button
        type="button"
        className="env-label env-dd-btn"
        aria-haspopup="listbox"
        aria-expanded={åben}
        title="Skift branch"
        onClick={() => setÅben((o) => !o)}
      >
        <GitBranch size={13} /> {aktuel || '—'}
        <span className="env-dd-caret">▾</span>
      </button>
      {åben && (
        <div className="env-dd-menu" role="listbox" aria-label="Branches">
          {/* Hvilket repo lister vi? Uden det staar der bare en liste navne,
              og med flere arbejdsmapper i spil ved man ikke hvis branches det
              er (Bjoern 18/9-2026). */}
          <div className="env-dd-overskrift" title={root}>
            {root ? mappeNavn(root) : 'ukendt repo'}
          </div>
          <div className="env-dd-soeg">
            <Search size={12} />
            <input
              ref={søgeFelt}
              type="text"
              value={søg}
              placeholder="Søg eller skriv nyt navn"
              aria-label="Søg i branches"
              onChange={(e) => setSøg(e.target.value)}
            />
          </div>
          <div className="env-dd-liste">
            {henter && <div className="env-dd-tom"><Loader2 size={12} className="spin" /> Henter…</div>}
            {!henter && filtreret.length === 0 && (
              <div className="env-dd-tom">{søg.trim() ? 'Ingen match' : 'Ingen branches'}</div>
            )}
            {filtreret.map((b) => (
              <button
                key={b}
                type="button"
                role="option"
                aria-selected={b === aktuel}
                className={b === aktuel ? 'active' : ''}
                disabled={!!arbejder}
                onClick={() => void vælg(b, false)}
              >
                {b === aktuel ? <Check size={12} /> : <span className="env-dd-plads" />}
                {b}
              </button>
            ))}
          </div>
          {kanOprette && (
            <button
              type="button"
              className="env-dd-opret"
              disabled={!!arbejder}
              onClick={() => void vælg(nytNavn, true)}
            >
              <Plus size={12} /> Opret og skift til «{nytNavn}»
            </button>
          )}
          {fejl && <div className="env-dd-fejl">{fejl}</div>}
        </div>
      )}
    </div>
  )
}
