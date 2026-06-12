import { useEffect, useState } from 'react'
import { GitBranch } from 'lucide-react'
import { getGitStatus, type GitStatus, type ApiConfig } from '../../lib/api'

/** Git-status-chip i code-headeren: viser branch + ucommittede ændringer for det
 *  AKTIVE workspace (container-repo eller workstation-mappe via broen). En blid,
 *  vedvarende påmindelse om at committe — uden at fylde i composeren.
 *
 *  `refreshKey` bumpes af forælderen (fx når et run slutter) for at gen-hente. */
export function GitChip({
  config, kind, root, refreshKey = 0,
}: {
  config: ApiConfig
  kind: 'container' | 'workstation'
  root: string
  refreshKey?: number
}) {
  const [git, setGit] = useState<GitStatus | null>(null)
  useEffect(() => {
    if (!root) { setGit(null); return }
    let cancelled = false
    getGitStatus(config, kind, root)
      .then((g) => { if (!cancelled) setGit(g) })
      .catch(() => { if (!cancelled) setGit(null) })
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [kind, root, refreshKey, config.apiBaseUrl, config.authToken])

  if (!git || !git.is_git) return null
  const clean = git.dirty === 0
  return (
    <div className={`git-chip ${clean ? 'clean' : 'dirty'}`} title={clean ? 'Ingen ucommittede ændringer' : `${git.dirty} ændrede filer`}>
      <GitBranch size={12} />
      <span className="git-branch">{git.branch}</span>
      {!clean && (
        <span className="git-counts">
          <span className="git-add">+{git.added}</span>
          <span className="git-del">−{git.removed}</span>
        </span>
      )}
    </div>
  )
}
