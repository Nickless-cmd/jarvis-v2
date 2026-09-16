import { useEffect, useRef, useState } from 'react'
import { GitBranch, Monitor, Server, Globe, Bot, Settings, Activity, GitCompare, GitCommitHorizontal, Github } from 'lucide-react'
import { RunHealth } from './RunHealth'
import { getGitStatus, commitAllChanges, createPullRequest, type GitStatus, type ApiConfig } from '../../lib/api'
import { lookupTool } from '../../lib/toolRegistry'
import type { AgentReference, EnvironmentEvidence, SourceEvidence, ToolEvidence } from '../../lib/environmentEvidence'
import { agentSkalStaaFremme } from '../../lib/agentSynlighed'
const SYNLIGE_LINJER = 4
const AGENT_COLORS = ['#e0843a', '#3ab85f', '#9b6bff', '#e0556b', '#3a9be0']

/** Stabil plads i farvepaletten ud fra en streng — samme agent, samme farve. */
function stabiltIndeks(noegle: string): number {
  let sum = 0
  for (let i = 0; i < noegle.length; i++) sum = (sum * 31 + noegle.charCodeAt(i)) >>> 0
  return sum
}

/** Pænt tool-label som i chatview: label + opsummering (kommando/sti). For
 *  operator_bash bliver det fx "Terminal: git status" — IKKE bare "operator_bash". */
function formatTool(t: ToolEvidence): string {
  const meta = lookupTool(t.name)
  const summary = meta.summarize(t.input || {})
  const short = summary.length > 38 ? summary.slice(0, 37) + '…' : summary
  return short ? `${meta.label}: ${short}` : meta.label
}

/** Miljø-felt (code mode): workspace-status og struktureret session-evidence.
 *  Kilder, agenter og tool-kald åbner den fælles inspector; tokens og antal kald
 *  er fortsat session-totaler. */
