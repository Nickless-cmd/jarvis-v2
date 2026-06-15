import { useEffect, useRef, useState } from 'react'
import { ChevronRight, ChevronDown, File, Folder } from 'lucide-react'
import { getTree, type TreeEntry, type ApiConfig } from '../../lib/api'

/** Rekursivt fil-træ for Code-mode. Loader børn lazily ved ekspander. onOpenFile
 *  får den fulde sti (relativt til root). highlightPath (Jarvis-styret) får træet
 *  til at auto-ekspandere stien + scrolle-til + markere filen. onContext åbner
 *  højreklik-menuen (editor/terminal). */
export function FileTree({
  config, kind, root, path = '', onOpenFile, highlightPath, onContext,
}: {
  config: ApiConfig
  kind: 'container' | 'workstation'
  root: string
  path?: string
  onOpenFile: (fullPath: string) => void
  highlightPath?: string
  onContext?: (fullPath: string, x: number, y: number) => void
}) {
  const [entries, setEntries] = useState<TreeEntry[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    let cancelled = false
    setError(null)
    getTree(config, kind, root, path)
      .then((e) => { if (!cancelled) setEntries(e) })
      .catch((err) => {
        // Tidligere blev fejl tavst til en tom liste → "viser ingen filer".
        // Surfacér i stedet hvad der gik galt (auth/jail/bro), så det kan ses.
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
          onOpenFile={onOpenFile} highlightPath={highlightPath} onContext={onContext} />
      ))}
    </ul>
  )
}

function TreeNode({
  config, kind, root, path, entry, onOpenFile, highlightPath, onContext,
}: {
  config: ApiConfig; kind: 'container' | 'workstation'; root: string
  path: string; entry: TreeEntry; onOpenFile: (p: string) => void
  highlightPath?: string
  onContext?: (p: string, x: number, y: number) => void
}) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLLIElement>(null)
  // Highlight: er denne node selve mål-filen, eller en forfader på stien?
  const isTarget = !!highlightPath && entry.kind === 'file' && highlightPath === path
  const onTargetPath = !!highlightPath && entry.kind === 'dir'
    && (highlightPath === path || highlightPath.startsWith(path + '/'))

  // Forfader-mapper på højlight-stien auto-ekspanderes (kaskaderer ned til filen).
  useEffect(() => {
    if (onTargetPath) setOpen(true)
  }, [onTargetPath])

  // Mål-filen scrolles ind i view når highlight rammer.
  useEffect(() => {
    // scrollIntoView findes ikke i jsdom (test) — guard så det ikke vælter.
    if (isTarget && ref.current?.scrollIntoView) {
      ref.current.scrollIntoView({ block: 'center', behavior: 'smooth' })
    }
  }, [isTarget])

  if (entry.kind === 'file') {
    return (
      <li
        ref={ref}
        className={`filetree-file ${isTarget ? 'highlight' : ''}`}
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
          onOpenFile={onOpenFile} highlightPath={highlightPath} onContext={onContext} />
      )}
    </li>
  )
}
