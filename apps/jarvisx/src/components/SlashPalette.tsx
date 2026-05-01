import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import {
  Plus,
  Folder,
  Search as SearchIcon,
  Trash2,
  FileText,
  Layers,
  Mic,
  Download,
  RefreshCw,
} from 'lucide-react'

export interface SlashCommand {
  cmd: string
  label: string
  description: string
  Icon: typeof Plus
  action: () => void
}

interface Props {
  commands: SlashCommand[]
  onClose: () => void
}

/**
 * Floating command palette — opened when user types `/` at the start
 * of an empty composer. Fuzzy-search list, keyboard-driven. Each
 * command has an action callback that runs on pick.
 *
 * Design choice: NOT inside the composer DOM. Rendered as a portal
 * with fixed positioning so it can appear above the composer without
 * fighting its overflow/clip rules.
 */
export function SlashPalette({ commands, onClose }: Props) {
  const [query, setQuery] = useState('')
  const [highlight, setHighlight] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  const matches = query.trim()
    ? commands.filter(
        (c) =>
          c.cmd.toLowerCase().includes(query.toLowerCase()) ||
          c.label.toLowerCase().includes(query.toLowerCase()),
      )
    : commands

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      e.preventDefault()
      onClose()
    } else if (e.key === 'ArrowDown') {
      e.preventDefault()
      setHighlight((i) => (i + 1) % Math.max(1, matches.length))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setHighlight((i) => (i - 1 + matches.length) % Math.max(1, matches.length))
    } else if (e.key === 'Enter' || e.key === 'Tab') {
      e.preventDefault()
      if (matches[highlight]) {
        matches[highlight].action()
        onClose()
      }
    }
  }

  return createPortal(
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,.55)',
        zIndex: 10000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="flex max-h-[60vh] w-[520px] max-w-[92vw] flex-col rounded-lg border border-line2 bg-bg1 shadow-2xl"
      >
        <div className="flex flex-shrink-0 items-center gap-2 border-b border-line px-4 py-3">
          <span className="font-mono text-sm text-accent">/</span>
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value)
              setHighlight(0)
            }}
            onKeyDown={handleKey}
            placeholder="Type a command…"
            className="flex-1 bg-transparent text-sm text-fg placeholder:text-fg3 focus:outline-none"
          />
          <span className="font-mono text-[10px] text-fg3">
            {matches.length}
          </span>
        </div>
        <div className="min-h-[60px] flex-1 overflow-y-auto py-1">
          {matches.length === 0 && (
            <div className="px-4 py-3 text-[11px] text-fg3">No matching commands.</div>
          )}
          {matches.map((c, i) => {
            const isActive = i === highlight
            return (
              <button
                key={c.cmd}
                onMouseEnter={() => setHighlight(i)}
                onClick={() => {
                  c.action()
                  onClose()
                }}
                className={[
                  'flex w-full items-center gap-3 px-4 py-2 text-left',
                  isActive ? 'bg-accent/10' : 'hover:bg-bg2/50',
                ].join(' ')}
              >
                <c.Icon
                  size={12}
                  className={isActive ? 'text-accent' : 'text-fg3'}
                />
                <div className="flex-1">
                  <div
                    className={`font-mono text-xs ${
                      isActive ? 'text-accent' : 'text-fg2'
                    }`}
                  >
                    /{c.cmd}
                  </div>
                  <div className="text-[10px] text-fg3">{c.description}</div>
                </div>
                <span className="font-mono text-[9px] text-fg3 opacity-60">
                  {c.label}
                </span>
              </button>
            )
          })}
        </div>
        <div className="flex flex-shrink-0 items-center justify-between border-t border-line/60 bg-bg1/40 px-4 py-1.5 font-mono text-[10px] text-fg3">
          <span>↑↓ navigate · Enter run · Esc close</span>
        </div>
      </div>
    </div>,
    document.body,
  )
}

// Standard icon set used to build the default command list — exported
// so consumers building their own palette don't need to re-import.
export const CommandIcons = {
  Plus,
  Folder,
  SearchIcon,
  Trash2,
  FileText,
  Layers,
  Mic,
  Download,
  RefreshCw,
}
