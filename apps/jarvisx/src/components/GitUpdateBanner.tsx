import { useEffect, useState } from 'react'
import {
  GitBranch,
  Download,
  X,
  CheckCircle2,
  AlertCircle,
  Loader2,
  RotateCw,
  ChevronDown,
  ChevronUp,
  Power,
} from 'lucide-react'
import type { GitUpdateStatus } from '../types'

/**
 * Banner that surfaces the git-based update flow.
 *
 * The main process polls origin/main every 5 minutes (plus once 8s
 * after launch). When commits are waiting upstream, this banner
 * shows up with the count and a "show what's new" expander. Click
 * "Update" → main process runs git pull + npm install + npm run
 * build, streaming output back so the user sees progress, then
 * relaunches Electron at the new HEAD.
 *
 * States:
 *   idle         → hidden
 *   checking     → hidden (silent, polling is background-quiet)
 *   up-to-date   → hidden
 *   behind       → "X commits behind main" with expander + Update button
 *   updating     → progress with phase + tailed stdout
 *   updated      → "Genstarter på {sha}" briefly before relaunch
 *   error        → red banner with retry
 *
 * Per-commit-set dismissal: clicking X stashes the latest HEAD sha
 * in localStorage so we don't re-pop the banner for the same set.
 * Banner returns when origin advances past that sha.
 */
export function GitUpdateBanner() {
  const [status, setStatus] = useState<GitUpdateStatus>({ kind: 'idle' })
  const [expanded, setExpanded] = useState(false)
  const [dismissedHead, setDismissedHead] = useState<string | null>(() =>
    localStorage.getItem('jarvisx:git-dismissed-head'),
  )

  useEffect(() => {
    if (!window.jarvisx?.gitUpdateStatus) return
    window.jarvisx.gitUpdateStatus().then(setStatus).catch(() => undefined)
    const off = window.jarvisx.onGitUpdateStatus(setStatus)
    return off
  }, [])

  if (!window.jarvisx?.gitUpdateStatus) return null

  // Dismissal: only meaningful while we're in 'behind' state. We key on
  // the sha of the most recent commit upstream (commits[0].sha).
  const latestUpstreamSha =
    status.kind === 'behind' && status.commits.length > 0
      ? status.commits[0].sha
      : null
  const isDismissed =
    status.kind === 'behind' &&
    latestUpstreamSha !== null &&
    dismissedHead === latestUpstreamSha

  const dismiss = () => {
    if (latestUpstreamSha) {
      localStorage.setItem('jarvisx:git-dismissed-head', latestUpstreamSha)
      setDismissedHead(latestUpstreamSha)
    }
  }

  if (
    status.kind === 'idle' ||
    status.kind === 'checking' ||
    status.kind === 'up-to-date' ||
    isDismissed
  ) {
    return null
  }

  if (status.kind === 'behind') {
    return (
      <div className="flex flex-shrink-0 flex-col border-b border-accent/30 bg-accent/10 text-[11px] text-accent">
        <div className="flex items-center gap-3 px-4 py-1.5">
          <GitBranch size={12} className="flex-shrink-0" />
          <span className="flex-shrink-0 font-semibold">
            {status.commits.length} new commit{status.commits.length === 1 ? '' : 's'} on main
          </span>
          <button
            onClick={() => setExpanded((v) => !v)}
            className="flex flex-1 items-center gap-1 truncate text-left text-fg2 hover:text-fg"
          >
            {expanded ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
            <span className="opacity-80">
              {status.commits.length > 0 ? status.commits[0].subject : 'view'}
            </span>
          </button>
          <button
            onClick={() => window.jarvisx?.gitUpdatePullAndRebuild()}
            className="flex items-center gap-1.5 rounded bg-accent px-3 py-1 text-[11px] font-semibold text-bg0 hover:bg-accent/90"
          >
            <Download size={11} /> Pull & rebuild
          </button>
          <button
            onClick={dismiss}
            title="Skjul indtil næste commit"
            className="flex h-5 w-5 items-center justify-center rounded text-fg3 hover:bg-bg2 hover:text-fg"
          >
            <X size={11} />
          </button>
        </div>
        {expanded && (
          <div className="max-h-[260px] overflow-y-auto border-t border-accent/20 bg-bg0/40 px-4 py-2">
            <ul className="flex flex-col gap-1">
              {status.commits.map((c) => (
                <li
                  key={c.sha}
                  className="flex items-baseline gap-2 font-mono text-[11px]"
                >
                  <span className="flex-shrink-0 text-fg3">{c.short}</span>
                  <span className="flex-1 break-words text-fg2" title={c.subject}>
                    {c.subject}
                  </span>
                  <span className="flex-shrink-0 text-[9px] text-fg3">
                    {c.author}
                  </span>
                </li>
              ))}
            </ul>
            <div className="mt-2 text-[10px] text-fg3">
              Du står på <span className="font-mono">{status.head}</span> · senest
              tjekket {new Date(status.checkedAt).toLocaleTimeString()}.
            </div>
          </div>
        )}
      </div>
    )
  }

  if (status.kind === 'updating') {
    return (
      <div className="flex flex-shrink-0 flex-col border-b border-accent/30 bg-accent/10">
        <div className="flex items-center gap-3 px-4 py-1.5 text-[11px] text-accent">
          <Loader2 size={12} className="flex-shrink-0 animate-spin" />
          <span className="flex-shrink-0 font-semibold">Opdaterer · {status.phase}</span>
          <span className="text-fg3">venter ikke — du kan blive ved at chatte mens build kører</span>
        </div>
        {status.output && (
          <pre className="max-h-[160px] overflow-auto border-t border-accent/20 bg-bg0/60 px-4 py-1.5 font-mono text-[10px] text-fg2">
            {status.output}
          </pre>
        )}
      </div>
    )
  }

  if (status.kind === 'updated') {
    // Build artifacts are on disk but the renderer is still running
    // the OLD bundle. We do NOT auto-restart — Bjørn is explicit
    // that mid-conversation yanks are not OK. User clicks "Restart
    // now" when they're at a natural break.
    return (
      <div className="flex flex-shrink-0 items-center gap-3 border-b border-ok/30 bg-ok/10 px-4 py-1.5 text-[11px] text-ok">
        <CheckCircle2 size={12} />
        <span className="flex-1 font-semibold">
          Build færdig på <span className="font-mono">{status.head}</span> —
          klar til genstart når du er klar
        </span>
        <button
          onClick={() => window.jarvisx?.gitUpdateRestartNow()}
          className="flex items-center gap-1.5 rounded bg-ok px-3 py-1 text-[11px] font-semibold text-bg0 hover:bg-ok/90"
        >
          <Power size={11} /> Genstart nu
        </button>
      </div>
    )
  }

  if (status.kind === 'error') {
    return (
      <div className="flex flex-shrink-0 items-start gap-3 border-b border-danger/30 bg-danger/10 px-4 py-1.5 text-[11px] text-danger">
        <AlertCircle size={12} className="mt-0.5 flex-shrink-0" />
        <span className="flex-1 whitespace-pre-wrap font-mono">{status.error}</span>
        <button
          onClick={() => window.jarvisx?.gitUpdateCheck()}
          className="flex flex-shrink-0 items-center gap-1 rounded border border-line2 bg-bg2 px-2 py-1 text-[10px] text-fg2 hover:text-fg"
        >
          <RotateCw size={10} /> Prøv igen
        </button>
      </div>
    )
  }

  return null
}
