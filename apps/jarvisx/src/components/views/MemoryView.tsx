import { useEffect, useMemo, useState } from 'react'
import {
  Brain,
  FileText,
  Cloud,
  Calendar,
  Mail,
  ChevronDown,
  RefreshCw,
} from 'lucide-react'
import { useMcEndpoint } from '../../lib/useMcEndpoint'
import { MarkdownRenderer } from '@ui/components/chat/MarkdownRenderer.jsx'

interface CanonicalEntry {
  name: string
  label: string
  present: boolean
  size_bytes: number
}

interface DirEntry {
  name: string
  size_bytes: number
  modified_at: number
}

interface WorkspaceTree {
  workspace: string
  canonical: CanonicalEntry[]
  dreams: DirEntry[]
  daily: DirEntry[]
  letters: DirEntry[]
}

interface WorkspaceListResp {
  workspaces: { name: string; owner: string }[]
  current: string
}

interface ReadResp {
  workspace: string
  path: string
  content: string
  size_bytes: number
  truncated: boolean
}

type Section = 'canonical' | 'dreams' | 'daily' | 'letters'

export function MemoryView({ apiBaseUrl }: { apiBaseUrl: string }) {
  const [workspace, setWorkspace] = useState<string>('')
  const [section, setSection] = useState<Section>('canonical')
  const [activePath, setActivePath] = useState<string>('MEMORY.md')
  const [showWorkspaceMenu, setShowWorkspaceMenu] = useState(false)

  const wsList = useMcEndpoint<WorkspaceListResp>(apiBaseUrl, '/api/workspace/list', 0)
  const tree = useMcEndpoint<WorkspaceTree>(
    apiBaseUrl,
    workspace
      ? `/api/workspace/tree?workspace=${encodeURIComponent(workspace)}`
      : '/api/workspace/tree',
    0,
  )

  // Default workspace from /workspace/list once it loads
  useEffect(() => {
    if (!workspace && wsList.data?.current) {
      setWorkspace(wsList.data.current)
    }
  }, [wsList.data, workspace])

  // Read the active file
  const readPath = useMemo(() => {
    if (!activePath) return null
    let p = activePath
    if (section === 'dreams') p = `dreams/${activePath}`
    else if (section === 'daily') p = `memory/daily/${activePath}`
    else if (section === 'letters') p = `letters/${activePath}`
    return p
  }, [activePath, section])

  const file = useMcEndpoint<ReadResp>(
    apiBaseUrl,
    readPath
      ? `/api/workspace/read?path=${encodeURIComponent(readPath)}${
          workspace ? `&workspace=${encodeURIComponent(workspace)}` : ''
        }`
      : '',
    0,
  )

  const sectionEntries: { name: string; label?: string; subtitle?: string }[] = useMemo(() => {
    if (!tree.data) return []
    if (section === 'canonical') {
      return tree.data.canonical
        .filter((c) => c.present)
        .map((c) => ({
          name: c.name,
          label: c.label,
          subtitle: `${(c.size_bytes / 1024).toFixed(1)} kB`,
        }))
    }
    const list: DirEntry[] =
      section === 'dreams'
        ? tree.data.dreams
        : section === 'daily'
        ? tree.data.daily
        : tree.data.letters
    return list.map((e) => ({
      name: e.name,
      label: e.name.replace(/\.(md|txt)$/, ''),
      subtitle: relativeTime(e.modified_at * 1000),
    }))
  }, [tree.data, section])

  // When section changes, jump to first entry
  useEffect(() => {
    if (sectionEntries.length === 0) return
    if (!sectionEntries.find((e) => e.name === activePath)) {
      setActivePath(sectionEntries[0].name)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [section, sectionEntries.length])

  return (
    <div className="flex h-full min-h-0 flex-col">
      {/* Header */}
      <header className="flex flex-shrink-0 items-center justify-between border-b border-line bg-bg1 px-4 py-2">
        <div className="flex items-center gap-3">
          <h2 className="text-sm font-semibold">Hukommelse</h2>
          <WorkspaceSelector
            value={workspace}
            options={wsList.data?.workspaces ?? []}
            open={showWorkspaceMenu}
            onToggle={() => setShowWorkspaceMenu((o) => !o)}
            onChange={(v) => {
              setWorkspace(v)
              setShowWorkspaceMenu(false)
              setActivePath('MEMORY.md')
              setSection('canonical')
            }}
          />
        </div>
        <button
          onClick={() => {
            tree.refresh()
            file.refresh()
          }}
          className="flex items-center gap-1.5 rounded-md border border-line2 bg-bg2 px-2 py-1 text-[10px] text-fg2 hover:text-accent"
        >
          <RefreshCw size={10} />
          refresh
        </button>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Section + entry sidebar */}
        <aside className="flex w-64 min-w-0 flex-col border-r border-line bg-bg1">
          {/* Section tabs */}
          <div className="flex flex-shrink-0 border-b border-line">
            <SectionTab
              active={section === 'canonical'}
              onClick={() => setSection('canonical')}
              Icon={FileText}
              label="Files"
              count={tree.data?.canonical.filter((c) => c.present).length}
            />
            <SectionTab
              active={section === 'dreams'}
              onClick={() => setSection('dreams')}
              Icon={Cloud}
              label="Drømme"
              count={tree.data?.dreams.length}
            />
            <SectionTab
              active={section === 'daily'}
              onClick={() => setSection('daily')}
              Icon={Calendar}
              label="Daily"
              count={tree.data?.daily.length}
            />
            <SectionTab
              active={section === 'letters'}
              onClick={() => setSection('letters')}
              Icon={Mail}
              label="Breve"
              count={tree.data?.letters.length}
            />
          </div>

          {/* Entry list */}
          <div className="flex-1 overflow-y-auto">
            {tree.loading && !tree.data && (
              <div className="px-3 py-3 text-[10px] text-fg3">loading…</div>
            )}
            {sectionEntries.length === 0 && !tree.loading && (
              <div className="px-3 py-4 text-[10px] text-fg3">
                Tom — intet i denne sektion endnu.
              </div>
            )}
            {sectionEntries.map((e) => {
              const isActive = e.name === activePath
              return (
                <button
                  key={e.name}
                  onClick={() => setActivePath(e.name)}
                  className={[
                    'flex w-full flex-col items-start gap-0.5 border-b border-line/40 px-3 py-2 text-left transition-colors',
                    isActive ? 'bg-bg2' : 'hover:bg-bg2/50',
                  ].join(' ')}
                >
                  <span
                    className={[
                      'truncate text-xs font-medium',
                      isActive ? 'text-accent' : 'text-fg2',
                    ].join(' ')}
                  >
                    {e.label || e.name}
                  </span>
                  {e.subtitle && (
                    <span className="font-mono text-[9px] text-fg3">{e.subtitle}</span>
                  )}
                </button>
              )
            })}
          </div>
        </aside>

        {/* Content panel */}
        <section className="flex flex-1 min-h-0 min-w-0 flex-col overflow-hidden bg-bg0">
          <div className="flex flex-shrink-0 items-center justify-between border-b border-line bg-bg1/40 px-5 py-2">
            <div className="flex items-center gap-2">
              <Brain size={12} className="text-accent" />
              <span className="font-mono text-[11px] text-fg2">
                {readPath || '—'}
              </span>
              {file.data?.truncated && (
                <span className="rounded bg-warn/20 px-1.5 py-0.5 font-mono text-[9px] text-warn">
                  truncated
                </span>
              )}
            </div>
            {file.data && (
              <span className="font-mono text-[10px] text-fg3">
                {(file.data.size_bytes / 1024).toFixed(1)} kB
              </span>
            )}
          </div>
          <div className="flex-1 overflow-y-auto px-6 py-5">
            <div className="mx-auto max-w-3xl">
              {file.loading && !file.data && (
                <div className="text-xs text-fg3">loading file…</div>
              )}
              {file.error && (
                <div className="rounded-md border border-danger/30 bg-danger/10 px-3 py-2 font-mono text-[11px] text-danger">
                  {file.error}
                </div>
              )}
              {file.data && file.data.content && (
                <div className="prose-jarvisx-doc">
                  <MarkdownRenderer content={file.data.content} />
                </div>
              )}
              {file.data && !file.data.content && (
                <div className="text-xs text-fg3">tom fil</div>
              )}
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}

function SectionTab({
  active,
  onClick,
  Icon,
  label,
  count,
}: {
  active: boolean
  onClick: () => void
  Icon: typeof Brain
  label: string
  count?: number
}) {
  return (
    <button
      onClick={onClick}
      className={[
        'flex flex-1 flex-col items-center gap-0.5 border-r border-line/60 px-2 py-2 text-[9px] uppercase tracking-wider transition-colors',
        active
          ? 'bg-bg2 text-accent'
          : 'text-fg3 hover:bg-bg2/40 hover:text-fg2',
      ].join(' ')}
    >
      <Icon size={13} />
      <span className="font-semibold">{label}</span>
      {typeof count === 'number' && (
        <span className="font-mono text-[8px] opacity-70">{count}</span>
      )}
    </button>
  )
}

function WorkspaceSelector({
  value,
  options,
  open,
  onToggle,
  onChange,
}: {
  value: string
  options: { name: string; owner: string }[]
  open: boolean
  onToggle: () => void
  onChange: (v: string) => void
}) {
  return (
    <div className="relative">
      <button
        onClick={onToggle}
        className="flex items-center gap-1.5 rounded-md border border-line2 bg-bg2 px-2.5 py-1 text-[11px] hover:border-accent/40"
      >
        <span className="font-mono text-fg2">{value || '—'}</span>
        <ChevronDown size={10} className="text-fg3" />
      </button>
      {open && (
        <div className="absolute left-0 top-full z-20 mt-1 min-w-[200px] rounded-md border border-line2 bg-bg1 py-1 shadow-xl">
          {options.map((o) => {
            const isActive = o.name === value
            return (
              <button
                key={o.name}
                onClick={() => onChange(o.name)}
                className={[
                  'flex w-full items-center justify-between px-3 py-1.5 text-[11px] transition-colors',
                  isActive
                    ? 'bg-bg2 text-accent'
                    : 'text-fg2 hover:bg-bg2/60 hover:text-fg',
                ].join(' ')}
              >
                <span className="font-mono">{o.name}</span>
                {o.owner && (
                  <span className="font-mono text-[10px] text-fg3">{o.owner}</span>
                )}
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}

function relativeTime(ms: number): string {
  const delta = Date.now() - ms
  if (isNaN(delta) || delta < 0) return ''
  const sec = Math.floor(delta / 1000)
  if (sec < 60) return 'lige nu'
  const min = Math.floor(sec / 60)
  if (min < 60) return `${min}m`
  const hr = Math.floor(min / 60)
  if (hr < 24) return `${hr}t`
  const d = Math.floor(hr / 24)
  if (d < 30) return `${d}d`
  const mo = Math.floor(d / 30)
  return `${mo}mdr`
}
