import { useEffect, useRef, useState } from 'react'
import { Check, FolderGit2, GitBranch, Loader2, Monitor, Plus, Server } from 'lucide-react'
import type { ApiConfig } from '../../lib/api'
import { hentBetroedeMapper, opretWorktree, type BetroetMappe } from '../../lib/gitWorkspace'

/**
 * Workstation-vælger (Bjørn 18/9-2026: «workstation skal være en dropdown hvor
 * man kan vælge trusted folder og ny lokal worktree»).
 *
 * Før var det en ren etiket — «Workstation» eller «Server» — uden noget at
 * vælge imellem. API'et kunne heller ikke liste betroede mapper; det kunne kun
 * svare på én ad gangen, så en vælger kunne ikke bygges.
 *
 * De to ting i menuen er forskellige af natur: en betroet mappe VÆLGES, en ny
 * worktree OPRETTES. Derfor står oprettelsen nederst bag et plus, adskilt fra
 * listen — som i branch-vælgeren.
 */
export function WorkspaceVaelger({
  config, kind, root, onVaelg,
}: {
  config?: ApiConfig
  kind: 'container' | 'workstation'
  root: string
  /** Kaldes når en anden mappe skal tages i brug. */
  onVaelg?: (valg: { kind: string; root: string }) => void
}) {
  const [åben, setÅben] = useState(false)
  const [mapper, setMapper] = useState<BetroetMappe[] | null>(null)
  const [henter, setHenter] = useState(false)
  const [nyNavn, setNyNavn] = useState('')
  const [arbejder, setArbejder] = useState(false)
  const [fejl, setFejl] = useState('')
  const rod = useRef<HTMLDivElement>(null)

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
    hentBetroedeMapper(config)
      .then(setMapper)
      .catch(() => setFejl('Kunne ikke hente betroede mapper'))
      .finally(() => setHenter(false))
  }, [åben, config])

  const opret = async () => {
    const navn = nyNavn.trim()
    if (!config || !navn || arbejder) return
    setArbejder(true); setFejl('')
    try {
      const r = await opretWorktree(config, { kind, root, name: navn })
      if (r.ok && r.path) {
        setÅben(false); setNyNavn('')
        // Stien er relativ til repoet — gør den hel, så den kan bruges direkte.
        onVaelg?.({ kind, root: `${root.replace(/\/$/, '')}/${r.path}` })
      } else {
        setFejl(r.error || 'Kunne ikke oprette worktree')
      }
    } catch {
      setFejl('Kunne ikke oprette worktree')
    } finally {
      setArbejder(false)
    }
  }

  const Ikon = kind === 'workstation' ? Monitor : Server
  return (
    <div className="env-dd" ref={rod}>
      <button
        type="button"
        className="env-label env-dd-btn"
        aria-haspopup="listbox"
        aria-expanded={åben}
        title="Vælg arbejdsmappe"
        onClick={() => setÅben((o) => !o)}
      >
        <Ikon size={13} /> {kind === 'workstation' ? 'Workstation' : 'Server'}
        <span className="env-dd-caret">▾</span>
      </button>
      {åben && (
        <div className="env-dd-menu" role="listbox" aria-label="Arbejdsmapper">
          <div className="env-dd-overskrift">Betroede mapper</div>
          <div className="env-dd-liste">
            {henter && <div className="env-dd-tom"><Loader2 size={12} className="spin" /> Henter…</div>}
            {!henter && (mapper?.length ?? 0) === 0 && (
              <div className="env-dd-tom">Ingen betroede mapper endnu</div>
            )}
            {(mapper ?? []).map((m) => (
              <button
                key={`${m.kind}:${m.root}`}
                type="button"
                role="option"
                aria-selected={m.root === root && m.kind === kind}
                className={m.root === root && m.kind === kind ? 'active' : ''}
                onClick={() => { setÅben(false); onVaelg?.({ kind: m.kind, root: m.root }) }}
              >
                {m.root === root && m.kind === kind ? <Check size={12} /> : <FolderGit2 size={12} />}
                <span className="env-dd-sti">{m.root}</span>
              </button>
            ))}
          </div>
          <div className="env-dd-overskrift">Ny lokal worktree</div>
          <div className="env-dd-soeg">
            <GitBranch size={12} />
            <input
              type="text"
              value={nyNavn}
              placeholder="navn på ny worktree"
              aria-label="Navn på ny worktree"
              onChange={(e) => setNyNavn(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') void opret() }}
            />
          </div>
          <button
            type="button"
            className="env-dd-opret"
            disabled={!nyNavn.trim() || arbejder}
            onClick={() => void opret()}
          >
            {arbejder ? <Loader2 size={12} className="spin" /> : <Plus size={12} />}
            {arbejder ? 'Opretter…' : 'Opret worktree'}
          </button>
          {fejl && <div className="env-dd-fejl">{fejl}</div>}
        </div>
      )}
    </div>
  )
}
