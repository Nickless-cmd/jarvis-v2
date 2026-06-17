import { useEffect, useState } from 'react'
import { GitBranch, Monitor, Server, Activity } from 'lucide-react'
import { getGitStatus, type GitStatus, type ApiConfig } from '../../lib/api'

/** Miljø-felt (code mode) — som Codex' "Miljø"-panel. Vises KUN under et run og
 *  logger live: ændringer (+/-), branch, workspace-type, samt Jarvis' aktuelle
 *  arbejdstrin + token-forbrug. Forsvinder igen når runnet er færdigt. */
export function EnvironmentPanel({
  config, kind, root, refreshKey = 0,
  working, workingStep, tokens,
}: {
  config?: ApiConfig
  kind: 'container' | 'workstation'
  root: string
  refreshKey?: number
  working: boolean
  workingStep?: string
  tokens?: number
}) {
  const [git, setGit] = useState<GitStatus | null>(null)
  useEffect(() => {
    if (!config || !root || !working) return
    let cancelled = false
    getGitStatus(config, kind, root)
      .then((g) => { if (!cancelled) setGit(g) })
      .catch(() => { if (!cancelled) setGit(null) })
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [kind, root, refreshKey, working, config?.apiBaseUrl, config?.authToken])

  if (!working) return null

  return (
    <aside className="env-panel" aria-label="Miljø">
      <div className="env-head">Miljø</div>
      <ul className="env-rows">
        {git?.is_git && git.dirty > 0 && (
          <li className="env-row">
            <span className="env-label">Ændringer</span>
            <span className="env-val"><span className="git-add">+{git.added}</span> <span className="git-del">−{git.removed}</span></span>
          </li>
        )}
        <li className="env-row">
          <span className="env-label">{kind === 'workstation' ? <Monitor size={13} /> : <Server size={13} />} {kind === 'workstation' ? 'Workstation' : 'Lokal'}</span>
        </li>
        {git?.is_git && (
          <li className="env-row">
            <span className="env-label"><GitBranch size={13} /> {git.branch}</span>
          </li>
        )}
      </ul>
      <div className="env-live">
        <Activity size={13} className="env-live-icon" />
        <span className="env-step">{workingStep || 'arbejder…'}</span>
        {typeof tokens === 'number' && tokens > 0 && <span className="env-tokens">{tokens} tokens</span>}
      </div>
    </aside>
  )
}
