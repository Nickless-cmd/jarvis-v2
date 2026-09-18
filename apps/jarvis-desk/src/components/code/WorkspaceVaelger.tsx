import { useEffect, useRef, useState } from 'react'
import { Check, FolderOpen, GitBranch, Loader2, Monitor, Plus, Server } from 'lucide-react'
import type { ApiConfig } from '../../lib/api'
import { opretWorktree } from '../../lib/gitWorkspace'
import { husArbejdsmappe, laesArbejdsmapper, mappeNavn } from '../../lib/arbejdsmapper'

/**
 * Arbejdsmappe-vælger (Bjørn 18/9-2026).
 *
 * Kilden er DIN maskine, ikke serverens trust-tabel. Første udgave læste
 * `workspace_trust`, og den havde ti rækker fra juni-juli med `C:\` og
 * `/Users/bjornslot/Documents` — mapper fra andre maskiner. Den ville have vist
 * en liste over noget der ikke findes.
 *
 * Nu: den valgte mappe øverst, de mapper der HAR været valgt nedenunder, en
 * native vælger til nye, og nederst en ny lokal worktree. De to nederste er
 * forskellige af natur — man VÆLGER en mappe, man OPRETTER en worktree.
 */
export function WorkspaceVaelger({
  config, kind, root, onVaelg, onVaelgMappe,
}: {
  config?: ApiConfig
  kind: 'container' | 'workstation'
  root: string
  /** En anden mappe skal i brug. */
  onVaelg?: (valg: { kind: string; root: string }) => void
  /** Åbn den native mappe-vælger. Returnerer stien, eller null hvis afbrudt. */
  onVaelgMappe?: () => Promise<string | null>
}) {
  const [åben, setÅben] = useState(false)
  const [historik, setHistorik] = useState<string[]>([])
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

  useEffect(() => { if (åben) setHistorik(laesArbejdsmapper()) }, [åben])
  // Den mappe der er i brug skal altid stå i historikken, også første gang.
  useEffect(() => { if (root && kind === 'workstation') husArbejdsmappe(root) }, [root, kind])

  const tag = (sti: string) => {
    setÅben(false)
    husArbejdsmappe(sti)
    onVaelg?.({ kind: 'workstation', root: sti })
  }

  const vaelgNy = async () => {
    if (!onVaelgMappe) return
    const p = await onVaelgMappe()
    if (p) tag(p)
  }

  const opret = async () => {
    const navn = nyNavn.trim()
    if (!config || !navn || arbejder || !root) return
    setArbejder(true); setFejl('')
    try {
      const r = await opretWorktree(config, { kind, root, name: navn })
      if (r.ok && r.path) {
        setNyNavn('')
        // Serveren svarer med en sti RELATIV til repoet; gør den hel, ellers
        // peger den på ingenting.
        tag(`${root.replace(/\/$/, '')}/${r.path}`)
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
  const etiket = kind === 'workstation' ? (root ? mappeNavn(root) : 'Vælg mappe') : 'Server'
  return (
    <div className="env-dd" ref={rod}>
      <button
        type="button"
        className="env-label env-dd-btn"
        aria-haspopup="listbox"
        aria-expanded={åben}
        title={root || 'Vælg arbejdsmappe'}
        onClick={() => setÅben((o) => !o)}
      >
        <Ikon size={13} /> {etiket}
        <span className="env-dd-caret">▾</span>
      </button>
      {åben && (
        <div className="env-dd-menu" role="listbox" aria-label="Arbejdsmapper">
          <div className="env-dd-overskrift">Mapper på din maskine</div>
          <div className="env-dd-liste">
            {historik.length === 0 && (
              <div className="env-dd-tom">Ingen valgt endnu</div>
            )}
            {historik.map((m) => (
              <button
                key={m}
                type="button"
                role="option"
                aria-selected={m === root}
                className={m === root ? 'active' : ''}
                title={m}
                onClick={() => tag(m)}
              >
                {m === root ? <Check size={12} /> : <span className="env-dd-plads" />}
                <span className="env-dd-sti">{m}</span>
              </button>
            ))}
          </div>
          {onVaelgMappe && (
            <button type="button" className="env-dd-opret" onClick={() => void vaelgNy()}>
              <FolderOpen size={12} /> Vælg en anden mappe…
            </button>
          )}
          {root && (
            <>
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
            </>
          )}
          {fejl && <div className="env-dd-fejl">{fejl}</div>}
        </div>
      )}
    </div>
  )
}
