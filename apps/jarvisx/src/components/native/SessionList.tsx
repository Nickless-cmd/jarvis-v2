import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { MoreHorizontal, Pencil, Trash2 } from 'lucide-react'

interface Session {
  id: string
  title: string
  updated_at?: string
}

interface Props {
  sessions: Session[]
  activeSessionId: string | null
  onSelect: (id: string) => void
  onRename: (id: string, title: string) => void
  onDelete: (id: string) => void
}

function relativeTime(dateStr?: string) {
  if (!dateStr) return ''
  const delta = Date.now() - new Date(dateStr).getTime()
  if (isNaN(delta) || delta < 0) return ''
  const sec = Math.floor(delta / 1000)
  if (sec < 60) return 'nu'
  const min = Math.floor(sec / 60)
  if (min < 60) return `${min}m`
  const hr = Math.floor(min / 60)
  if (hr < 24) return `${hr}t`
  return `${Math.floor(hr / 24)}d`
}

/**
 * Native desktop-feel session list. Replaces apps/ui's SidebarSessions
 * inside JarvisX so rows match the sidebar nav language (rounded hover,
 * accent dot when active, no card-in-card framing) instead of feeling
 * like a webchat panel embedded in a desktop sidebar.
 *
 * Affordances:
 *   - Click row → select session
 *   - Hover row → ellipsis appears
 *   - Ellipsis → portal dropdown with Omdøb / Slet
 *   - Omdøb → swaps title to inline <input>; Enter saves, Esc cancels
 *   - Slet → inline two-step confirm (row turns red, click again to confirm)
 */
export function SessionList({
  sessions,
  activeSessionId,
  onSelect,
  onRename,
  onDelete,
}: Props) {
  const [menu, setMenu] = useState<{ id: string; rect: DOMRect } | null>(null)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null)

  // Auto-clear pending delete confirm if user clicks elsewhere
  useEffect(() => {
    if (!confirmDeleteId) return
    const t = setTimeout(() => setConfirmDeleteId(null), 3000)
    return () => clearTimeout(t)
  }, [confirmDeleteId])

  if (!sessions.length) {
    return <div className="px-3 py-2 text-[10px] text-fg3">Ingen chats endnu</div>
  }

  return (
    <div className="flex flex-col gap-0.5 px-2">
      {sessions.map((s) => {
        const isActive = s.id === activeSessionId
        const isEditing = editingId === s.id
        const isConfirmingDelete = confirmDeleteId === s.id

        if (isEditing) {
          return (
            <RenameRow
              key={s.id}
              initial={s.title}
              onCommit={(t) => {
                if (t && t !== s.title) onRename(s.id, t)
                setEditingId(null)
              }}
              onCancel={() => setEditingId(null)}
            />
          )
        }

        return (
          <div
            key={s.id}
            onClick={() => onSelect(s.id)}
            title={s.title}
            className={[
              'group relative flex cursor-pointer items-center gap-2 rounded-md px-2.5 py-1.5 text-[12px] transition-colors',
              isConfirmingDelete
                ? 'bg-danger/15 text-danger ring-1 ring-danger/30'
                : isActive
                ? 'bg-bg2 text-fg ring-1 ring-line2'
                : 'text-fg2 hover:bg-bg2/60 hover:text-fg',
            ].join(' ')}
          >
            <span className="min-w-0 flex-1 truncate">
              {isConfirmingDelete ? `Slet "${s.title}"?` : s.title}
            </span>
            {!isConfirmingDelete && (
              <span className="font-mono text-[9px] text-fg3 opacity-0 transition-opacity group-hover:opacity-100">
                {relativeTime(s.updated_at)}
              </span>
            )}
            {isConfirmingDelete ? (
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  onDelete(s.id)
                  setConfirmDeleteId(null)
                }}
                className="rounded bg-danger/30 px-2 py-0.5 text-[10px] font-semibold text-danger hover:bg-danger/40"
              >
                Slet
              </button>
            ) : (
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
                  setMenu(menu?.id === s.id ? null : { id: s.id, rect })
                }}
                title="Mere"
                className="flex h-5 w-5 flex-shrink-0 items-center justify-center rounded text-fg3 opacity-0 transition-opacity hover:bg-bg1 hover:text-fg group-hover:opacity-100"
              >
                <MoreHorizontal size={12} />
              </button>
            )}
            {isActive && !isConfirmingDelete && (
              <span className="h-1.5 w-1.5 flex-shrink-0 rounded-full bg-accent" />
            )}
          </div>
        )
      })}

      {menu && (
        <DropdownMenu
          rect={menu.rect}
          onClose={() => setMenu(null)}
          onRename={() => {
            setEditingId(menu.id)
            setMenu(null)
          }}
          onDelete={() => {
            setConfirmDeleteId(menu.id)
            setMenu(null)
          }}
        />
      )}
    </div>
  )
}

function RenameRow({
  initial,
  onCommit,
  onCancel,
}: {
  initial: string
  onCommit: (t: string) => void
  onCancel: () => void
}) {
  const [val, setVal] = useState(initial)
  const ref = useRef<HTMLInputElement>(null)
  useEffect(() => {
    ref.current?.focus()
    ref.current?.select()
  }, [])
  return (
    <div className="flex items-center rounded-md bg-bg2 px-2 py-1 ring-1 ring-accent/40">
      <input
        ref={ref}
        value={val}
        onChange={(e) => setVal(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter') onCommit(val.trim())
          else if (e.key === 'Escape') onCancel()
        }}
        onBlur={() => onCommit(val.trim())}
        className="w-full bg-transparent text-[12px] text-fg outline-none"
      />
    </div>
  )
}

function DropdownMenu({
  rect,
  onClose,
  onRename,
  onDelete,
}: {
  rect: DOMRect
  onClose: () => void
  onRename: () => void
  onDelete: () => void
}) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose()
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [onClose])
  return createPortal(
    <div
      ref={ref}
      className="fixed z-[9999] min-w-[140px] overflow-hidden rounded-md border border-line2 bg-bg1 shadow-xl"
      style={{
        top: rect.bottom + 4,
        left: Math.max(8, rect.right - 140),
      }}
    >
      <button
        onClick={onRename}
        className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-[12px] text-fg2 hover:bg-bg2 hover:text-fg"
      >
        <Pencil size={12} /> Omdøb
      </button>
      <button
        onClick={onDelete}
        className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-[12px] text-danger hover:bg-danger/10"
      >
        <Trash2 size={12} /> Slet
      </button>
    </div>,
    document.body,
  )
}
