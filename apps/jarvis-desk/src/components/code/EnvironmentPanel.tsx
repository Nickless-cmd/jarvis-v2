import { useEffect, useRef, useState } from 'react'
import { GitBranch, Monitor, Server, Globe, Bot, Settings, Activity, GitCompare, GitCommitHorizontal, Github } from 'lucide-react'
import { RunHealth } from './RunHealth'
import { getGitStatus, commitAllChanges, createPullRequest, type GitStatus, type ApiConfig } from '../../lib/api'
import { lookupTool } from '../../lib/toolRegistry'

/** Tool-navne der er agent-dispatch (vises som "Underagenter" à la Codex). */
/**
 * Vaerktoejer der STARTER en agent.
 *
 * Listen navngav foer fire dispatch-vaerktoejer — hvoraf `spawn_subagent` slet
 * ikke findes — og manglede dem han faktisk bruger. `explore` er ordret «send a
 * read-only research agent», og den kaldes hele tiden; den stod bare ikke her,
 * saa «Underagenter» var tom naesten altid (Bjoern 8/9-2026).
 *
 * De agent-STYRENDE vaerktoejer (list_agents, send_message_to_agent,
 * relay_to_agent, cancel_agent) hoerer IKKE hjemme her. De starter ingen agent;
 * at tage dem med ville faa et opslag i listen til at se ud som en agent.
 */
const AGENT_TOOLS = new Set([
  'explore',
  'task',
  'convene_council',
  'quick_council_check',
  'dispatch_code_mode_task',
  'dispatch_to_claude_code',
  'agent_dispatch',
])
/** Tool-navne der er eksterne kilder (Codex "Kilder"). */
const SOURCE_RULES: { match: (n: string) => boolean; label: string }[] = [
  { match: (n) => /web.?search|search.?web|websearch/.test(n), label: 'Websøgning' },
  { match: (n) => /web.?fetch|fetch.?url|browse|open_url/.test(n), label: 'Web-hentning' },
]
const AGENT_COLORS = ['#e0843a', '#3ab85f', '#9b6bff', '#e0556b', '#3a9be0']

export interface ToolInvocation {
  name: string
  input: Record<string, unknown>
  /** Kun sat for LIVE kald (fra streamens blokke). Persisterede kald fra
   *  sessionen har den ikke — og det er rigtigt: de er per definition faerdige. */
  status?: 'running' | 'done' | 'error'
}

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
  tools?: ToolInvocation[]
  sessionId?: string | null
  hasHistory?: boolean
  isOwner?: boolean
  onChanged?: () => void
  gitMissing?: boolean
  komprimerVed?: number
  /** Kontekst-fyldet som ringen i skrivefeltet maaler det. `totalTokens` er noget
   *  ANDET — sessionens kumulative forbrug — og duer ikke som kontekst-tal:
   *  den falder aldrig naar compaction fyrer. */
  kontekstTokens?: number
  installingTool?: string
  onInstallTool?: (tool: string) => void
}) {
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

  // Udled underagenter, kilder + pænt-formaterede tool-kald fra SESSIONENS tools.
  const agents: ToolInvocation[] = []
  const sources: string[] = []
  const toolLabels: string[] = []
  for (const t of tools) {
    const nm = t.name || ''
    if (AGENT_TOOLS.has(nm)) {
      // KOERENDE agenter staar hver for sig — to parallelle explore-kald er to
      // agenter, ikke én. Faerdige samles fortsat pr. navn, ellers ville listen
      // vokse med hver eneste tur.
      if (t.status === 'running' || !agents.some((a) => a.name === nm && a.status !== 'running')) {
        agents.push(t)
      }
      continue
    }
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
                {agents.map((a, i) => {
                  const farve = AGENT_COLORS[i % AGENT_COLORS.length]
                  const koerer = a.status === 'running'
                  // Opgaven staar, ikke bare vaerktoejsnavnet: «(worker)» sagde
                  // ingenting om hvad agenten var sat til. For explore er det
                  // `query`, for task `prompt`, for et raad `question`.
                  const opgave = String(
                    a.input?.query ?? a.input?.task ?? a.input?.prompt
                    ?? a.input?.description ?? a.input?.instruction ?? a.input?.question ?? '',
                  ).replace(/\s+/g, ' ').trim()
                  return (
                    <li className={`env-row${koerer ? ' agent-koerer' : ''}`} key={`${a.name}-${i}`}>
                      <span className="env-label">
                        <Bot size={13} style={{ color: farve }} />
                        <span style={{ color: farve }}>{lookupTool(a.name).label}</span>
                        {opgave && <span className="env-muted agent-opgave" title={opgave}>{opgave}</span>}
                      </span>
                      {koerer && <span className="env-val agent-status">kører</span>}
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
