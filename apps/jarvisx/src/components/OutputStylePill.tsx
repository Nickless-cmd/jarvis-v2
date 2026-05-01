import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { Sliders } from 'lucide-react'

const STYLES: Array<{ id: string; label: string; hint: string }> = [
  { id: 'concise', label: 'Concise', hint: 'Korte, tætte svar' },
  { id: 'balanced', label: 'Balanced', hint: 'Default — middle of the road' },
  { id: 'detailed', label: 'Detailed', hint: 'Forklarende, walk-through' },
  { id: 'technical', label: 'Technical', hint: 'Mere kode, mindre prosa' },
]

interface Props {
  apiBaseUrl: string
}

/**
 * Compact selector for output-style preference. Persisted via
 * /api/preferences. The backend reads the file in prompt_contract and
 * surfaces it as an awareness section so Jarvis adjusts his
 * verbosity/structure on every turn.
 */
export function OutputStylePill({ apiBaseUrl }: Props) {
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState<string>('balanced')
  const triggerRef = useRef<HTMLButtonElement>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const [pos, setPos] = useState<{ top: number; right: number } | null>(null)

  useEffect(() => {
    fetch(`${apiBaseUrl.replace(/\/$/, '')}/api/preferences`)
      .then((r) => r.json())
      .then((p) => setActive(p.output_style || 'balanced'))
      .catch(() => undefined)
  }, [apiBaseUrl])

  useEffect(() => {
    if (!open || !triggerRef.current) return
    const rect = triggerRef.current.getBoundingClientRect()
    setPos({ top: rect.bottom + 4, right: window.innerWidth - rect.right })
  }, [open])

  useEffect(() => {
    if (!open) return
    const onClick = (e: MouseEvent) => {
      const t = e.target as Node
      if (triggerRef.current?.contains(t) || dropdownRef.current?.contains(t)) return
      setOpen(false)
    }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [open])

  const pick = async (id: string) => {
    setActive(id)
    setOpen(false)
    try {
      await fetch(`${apiBaseUrl.replace(/\/$/, '')}/api/preferences`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ output_style: id }),
      })
    } catch { /* ignore */ }
  }

  const cur = STYLES.find((s) => s.id === active) || STYLES[1]

  return (
    <>
      <button
        ref={triggerRef}
        onClick={() => setOpen((o) => !o)}
        title={`Output style: ${cur.label} — ${cur.hint}`}
        className="flex items-center gap-1.5 rounded-md border border-line2 bg-bg2 px-2 py-1 font-mono text-[10px] text-fg2 hover:border-accent/40 hover:text-accent"
      >
        <Sliders size={10} />
        <span>{cur.label}</span>
      </button>
      {open && pos && createPortal(
        <div
          ref={dropdownRef}
          style={{ position: 'fixed', top: pos.top, right: pos.right, zIndex: 9999 }}
          className="w-[220px] rounded-md border border-line2 bg-bg1 shadow-xl"
        >
          <div className="border-b border-line/60 px-3 py-1.5 text-[9px] font-semibold uppercase tracking-wider text-fg3">
            Output style
          </div>
          {STYLES.map((s) => (
            <button
              key={s.id}
              onClick={() => pick(s.id)}
              className={[
                'flex w-full flex-col items-start gap-0 px-3 py-1.5 text-left transition-colors',
                s.id === active ? 'bg-accent/10' : 'hover:bg-bg2/50',
              ].join(' ')}
            >
              <span
                className={`text-[11px] font-medium ${
                  s.id === active ? 'text-accent' : 'text-fg2'
                }`}
              >
                {s.label}
              </span>
              <span className="text-[10px] text-fg3">{s.hint}</span>
            </button>
          ))}
        </div>,
        document.body,
      )}
    </>
  )
}
