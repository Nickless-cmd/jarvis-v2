import { useEffect, useRef, useState } from 'react'
import { ChevronRight, ChevronDown, File, Folder } from 'lucide-react'
import type { TreeEntry, ApiConfig } from '../../lib/api'
import { getTreeCached, peekTree } from '../../lib/treeCache'

/** Rekursivt fil-træ for Code-mode. Loader børn lazily ved ekspander; mapper
 *  caches (treeCache) så panel/tab-skift ikke re-henter samme mappe (tungt lokalt).
 *  highlightPath (Jarvis-eksplicit) auto-ekspanderer + scroller-til + åbner filen;
 *  activePath (live: filer Jarvis læser/skriver netop nu) markeres diskret uden at
 *  åbne preview. onContext åbner højreklik-menuen (editor/terminal). */
export function FileTree({
  config, kind, root, path = '', onOpenFile, highlightPath, activePath, onContext,
}: {
  config: ApiConfig
  kind: 'container' | 'workstation'
  root: string
  path?: string
  onOpenFile: (fullPath: string) => void
  highlightPath?: string
  activePath?: string
  onContext?: (fullPath: string, x: number, y: number) => void
}) {
  // Cache-first: instant render hvis mappen er kendt, ellers hent + gem.
  const [entries, setEntries] = useState<TreeEntry[] | null>(() => peekTree(kind, root, path) ?? null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    let cancelled = false
    setError(null)
    const cached = peekTree(kind, root, path)
    if (cached) setEntries(cached)
    getTreeCached(config, kind, root, path)
      .then((e) => { if (!cancelled) setEntries(e) })
      .catch((err) => {
        if (!cancelled) { setEntries([]); setError(err instanceof Error ? err.message : 'ukendt fejl') }
      })
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [kind, root, path])

  if (entries === null) return <div className="filetree-loading">…</div>
  if (error) return <div className="filetree-error">Kunne ikke hente filer: {error}</div>
  if (entries.length === 0 && !path) return <div className="filetree-empty">Tom mappe.</div>
  return (
    <ul className="filetree">
      {entries.map((e) => (
        <TreeNode key={e.name} config={config} kind={kind} root={root}
          path={path ? `${path}/${e.name}` : e.name} entry={e}
          onOpenFile={onOpenFile} highlightPath={highlightPath} activePath={activePath} onContext={onContext} />
      ))}
    </ul>
  )
}

function TreeNode({
  config, kind, root, path, entry, onOpenFile, highlightPath, activePath, onContext,
}: {
  config: ApiConfig; kind: 'container' | 'workstation'; root: string
  path: string; entry: TreeEntry; onOpenFile: (p: string) => void
  highlightPath?: string; activePath?: string
  onContext?: (p: string, x: number, y: number) => void
}) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLLIElement>(null)
  const isFile = entry.kind === 'file'
  // Eksplicit highlight (Jarvis pegede) vs. live aktiv-fil (læser/skriver nu).
  const isTarget = !!highlightPath && isFile && highlightPath === path
  const isActive = !!activePath && isFile && activePath === path
  const onPath = (p?: string) => !!p && entry.kind === 'dir' && (p === path || p.startsWith(path + '/'))
  const onTargetPath = onPath(highlightPath) || onPath(activePath)

  // Forfader-mapper på en highlight/aktiv-sti auto-ekspanderes (kaskaderer ned).
  useEffect(() => { if (onTargetPath) setOpen(true) }, [onTargetPath])

  // Mål-/aktiv-filen scrolles ind i view. scrollIntoView mangler i jsdom → guard.
  useEffect(() => {
    if ((isTarget || isActive) && ref.current?.scrollIntoView) {
      ref.current.scrollIntoView({ block: 'center', behavior: 'smooth' })
    }
  }, [isTarget, isActive])

  if (isFile) {
    return (
      <li
        ref={ref}
        className={`filetree-file ${isTarget ? 'highlight' : ''} ${isActive ? 'active-file' : ''}`}
        onClick={() => onOpenFile(path)}
        onContextMenu={onContext ? (e) => { e.preventDefault(); onContext(path, e.clientX, e.clientY) } : undefined}
        title={entry.name}
      >
        <File size={13} /> <span className="filetree-name">{entry.name}</span>
      </li>
    )
  }
  return (
    <li className="filetree-dir">
      <div className="filetree-dir-row" onClick={() => setOpen((o) => !o)} title={entry.name}>
        {open ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
        <Folder size={13} /> <span className="filetree-name">{entry.name}</span>
      </div>
      {open && (
        <FileTree config={config} kind={kind} root={root} path={path}
          onOpenFile={onOpenFile} highlightPath={highlightPath} activePath={activePath} onContext={onContext} />
      )}
    </li>
  )
}
