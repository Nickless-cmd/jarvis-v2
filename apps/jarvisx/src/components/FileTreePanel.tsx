import { useEffect, useState, useCallback, useMemo } from 'react'
import {
  Folder,
  FolderOpen,
  File as FileIcon,
  ChevronRight,
  ChevronDown,
  X,
  RefreshCw,
} from 'lucide-react'
import { MarkdownRenderer } from '@ui/components/chat/MarkdownRenderer.jsx'

interface TreeNode {
  name: string
  kind: 'dir' | 'file'
  path: string
  children?: TreeNode[]
  size_bytes?: number
  truncated?: boolean
  skipped?: boolean
}

interface TreeResp {
  root: string
  tree: TreeNode
  entry_count: number
}

interface ReadResp {
  root: string
  path: string
  rel: string
  content: string
  size_bytes: number
  truncated: boolean
}

interface Props {
  apiBaseUrl: string
  projectRoot: string
  onClose: () => void
}

/**
 * Right-side panel showing the anchored project's file tree.
 * Click a file → preview in the lower half. Click a folder → expand.
 *
 * The preview uses MarkdownRenderer for .md files, syntax-highlighted
 * code (via the same MarkdownRenderer's code-block path) for source
 * files. Plain text fallback otherwise.
 */
export function FileTreePanel({ apiBaseUrl, projectRoot, onClose }: Props) {
  const [tree, setTree] = useState<TreeResp | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set())
  const [selectedPath, setSelectedPath] = useState<string | null>(null)
  const [fileContent, setFileContent] = useState<ReadResp | null>(null)
  const [filter, setFilter] = useState('')

  const fetchTree = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const url = `${apiBaseUrl.replace(
        /\/$/,
        '',
      )}/api/project/tree?root=${encodeURIComponent(projectRoot)}&max_depth=4`
      const res = await fetch(url)
      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }))
        throw new Error(body.detail || `HTTP ${res.status}`)
      }
      const j = (await res.json()) as TreeResp
      setTree(j)
      // Auto-expand root + first level
      setExpanded(
        new Set([
          j.tree.path,
          ...(j.tree.children
            ?.filter((c) => c.kind === 'dir' && !c.skipped)
            .slice(0, 3)
            .map((c) => c.path) ?? []),
        ]),
      )
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }, [apiBaseUrl, projectRoot])

  useEffect(() => {
    fetchTree()
  }, [fetchTree])

  const toggleExpand = (path: string) => {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(path)) next.delete(path)
      else next.add(path)
      return next
    })
  }

  const selectFile = useCallback(
    async (path: string) => {
      setSelectedPath(path)
      setFileContent(null)
      // Cross-app: also surface in the right preview pane if it's open
      window.dispatchEvent(
        new CustomEvent('jarvisx:preview-file', { detail: { path } }),
      )
      try {
        const url = `${apiBaseUrl.replace(
          /\/$/,
          '',
        )}/api/project/read?root=${encodeURIComponent(
          projectRoot,
        )}&path=${encodeURIComponent(path)}`
        const res = await fetch(url)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const j = (await res.json()) as ReadResp
        setFileContent(j)
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : String(e))
      }
    },
    [apiBaseUrl, projectRoot],
  )

  // Filter logic — when set, expand all paths matching and only render those
  const filteredPaths = useMemo(() => {
    if (!filter.trim() || !tree) return null
    const q = filter.toLowerCase()
    const matches = new Set<string>()
    const visit = (n: TreeNode) => {
      if (n.kind === 'file' && n.path.toLowerCase().includes(q)) {
        matches.add(n.path)
        // Add all parent dirs to keep them visible
        const parts = n.path.replace(tree.tree.path, '').split('/').filter(Boolean)
        let cur = tree.tree.path
        for (const part of parts) {
          cur += `/${part}`
          matches.add(cur)
        }
      }
      n.children?.forEach(visit)
    }
    visit(tree.tree)
    return matches
  }, [filter, tree])

  return (
    <aside className="flex h-full w-[360px] flex-shrink-0 flex-col border-l border-line bg-bg1">
      <header className="flex flex-shrink-0 items-center gap-2 border-b border-line px-3 py-2">
        <FolderOpen size={12} className="text-accent" />
        <div className="min-w-0 flex-1">
          <div className="truncate text-[11px] font-semibold">Project</div>
          <div className="truncate font-mono text-[9px] text-fg3">
            {projectRoot.replace(/^\/home\/[^/]+/, '~')}
          </div>
        </div>
        <button
          onClick={fetchTree}
          title="Refresh tree"
          className="flex h-6 w-6 items-center justify-center rounded text-fg3 hover:bg-bg2 hover:text-accent"
        >
          <RefreshCw size={11} />
        </button>
        <button
          onClick={onClose}
          title="Hide panel"
          className="flex h-6 w-6 items-center justify-center rounded text-fg3 hover:bg-bg2 hover:text-fg"
        >
          <X size={11} />
        </button>
      </header>

      <div className="flex flex-shrink-0 items-center gap-2 border-b border-line/60 px-3 py-1.5">
        <input
          type="text"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="Filter (substring)…"
          className="flex-1 rounded bg-bg2 px-2 py-1 font-mono text-[10px] text-fg placeholder:text-fg3 focus:outline-none focus:ring-1 focus:ring-accent/30"
        />
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-2 py-1.5 font-mono text-[11px]">
        {loading && !tree && <div className="px-2 py-2 text-fg3">loading…</div>}
        {error && (
          <div className="rounded-md border border-danger/30 bg-danger/10 px-2 py-1.5 text-[10px] text-danger">
            {error}
          </div>
        )}
        {tree && (
          <TreeNodeView
            node={tree.tree}
            depth={0}
            expanded={expanded}
            toggleExpand={toggleExpand}
            selectedPath={selectedPath}
            onSelect={selectFile}
            filteredPaths={filteredPaths}
          />
        )}
      </div>

      {selectedPath && (
        <div className="flex max-h-[45%] min-h-[160px] flex-shrink-0 flex-col border-t border-line bg-bg0">
          <div className="flex flex-shrink-0 items-center justify-between border-b border-line/60 bg-bg1/40 px-3 py-1.5">
            <span className="truncate font-mono text-[10px] text-fg2">
              {fileContent?.rel || '…'}
            </span>
            {fileContent?.truncated && (
              <span className="rounded bg-warn/20 px-1.5 py-0.5 font-mono text-[9px] text-warn">
                truncated
              </span>
            )}
          </div>
          <div className="flex-1 overflow-y-auto px-3 py-2 text-[11px]">
            {!fileContent && <div className="text-fg3">loading…</div>}
            {fileContent && fileContent.path.endsWith('.md') ? (
              <div className="prose-jarvisx-doc">
                <MarkdownRenderer content={fileContent.content} />
              </div>
            ) : fileContent ? (
              <pre className="whitespace-pre-wrap break-words text-fg2">
                <code>{fileContent.content}</code>
              </pre>
            ) : null}
          </div>
        </div>
      )}
    </aside>
  )
}

