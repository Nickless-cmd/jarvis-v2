import { useState } from 'react'
import { Edit2, Trash2, Check, X } from 'lucide-react'

interface Props {
  title: string
  onRename: (newTitle: string) => void
  onDelete: () => void
}

/**
 * Slim chat header with editable title + delete. No refresh / no model
 * picker / no thinking-mode badge — that's all in the composer
 * footer or status bar. Claude-Code-style: the title is one click
 * away from being editable.
 */
export function ChatHeader({ title, onRename, onDelete }: Props) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(title)

  const startEdit = () => {
    setDraft(title)
    setEditing(true)
  }
  const commit = () => {
    const t = draft.trim()
    if (t && t !== title) onRename(t)
    setEditing(false)
  }
  const cancel = () => {
    setEditing(false)
    setDraft(title)
  }

  return (
    <div className="flex flex-shrink-0 items-center gap-2 border-b border-line/60 bg-bg1/50 px-4 py-2">
      {editing ? (
        <>
          <input
            autoFocus
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') commit()
              else if (e.key === 'Escape') cancel()
            }}
            className="flex-1 rounded bg-bg2 px-2 py-1 text-sm text-fg focus:outline-none focus:ring-1 focus:ring-accent/40"
          />
          <button
            onClick={commit}
            className="flex h-6 w-6 items-center justify-center rounded text-ok hover:bg-bg2"
          >
            <Check size={12} />
          </button>
          <button
            onClick={cancel}
            className="flex h-6 w-6 items-center justify-center rounded text-fg3 hover:bg-bg2 hover:text-fg"
          >
            <X size={12} />
          </button>
        </>
      ) : (
        <>
          <h2 className="flex-1 truncate text-sm font-medium text-fg">
            {title || 'Ny samtale'}
          </h2>
          <button
            onClick={startEdit}
            title="Omdøb"
            className="flex h-6 w-6 items-center justify-center rounded text-fg3 hover:bg-bg2 hover:text-fg"
          >
            <Edit2 size={11} />
          </button>
          <button
            onClick={() => {
              if (confirm(`Slet "${title || 'denne samtale'}"?`)) onDelete()
            }}
            title="Slet samtale"
            className="flex h-6 w-6 items-center justify-center rounded text-fg3 hover:bg-bg2 hover:text-danger"
          >
            <Trash2 size={11} />
          </button>
        </>
      )}
    </div>
  )
}