export function EnvironmentPanel({
  config, kind, root, refreshKey = 0,
  working, workingStep, totalTokens = 0, totalToolCalls = 0, evidence, sessionId, hasHistory = false,
  isOwner = false, onChanged,
  onOpenAgent, onOpenSource, onOpenTool,
  gitMissing = false, installingTool = '', onInstallTool, komprimerVed = 0, kontekstTokens,
}: {
  config?: ApiConfig
  kind: 'container' | 'workstation'
  root: string
  refreshKey?: number
  working: boolean
  workingStep?: string
  totalTokens?: number
  totalToolCalls?: number
  evidence?: EnvironmentEvidence
  sessionId?: string | null
  hasHistory?: boolean
  isOwner?: boolean
  onChanged?: () => void
  onOpenAgent?: (agent: AgentReference) => void
  onOpenSource?: (source: SourceEvidence) => void
  onOpenTool?: (tool: ToolEvidence) => void
  gitMissing?: boolean
  komprimerVed?: number
  /** Kontekst-fyldet som ringen i skrivefeltet maaler det. `totalTokens` er noget
   *  ANDET — sessionens kumulative forbrug — og duer ikke som kontekst-tal:
   *  den falder aldrig naar compaction fyrer. */
  kontekstTokens?: number
  installingTool?: string
  onInstallTool?: (tool: string) => void
}) {
  const [visAlleKilder, setVisAlleKilder] = useState(false)
  const [visAlleTools, setVisAlleTools] = useState(false)
  const [git, setGit] = useState<GitStatus | null>(null)
  const [collapsed, setCollapsed] = useState(false)
  const [busy, setBusy] = useState<'' | 'commit' | 'pr'>('')
  const [note, setNote] = useState<{ text: string; url?: string; err?: boolean } | null>(null)

  // Samlet funktion: git-handlinger tilgængelige når der BARE er et git-repo (git.is_git afgør det —
  // ikke en root==='repo'-begrænsning). Server kræver owner; workstation altid. Så server- og
  // computer-mode har samme funktion.
  const canGit = !!git?.is_git && (kind === 'workstation' || isOwner)
  const target = { kind, root }

  const doCommit = async () => {
    if (!config || busy) return
    setBusy('commit'); setNote(null)
    try {
      const r = await commitAllChanges(config, target)
      setNote(r.status === 'ok' ? { text: `Committet ${r.sha}` } : { text: 'Ingen ændringer' })
      onChanged?.()
    } catch (e) { setNote({ text: (e as Error).message || 'Commit fejlede', err: true }) }
    finally { setBusy('') }
  }
  const doPr = async () => {
    if (!config || busy) return
    setBusy('pr'); setNote(null)
    try {
      const r = await createPullRequest(config, target)
      setNote({ text: r.url ? 'Pull request oprettet' : `PR (${r.status})`, url: r.url })
      if (r.url) try { window.open(r.url, '_blank') } catch { /* ignore */ }
      onChanged?.()
    } catch (e) { setNote({ text: (e as Error).message || 'PR fejlede', err: true }) }
    finally { setBusy('') }
  }

  const [everRan, setEverRan] = useState(hasHistory)
  const sessionRef = useRef<string | null | undefined>(sessionId)
  useEffect(() => {
    if (sessionRef.current !== sessionId) { sessionRef.current = sessionId; setEverRan(hasHistory) }
  }, [sessionId, hasHistory])
  useEffect(() => { if (working || hasHistory) setEverRan(true) }, [working, hasHistory])

  useEffect(() => {
    if (!config || !root || !everRan) return
    let cancelled = false
    getGitStatus(config, kind, root)
      .then((g) => { if (!cancelled) setGit(g) })
      .catch(() => { if (!cancelled) setGit(null) })
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [kind, root, refreshKey, everRan, working, config?.apiBaseUrl, config?.authToken])

  if (!everRan) return null

  // Underagenter er ikke en historik, men en liste over det der kraever
  // opmaerksomhed: noget der koerer, og noget der gik galt. En agent der
  // gjorde sit arbejde faerdigt forsvinder. (Bjoern 16/9-2026)
  const agents = (evidence?.agents ?? []).filter((a) => agentSkalStaaFremme(a.status))
  const alleSources = evidence?.sources ?? []
  const alleTools = evidence?.tools ?? []
  // Fire linjer, resten bag «Vis alle». Tallet staar PAA knappen, saa halen
  // aldrig er skjult uden at nogen kan se at den findes.
  const sources = visAlleKilder ? alleSources : alleSources.slice(-SYNLIGE_LINJER)
  const recentTools = visAlleTools ? alleTools : alleTools.slice(-SYNLIGE_LINJER)
  const flereKilder = alleSources.length > sources.length
  const flereTools = alleTools.length > recentTools.length

  return (
    <aside className="env-panel" aria-label="Miljø">
      <div className="env-head">
        <span>Miljø</span>
        <button type="button" className="env-gear" onClick={() => setCollapsed((c) => !c)}
          aria-label="Skjul/vis detaljer" title="Skjul/vis detaljer">
          <Settings size={14} />
        </button>
      </div>

      {!collapsed && (
        <>
          <ul className="env-rows">
            <li className="env-row env-changes">
              <span className="env-label"><GitCompare size={13} /> Ændringer</span>
              <span className="env-val">
                {/* Fire tilstande, ikke tre. Backenden svarer is_git=false BAADE
                    naar mappen ikke er et repo OG naar broen ikke svarer — de
                    skelnes paa `link`. «Ikke et git-repo» om et repo der findes
                    er en paastand vi ikke har belaeg for.
                    Og +0 −0: `dirty` taelles af `git status --porcelain` (med
                    utrackede), mens added/removed kommer fra `git diff --numstat
                    HEAD` (kun trackede). Fem helt nye filer giver derfor dirty=5
                    og 0/0 — et tal der ikke findes. */}
                {git?.link && git.link !== 'ok'
                  ? <span className="env-muted">{git.link === 'genforbinder' ? 'Genforbinder…' : 'Broen er nede'}</span>
                  : git?.is_git
                    ? git.dirty > 0
                      ? (git.added > 0 || git.removed > 0
                        ? <><span className="git-add">+{git.added}</span> <span className="git-del">−{git.removed}</span></>
                        : <span className="env-muted">{git.dirty} {git.dirty === 1 ? 'ny fil' : 'nye filer'}</span>)
                      : <span className="env-muted">Ingen ændringer</span>
                    : <span className="env-muted">{git ? 'Ikke et git-repo' : 'Henter…'}</span>}
              </span>
            </li>
            {gitMissing && kind === 'workstation' && (
              <li className="env-row env-action">
                <button type="button" className="env-actbtn" disabled={installingTool === 'git'}
                  onClick={() => onInstallTool?.('git')}>
                  <GitCompare size={13} /> {installingTool === 'git' ? 'Installerer git…' : 'git mangler — installér'}
                </button>
              </li>
            )}
            <li className="env-row">
              <span className="env-label">{kind === 'workstation' ? <Monitor size={13} /> : <Server size={13} />} {kind === 'workstation' ? 'Workstation' : 'Server'}</span>
            </li>
            {git?.is_git && (
              <li className="env-row">
                <span className="env-label"><GitBranch size={13} /> {git.branch}</span>
              </li>
            )}
            {canGit && git?.is_git && (
              <li className="env-row env-action">
                <button type="button" className="env-actbtn" onClick={doCommit} disabled={!!busy}>
                  <GitCommitHorizontal size={13} /> {busy === 'commit' ? 'Committer…' : 'Indsæt'}
                </button>
              </li>
            )}
            {canGit && git?.is_git && (
              <li className="env-row env-action">
                <button type="button" className="env-actbtn" onClick={doPr} disabled={!!busy}>
                  <Github size={13} /> {busy === 'pr' ? 'Opretter…' : 'Opret pull request'}
                </button>
              </li>
            )}
          </ul>

          {/* Maskin- og kontekst-tryk. Bjørn: miljø-feltet er stedet hvor
              tilstand hører til, ikke endnu et dashboard. */}
          <RunHealth config={config} tokens={kontekstTokens ?? totalTokens} komprimerVed={komprimerVed} />

          {note && (
            <div className={`env-note ${note.err ? 'is-err' : ''}`}>
              {note.url
                ? <a href={note.url} target="_blank" rel="noreferrer">{note.text} →</a>
                : note.text}
            </div>
          )}

          {agents.length > 0 && (
            <>
              <div className="env-divider" />
              <div className="env-section-head">Underagenter</div>
              <ul className="env-rows">
                {agents.map((agent) => {
                  // Farven haenger paa dispatch-id'et, ikke paa pladsen i listen:
                  // med indeks skiftede en agents farve hver gang listen voksede.
                  const farve = AGENT_COLORS[stabiltIndeks(agent.dispatchToolUseId) % AGENT_COLORS.length]
                  const koerer = ['active', 'queued', 'starting', 'waiting', 'running'].includes(agent.status || '')
                  const label = agent.role || 'Agent'
                  // Uden agent-id findes der ingen detalje at hente (hegnet,
                  // klippet eller endnu ikke ankommet resultat). Saa aabner
                  // raekken selve kaldet — det er det vi FAKTISK har.
                  const dispatchTool = alleTools.find((t) => t.id === agent.dispatchToolUseId)
                  const aabn = agent.agentId
                    ? () => onOpenAgent?.(agent)
                    : dispatchTool ? () => onOpenTool?.(dispatchTool) : undefined
                  return (
                    <li className={`env-row${koerer ? ' agent-koerer' : ''}`}
                        key={`${agent.dispatchToolUseId}:${agent.agentId}`}>
                      <button type="button" className="env-row-button" disabled={!aabn} onClick={aabn}>
                        <Bot size={13} style={{ color: farve }} />
                        <span style={{ color: farve }}>{label}</span>
                        {agent.goal && <span className="env-muted agent-opgave" title={agent.goal}>{agent.goal}</span>}
                        <span className="env-val agent-status">{koerer ? 'kører' : agent.status || 'detaljer'}</span>
                      </button>
                    </li>
                  )
                })}
              </ul>
            </>
          )}

          {sources.length > 0 && (
            <>
              <div className="env-divider" />
              <div className="env-section-head">Kilder</div>
              <ul className={`env-rows${flereKilder ? ' er-klippet' : ''}`}>
                {sources.map((source) => (
                  <li className="env-row" key={source.url}>
                    <button type="button" className="env-row-button" onClick={() => onOpenSource?.(source)} title={source.url}>
                      <Globe size={13} /><span>{source.domaene}</span>
                    </button>
                  </li>
                ))}
              </ul>
              {(flereKilder || visAlleKilder) && (
                <button type="button" className="env-vis-alle" onClick={() => setVisAlleKilder((v) => !v)}>
                  {visAlleKilder ? 'Vis færre' : `Vis alle ${alleSources.length}`}
                </button>
              )}
            </>
          )}

          {recentTools.length > 0 && (
            <>
              <div className="env-divider" />
              <div className="env-section-head">Tool-kald</div>
              <div className={`env-tools${flereTools ? ' er-klippet' : ''}`}>
                {recentTools.map((tool) => {
                  const label = formatTool(tool)
                  return (
                    <button type="button" key={tool.id} className="env-tool-chip" title={label} onClick={() => onOpenTool?.(tool)}>
                      {label}
                    </button>
                  )
                })}
              </div>
              {(flereTools || visAlleTools) && (
                <button type="button" className="env-vis-alle" onClick={() => setVisAlleTools((v) => !v)}>
                  {visAlleTools ? 'Vis færre' : `Vis alle ${alleTools.length}`}
                </button>
              )}
            </>
          )}
        </>
      )}

      <div className="env-live">
        {working
          ? <><Activity size={13} className="env-live-icon" /><span className="env-step">{workingStep || 'arbejder…'}</span></>
          : <span className="env-step env-idle">færdig</span>}
        <span className="env-tokens">
          {totalToolCalls > 0 && <>{totalToolCalls} kald · </>}
          {totalTokens > 0 ? `${totalTokens} tokens` : ''}
        </span>
      </div>
    </aside>
  )
}
