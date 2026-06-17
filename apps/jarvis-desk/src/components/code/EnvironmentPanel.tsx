import { useEffect, useRef, useState } from 'react'
import { GitBranch, Monitor, Server, Globe, Bot, Settings, Activity, GitCompare, GitCommitHorizontal, Github } from 'lucide-react'
import { getGitStatus, commitAllChanges, createPullRequest, type GitStatus, type ApiConfig } from '../../lib/api'
import { lookupTool } from '../../lib/toolRegistry'

/** Tool-navne der er agent-dispatch (vises som "Underagenter" à la Codex). */
const AGENT_TOOLS = new Set(['dispatch_code_mode_task', 'dispatch_to_claude_code', 'spawn_subagent', 'agent_dispatch'])
/** Tool-navne der er eksterne kilder (Codex "Kilder"). */
const SOURCE_RULES: { match: (n: string) => boolean; label: string }[] = [
  { match: (n) => /web.?search|search.?web|websearch/.test(n), label: 'Websøgning' },
  { match: (n) => /web.?fetch|fetch.?url|browse|open_url/.test(n), label: 'Web-hentning' },
]
const AGENT_COLORS = ['#e0843a', '#3ab85f', '#9b6bff', '#e0556b', '#3a9be0']

export interface ToolInvocation { name: string; input: Record<string, unknown> }

/** Pænt tool-label som i chatview: label + opsummering (kommando/sti). For
 *  operator_bash bliver det fx "Terminal: git status" — IKKE bare "operator_bash". */
function formatTool(t: ToolInvocation): string {
  const meta = lookupTool(t.name)
  const summary = meta.summarize(t.input || {})
  const short = summary.length > 38 ? summary.slice(0, 37) + '…' : summary
  return short ? `${meta.label}: ${short}` : meta.label
}

/** Miljø-felt (code mode) — 1:1 med Codex' "Miljø"-panel: Ændringer (+/−),
 *  workspace-type, branch, Underagenter, Kilder + SESSION-totaler (tokens,
 *  tool-kald) der akkumuleres HELE sessionen igennem (ikke pr. run). Tool-kald
 *  formateres som i chatview via toolRegistry. Latches fra session-start/resume,
 *  nulstilles ved session-skift. Skjules af CodeView ved åbne paneler/smalt vindue. */
export function EnvironmentPanel({
  config, kind, root, refreshKey = 0,
  working, workingStep, totalTokens = 0, totalToolCalls = 0, tools = [], sessionId, hasHistory = false,
  isOwner = false, onChanged,
  gitMissing = false, installingTool = '', onInstallTool,
}: {
  config?: ApiConfig
  kind: 'container' | 'workstation'
  root: string
  refreshKey?: number
  working: boolean
  workingStep?: string
  totalTokens?: number
  totalToolCalls?: number
  tools?: ToolInvocation[]
  sessionId?: string | null
  hasHistory?: boolean
  isOwner?: boolean
  onChanged?: () => void
  gitMissing?: boolean
  installingTool?: string
  onInstallTool?: (tool: string) => void
}) {
  const [git, setGit] = useState<GitStatus | null>(null)
  const [collapsed, setCollapsed] = useState(false)
  const [busy, setBusy] = useState<'' | 'commit' | 'pr'>('')
  const [note, setNote] = useState<{ text: string; url?: string; err?: boolean } | null>(null)

  const canGit = !!git?.is_git && (
    (isOwner && kind === 'container' && root === 'repo') || kind === 'workstation'
  )
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

  // Udled underagenter, kilder + pænt-formaterede tool-kald fra SESSIONENS tools.
  const agents: ToolInvocation[] = []
  const sources: string[] = []
  const toolLabels: string[] = []
  for (const t of tools) {
    const nm = t.name || ''
    if (AGENT_TOOLS.has(nm)) { if (!agents.some((a) => a.name === nm)) agents.push(t); continue }
    const src = SOURCE_RULES.find((r) => r.match(nm))
    if (src) { if (!sources.includes(src.label)) sources.push(src.label); continue }
    if (nm) {
      const label = formatTool(t)
      if (!toolLabels.includes(label)) toolLabels.push(label)
    }
  }
  const recentTools = toolLabels.slice(-5)

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
            {gitMissing && kind === 'workstation' && (
              <li className="env-row env-action">
                <button type="button" className="env-actbtn" disabled={installingTool === 'git'}
                  onClick={() => onInstallTool?.('git')}>
                  <GitCompare size={13} /> {installingTool === 'git' ? 'Installerer git…' : 'git mangler — installér'}
                </button>
              </li>
            )}
            {git?.is_git && git.dirty > 0 && (
              <li className="env-row">
                <span className="env-label"><GitCompare size={13} /> Ændringer</span>
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
                {agents.map((a, i) => (
                  <li className="env-row" key={a.name}>
                    <span className="env-label">
                      <Bot size={13} style={{ color: AGENT_COLORS[i % AGENT_COLORS.length] }} />
                      <span style={{ color: AGENT_COLORS[i % AGENT_COLORS.length] }}>{lookupTool(a.name).label}</span>
                      <span className="env-muted">(worker)</span>
                    </span>
                  </li>
                ))}
              </ul>
            </>
          )}

          {sources.length > 0 && (
            <>
              <div className="env-divider" />
              <div className="env-section-head">Kilder</div>
              <ul className="env-rows">
                {sources.map((s) => (
                  <li className="env-row" key={s}>
                    <span className="env-label"><Globe size={13} /> {s}</span>
                  </li>
                ))}
              </ul>
            </>
          )}

          {recentTools.length > 0 && (
            <>
              <div className="env-divider" />
              <div className="env-section-head">Tool-kald</div>
              <div className="env-tools">
                {recentTools.map((label) => (
                  <span key={label} className="env-tool-chip" title={label}>{label}</span>
                ))}
              </div>
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
