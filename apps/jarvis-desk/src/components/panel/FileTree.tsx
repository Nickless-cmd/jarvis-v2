import { useEffect, useState } from 'react'
import { ChevronRight, ChevronDown, File, Folder } from 'lucide-react'
import { getTree, type TreeEntry, type ApiConfig } from '../../lib/api'

/** Rekursivt fil-træ for Code-mode. Loader børn lazily ved ekspander. onOpenFile
 *  får den fulde sti (relativt til root). */
export function FileTree({
  config, kind, root, path = '', onOpenFile,
}: {
  config: ApiConfig
  kind: 'container' | 'workstation'
  root: string
  path?: string
  onOpenFile: (fullPath: string) => void
}) {
  const [entries, setEntries] = useState<TreeEntry[] | null>(null)
  useEffect(() => {
    let cancelled = false
    getTree(config, kind, root, path)
      .then((e) => { if (!cancelled) setEntries(e) })
      .catch(() => { if (!cancelled) setEntries([]) })
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [kind, root, path])

  if (entries === null) return <div className="filetree-loading">…</div>
  return (
    <ul className="filetree">
      {entries.map((e) => (
        <TreeNode key={e.name} config={config} kind={kind} root={root}
          path={path ? `${path}/${e.name}` : e.name} entry={e} onOpenFile={onOpenFile} />
      ))}
    </ul>
  )
}

function TreeNode({
  config, kind, root, path, entry, onOpenFile,
}: {
  config: ApiConfig; kind: 'container' | 'workstation'; root: string
  path: string; entry: TreeEntry; onOpenFile: (p: string) => void
}) {
  const [open, setOpen] = useState(false)
  if (entry.kind === 'file') {
    return (
      <li className="filetree-file" onClick={() => onOpenFile(path)}>
        <File size={13} /> {entry.name}
      </li>
    )
  }
  return (
    <li className="filetree-dir">
      <div className="filetree-dir-row" onClick={() => setOpen((o) => !o)}>
        {open ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
        <Folder size={13} /> {entry.name}
      </div>
      {open && <FileTree config={config} kind={kind} root={root} path={path} onOpenFile={onOpenFile} />}
    </li>
  )
}
