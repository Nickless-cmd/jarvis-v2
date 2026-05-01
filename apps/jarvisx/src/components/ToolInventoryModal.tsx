import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { Wrench, Search, X } from 'lucide-react'

interface Tool {
  name: string
  description: string
  required: string[]
}

interface Props {
  apiBaseUrl: string
  onClose: () => void
}

/**
 * Modal listing every registered tool with its description + required
 * params. Searchable. Shows the full power Jarvis has to draw on —
 * answers "what can he actually do?" in one glance.
 */
export function ToolInventoryModal({ apiBaseUrl, onClose }: Props) {
  const [tools, setTools] = useState<Tool[]>([])
  const [filter, setFilter] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    inputRef.current?.focus()
    fetch(`${apiBaseUrl.replace(/\/$/, '')}/api/tools/inventory`)
      .then((r) => r.json())
      .then((j) => setTools(j.tools || []))
      .catch(() => undefined)
  }, [apiBaseUrl])

  const matches = filter.trim()
    ? tools.filter(
        (t) =>
          t.name.toLowerCase().includes(filter.toLowerCase()) ||
          t.description.toLowerCase().includes(filter.toLowerCase()),
      )
    : tools

  return createPortal(
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,.65)',
        zIndex: 10000,
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'center',
        paddingTop: '8vh',
      }}
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="flex max-h-[80vh] w-[760px] max-w-[95vw] flex-col rounded-lg border border-line2 bg-bg1 shadow-2xl"
      >
        <header className="flex flex-shrink-0 items-center gap-2 border-b border-line px-4 py-3">
          <Wrench size={14} className="text-accent" />
          <h2 className="text-sm font-semibold">Tool inventory</h2>
          <span className="font-mono text-[10px] text-fg3">{tools.length} tools</span>
          <button
            onClick={onClose}
            className="ml-auto flex h-6 w-6 items-center justify-center rounded text-fg3 hover:bg-bg2 hover:text-fg"
          >
            <X size={14} />
          </button>
        </header>

        <div className="flex flex-shrink-0 items-center gap-2 border-b border-line/60 bg-bg1/40 px-4 py-2">
          <Search size={11} className="text-fg3" />
          <input
            ref={inputRef}
            type="text"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="Filter…"
            className="flex-1 bg-transparent text-xs text-fg placeholder:text-fg3 focus:outline-none"
          />
          {filter && (
            <button
              onClick={() => setFilter('')}
              className="font-mono text-[10px] text-fg3 hover:text-fg"
            >
              clear
            </button>
          )}
          <span className="font-mono text-[10px] text-fg3">
            {matches.length} / {tools.length}
          </span>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto">
          {tools.length === 0 && (
            <div className="px-4 py-3 text-[11px] text-fg3">loading…</div>
          )}
          {matches.map((t) => (
            <div
              key={t.name}
              className="grid grid-cols-[180px,1fr] gap-3 border-b border-line/30 px-4 py-2 hover:bg-bg2/30"
            >
              <div className="flex items-start gap-1.5">
                <Wrench size={10} className="mt-1 flex-shrink-0 text-accent" />
                <span className="font-mono text-[11px] text-fg break-all">
                  {t.name}
                </span>
              </div>
              <div>
                <p className="text-[11px] leading-relaxed text-fg2">
                  {t.description}
                </p>
                {t.required.length > 0 && (
                  <div className="mt-1 flex flex-wrap gap-1">
                    {t.required.map((r) => (
                      <span
                        key={r}
                        className="rounded bg-bg2 px-1.5 py-0.5 font-mono text-[9px] text-fg3"
                      >
                        {r}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
          {matches.length === 0 && tools.length > 0 && (
            <div className="px-4 py-3 text-[11px] text-fg3">
              No match for "{filter}"
            </div>
          )}
        </div>
      </div>
    </div>,
    document.body,
  )
}