function TreeNodeView({
  node,
  depth,
  expanded,
  toggleExpand,
  selectedPath,
  onSelect,
  filteredPaths,
}: {
  node: TreeNode
  depth: number
  expanded: Set<string>
  toggleExpand: (p: string) => void
  selectedPath: string | null
  onSelect: (p: string) => void
  filteredPaths: Set<string> | null
}) {
  if (filteredPaths && !filteredPaths.has(node.path)) return null

  const indent = depth * 12

  if (node.kind === 'dir') {
    const isOpen = expanded.has(node.path) || (filteredPaths !== null && filteredPaths.has(node.path))
    return (
      <div>
        <button
          onClick={() => toggleExpand(node.path)}
          className="group flex w-full items-center gap-1 rounded px-1 py-0.5 text-left hover:bg-bg2/50"
          style={{ paddingLeft: indent }}
        >
          {isOpen ? (
            <ChevronDown size={9} className="flex-shrink-0 text-fg3" />
          ) : (
            <ChevronRight size={9} className="flex-shrink-0 text-fg3" />
          )}
          {isOpen ? (
            <FolderOpen size={11} className="flex-shrink-0 text-accent" />
          ) : (
            <Folder size={11} className="flex-shrink-0 text-fg3 group-hover:text-fg2" />
          )}
          <span className="truncate text-fg2 group-hover:text-fg">{node.name}</span>
          {node.skipped && (
            <span className="ml-auto font-mono text-[8px] text-fg3 opacity-60">skipped</span>
          )}
          {node.truncated && (
            <span className="ml-auto font-mono text-[8px] text-warn opacity-80">…</span>
          )}
        </button>
        {isOpen &&
          !node.skipped &&
          node.children?.map((child) => (
            <TreeNodeView
              key={child.path}
              node={child}
              depth={depth + 1}
              expanded={expanded}
              toggleExpand={toggleExpand}
              selectedPath={selectedPath}
              onSelect={onSelect}
              filteredPaths={filteredPaths}
            />
          ))}
      </div>
    )
  }

  // File
  const active = node.path === selectedPath
  return (
    <button
      onClick={() => onSelect(node.path)}
      className={[
        'group flex w-full items-center gap-1 rounded px-1 py-0.5 text-left',
        active ? 'bg-accent/10 text-accent' : 'text-fg2 hover:bg-bg2/50 hover:text-fg',
      ].join(' ')}
      style={{ paddingLeft: indent + 14 }}
    >
      <FileIcon size={10} className={active ? 'text-accent' : 'text-fg3'} />
      <span className="truncate">{node.name}</span>
      {typeof node.size_bytes === 'number' && (
        <span className="ml-auto font-mono text-[8px] text-fg3 opacity-50">
          {formatSize(node.size_bytes)}
        </span>
      )}
    </button>
  )
}

function formatSize(n: number): string {
  if (n < 1024) return `${n}B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)}K`
  return `${(n / 1024 / 1024).toFixed(1)}M`
}
