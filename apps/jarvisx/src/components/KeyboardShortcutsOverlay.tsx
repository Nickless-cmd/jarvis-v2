import { useEffect } from 'react'
import { Keyboard, X } from 'lucide-react'
import { SHORTCUTS, type Shortcut } from '../lib/shortcuts'

interface Props {
  open: boolean
  onClose: () => void
}

const SCOPE_LABELS: Record<Shortcut['scope'], string> = {
  global: 'Globalt',
  chat: 'Chat',
  composer: 'Composer',
}

const SCOPE_ORDER: Shortcut['scope'][] = ['global', 'chat', 'composer']

/**
 * Modal cheat sheet for every keyboard shortcut JarvisX exposes.
 * Triggered by F1 or `?`. Esc closes.
 *
 * Why a modal vs a settings page: discoverability. When the user
 * presses a key combo and nothing happens, they need a fast way to
 * check what they meant — a modal hovering over whatever they were
 * doing is the right affordance. A settings page is for tweaks, not
 * "what does X do?".
 */
export function KeyboardShortcutsOverlay({ open, onClose }: Props) {
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        onClose()
      }
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  // Group by scope, preserving SCOPE_ORDER
  const grouped = SCOPE_ORDER.map((scope) => ({
    scope,
    items: SHORTCUTS.filter((s) => s.scope === scope),
  })).filter((g) => g.items.length > 0)

  return (
    <div
      onClick={onClose}
      className="fixed inset-0 z-[9999] flex items-center justify-center bg-bg0/80 backdrop-blur-sm"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="flex max-h-[80vh] w-[640px] max-w-[90vw] flex-col overflow-hidden rounded-xl border border-line2 bg-bg1 shadow-2xl"
      >
        <header className="flex flex-shrink-0 items-center justify-between border-b border-line px-5 py-3">
          <div className="flex items-center gap-2">
            <Keyboard size={14} className="text-accent" />
            <h2 className="text-sm font-semibold">Keyboard genveje</h2>
            <span className="font-mono text-[10px] text-fg3">F1 toggler · Esc lukker</span>
          </div>
          <button
            onClick={onClose}
            className="flex h-7 w-7 items-center justify-center rounded text-fg3 hover:bg-bg2 hover:text-fg"
          >
            <X size={14} />
          </button>
        </header>

        <div className="flex-1 overflow-y-auto px-5 py-4">
          {grouped.map(({ scope, items }) => (
            <section key={scope} className="mb-4 last:mb-0">
              <h3 className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-fg3">
                {SCOPE_LABELS[scope]}
              </h3>
              <div className="grid gap-1.5">
                {items.map((s) => (
                  <div
                    key={s.keys.join('+')}
                    className="flex items-center justify-between gap-3 rounded-md px-3 py-1.5 text-[12px] hover:bg-bg2/40"
                  >
                    <span className="text-fg2">{s.label}</span>
                    <span className="flex flex-shrink-0 items-center gap-1">
                      {s.keys.map((k, i) => (
                        <span key={i}>
                          {i > 0 && <span className="mx-0.5 text-fg3">+</span>}
                          <kbd className="rounded border border-line2 bg-bg2 px-1.5 py-0.5 font-mono text-[10px] text-fg shadow-sm">
                            {k}
                          </kbd>
                        </span>
                      ))}
                    </span>
                  </div>
                ))}
              </div>
            </section>
          ))}
        </div>

        <footer className="flex-shrink-0 border-t border-line/60 bg-bg1/50 px-5 py-2 text-[10px] text-fg3">
          Ctrl betyder Cmd på macOS. Layout-uafhængige tal (Ctrl+1..8) bruger fysisk
          tasteposition så de virker på dansk, tysk og andre layouts.
        </footer>
      </div>
    </div>
  )
}
