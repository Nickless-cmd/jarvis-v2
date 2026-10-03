import { useEffect, useState } from 'react'
import { X, GitBranch } from 'lucide-react'
import { getGitStatus, type ApiConfig, type GitStatus } from '../../lib/api'

/**
 * «Klar til PR» ved samtalen — Jarvis' `desk_show_pane('pr')`.
 *
 * 3/10-2026: desk afviste `pr` med «Desk har intet pull request-panel».
 *
 * Og det er sandt i ordets strenge forstand: der findes INGEN PR-LISTE i
 * desk — kun `POST /chat/git/create-pr`, altså handlingen at oprette én.
 * Et panel der påstod at vise «åbne pull requests» ville derfor opfinde data.
 *
 * Det her viser i stedet den git-tilstand der FAKTISK findes, og som er det
 * man kigger på inden man opretter en PR: hvilken branch man står på, hvor
 * langt den er fra sin upstream, og hvad der ligger i arbejdstræet.
 */
export function PrPanel({ config, onClose }: { config: ApiConfig; onClose: () => void }) {
  const [git, setGit] = useState<GitStatus | null>(null)
  const [fejl, setFejl] = useState('')
  useEffect(() => {
    let levende = true
    setFejl('')
    // Samme workspace-valg som code-headeren: `jarvis-desk:code-ws`.
    let kind: 'container' | 'workstation' = 'container'
    let root = ''
    try {
      const ws = JSON.parse(localStorage.getItem('jarvis-desk:code-ws') || '{}') as {
        kind?: string; root?: string; wsPath?: string
      }
      if (ws.kind === 'workstation') kind = 'workstation'
      root = ws.wsPath || ws.root || ''
    } catch { /* standard: serverens repo */ }
    getGitStatus(config, kind, root)
      .then((g) => { if (levende) setGit(g) })
      .catch(() => { if (levende) setFejl('Kunne ikke læse git-tilstanden') })
    return () => { levende = false }
  }, [config])
  const rent = git?.dirty === 0
  return (
    <div className="artifact-panel">
      <div className="artifact-head">
        <GitBranch size={14} /> <span className="artifact-title">Klar til PR</span>
        <button type="button" className="artifact-close" aria-label="Luk panel" onClick={onClose}>
          <X size={15} />
        </button>
      </div>
      <div className="artifact-body">
        {fejl && <div className="artifact-error">{fejl}</div>}
        {!fejl && !git && <div className="artifact-loading">Henter…</div>}
        {git && !git.is_git && (
          <div className="artifact-empty">
            {git.link === 'nede'
              ? 'Broen er nede — jeg kan ikke se arbejdstræet.'
              : 'Workspacet er ikke et git-repo.'}
          </div>
        )}
        {git?.is_git && (
          <div className="pr-status">
            <div className="pr-raekke">
              <span className="pr-noegle">Branch</span>
              <span className="pr-vaerdi">{git.branch || '—'}</span>
            </div>
            <div className="pr-raekke">
              <span className="pr-noegle">Arbejdstræ</span>
              <span className="pr-vaerdi">
                {rent ? 'rent' : `${git.dirty} ændrede filer`}
              </span>
            </div>
            {(git.added > 0 || git.removed > 0) && (
              <div className="pr-raekke">
                <span className="pr-noegle">Diff</span>
                <span className="pr-vaerdi">
                  {git.added > 0 && <span className="git-add">+{git.added}</span>}
                  {git.added > 0 && git.removed > 0 ? ' ' : null}
                  {git.removed > 0 && <span className="git-del">−{git.removed}</span>}
                </span>
              </div>
            )}
            <div className="pr-hint">
              {rent
                ? 'Intet at committe — træet er rent.'
                : 'Der ligger ændringer klar. Commit dem, og opret PR fra miljø-feltet.'}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
