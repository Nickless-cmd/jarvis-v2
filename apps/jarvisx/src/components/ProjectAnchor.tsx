import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { Folder, FolderOpen, Check, X } from 'lucide-react'

interface Props {
  projectRoot: string
  recentProjects: string[]
  onChange: (patch: { projectRoot?: string; recentProjects?: string[] }) => void
}

/**
 * Pill in the chat header showing the currently anchored project.
 * Click to open native directory picker. Drop-down shows recent
 * projects for quick switching. Once anchored, every JarvisX request
 * carries X-JarvisX-Project so Jarvis knows where Bjørn is rooted.
 */
export function ProjectAnchor({ projectRoot, recentProjects, onChange }: Props) {
  const [open, setOpen] = useState(false)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const [pos, setPos] = useState<{ top: number; left: number } | null>(null)

  // Position the portaled dropdown under the trigger
  useLayoutEffect(() => {
    if (!open || !triggerRef.current) return
    const rect = triggerRef.current.getBoundingClientRect()
    setPos({
      top: rect.bottom + 4,
      // anchor right-edge of dropdown to right-edge of trigger so it
      // never overflows offscreen on the right side
      left: Math.max(8, rect.right - 320),
    })
  }, [open])

  // Close on outside click — both trigger and dropdown count as "inside"
  useEffect(() => {
    if (!open) return
    const onClick = (e: MouseEvent) => {
      const t = e.target as Node
      if (
        triggerRef.current?.contains(t) ||
        dropdownRef.current?.contains(t)
      )
        return
      setOpen(false)
    }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [open])

  const [error, setError] = useState<string | null>(null)
  const pick = async () => {
    setError(null)
    // Close dropdown FIRST so it doesn't sit on top of the OS dialog
    // and so React state isn't fighting the IPC roundtrip.
    setOpen(false)
    if (!window.jarvisx?.pickProjectRoot) {
      setError('window.jarvisx not available — preload failed to load')
      console.error('[ProjectAnchor] window.jarvisx missing', window.jarvisx)
      return
    }
    try {
      const result = await window.jarvisx.pickProjectRoot()
      console.log('[ProjectAnchor] pickProjectRoot result:', result)
      if (result) {
        onChange({
          projectRoot: result.projectRoot,
          recentProjects: result.recentProjects,
        })
      }
      // result === null means user cancelled — that's fine, no error
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      console.error('[ProjectAnchor] pickProjectRoot threw:', e)
      setError(msg)
    }
  }

  const choose = (path: string) => {
    setOpen(false)
    const recents = [path, ...recentProjects.filter((p) => p !== path)].slice(0, 8)
    onChange({ projectRoot: path, recentProjects: recents })
  }

  const clear = () => {
    setOpen(false)
    onChange({ projectRoot: '' })
  }

  const display = projectRoot
    ? projectRoot.replace(/^\/home\/[^/]+/, '~').replace(/^([^/]+\/[^/]+\/[^/]+\/)(.+)/, (_, head, tail) => {
        return tail.length > 30 ? head + '…/' + tail.split('/').slice(-1)[0] : head + tail
      })
    : null

  const dropdown = open && pos ? (
    <div
      ref={dropdownRef}
      style={{ position: 'fixed', top: pos.top, left: pos.left, zIndex: 9999 }}
      className="w-[320px] rounded-md border border-line2 bg-bg1 shadow-2xl"
    >
          <div className="border-b border-line/60 px-3 py-2">
            <div className="text-[9px] font-semibold uppercase tracking-wider text-fg3">
              Anchor Jarvis to a project
            </div>
            <p className="mt-1 text-[10px] leading-relaxed text-fg3">
              Sender stien som <code className="font-mono text-fg2">X-JarvisX-Project</code>{' '}
              header — Jarvis ser den i sin awareness og bruger den som default
              cwd for bash + relative file paths.
            </p>
          </div>
          <button
            onClick={pick}
            className="flex w-full items-center gap-2 border-b border-line/60 px-3 py-2 text-left text-xs text-fg2 hover:bg-bg2 hover:text-accent"
          >
            <FolderOpen size={12} />
            Browse for folder…
          </button>
          {error && (
            <div className="border-b border-danger/30 bg-danger/10 px-3 py-2 text-[10px] text-danger">
              {error}
            </div>
          )}
          {recentProjects.length > 0 && (
            <div>
              <div className="px-3 py-1.5 text-[9px] font-semibold uppercase tracking-wider text-fg3">
                Recent
              </div>
              {recentProjects.map((p) => {
                const isActive = p === projectRoot
                return (
                  <button
                    key={p}
                    onClick={() => choose(p)}
                    className={[
                      'flex w-full items-center gap-2 px-3 py-1.5 text-left text-[11px] transition-colors',
                      isActive
                        ? 'bg-bg2 text-accent'
                        : 'text-fg2 hover:bg-bg2/60 hover:text-fg',
                    ].join(' ')}
                  >
                    {isActive ? (
                      <Check size={11} className="text-accent" />
                    ) : (
                      <Folder size={11} className="text-fg3" />
                    )}
                    <span className="truncate font-mono">
                      {p.replace(/^\/home\/[^/]+/, '~')}
                    </span>
                  </button>
                )
              })}
            </div>
          )}
          {projectRoot && (
            <button
              onClick={clear}
              className="flex w-full items-center gap-2 border-t border-line/60 px-3 py-2 text-left text-[11px] text-fg3 hover:bg-bg2 hover:text-danger"
            >
              <X size={11} />
              Unanchor (no project)
            </button>
          )}
    </div>
  ) : null

  return (
    <>
      <button
        ref={triggerRef}
        onClick={() => setOpen((o) => !o)}
        title={projectRoot || 'No project anchored'}
        className={[
          'flex items-center gap-1.5 rounded-md border px-2 py-1 text-[11px] transition-colors',
          projectRoot
            ? 'border-accent/30 bg-accent/10 text-accent hover:border-accent/50'
            : 'border-line2 bg-bg2 text-fg3 hover:text-fg2',
        ].join(' ')}
      >
        {projectRoot ? <FolderOpen size={11} /> : <Folder size={11} />}
        <span className="font-mono">{display || 'no project'}</span>
      </button>
      {dropdown && createPortal(dropdown, document.body)}
    </>
  )
}
