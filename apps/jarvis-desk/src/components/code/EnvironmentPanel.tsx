import { useEffect, useRef, useState } from 'react'
import { GitBranch, Monitor, Server, Globe, Bot, Settings, Activity, Wrench, GitCompare, GitCommitHorizontal, Github } from 'lucide-react'
import { getGitStatus, commitAllChanges, createPullRequest, type GitStatus, type ApiConfig } from '../../lib/api'
import type { ContentBlock } from '../../lib/sseProtocol'

/** Tool-navne der er agent-dispatch (vises som "Underagenter" à la Codex). */
const AGENT_TOOLS = new Set(['dispatch_code_mode_task', 'dispatch_to_claude_code', 'spawn_subagent', 'agent_dispatch'])
/** Tool-navne der er eksterne kilder (Codex "Kilder"). */
const SOURCE_RULES: { match: (n: string) => boolean; label: string }[] = [
  { match: (n) => /web.?search|search.?web|websearch/.test(n), label: 'Websøgning' },
  { match: (n) => /web.?fetch|fetch.?url|browse|open_url/.test(n), label: 'Web-hentning' },
]
/** Codex-agtige agent-farver (orange/grøn/lilla/rød/blå). */
const AGENT_COLORS = ['#e0843a', '#3ab85f', '#9b6bff', '#e0556b', '#3a9be0']

function prettyTool(name: string): string {
  const n = (name || '').replace(/_/g, ' ').trim()
  return n ? n.charAt(0).toUpperCase() + n.slice(1) : 'tool'
}

/** Miljø-felt (code mode) — 1:1 med Codex' "Miljø"-panel: Ændringer (+/−),
 *  workspace-type, branch, Underagenter (farvede bots) og Kilder. Plus vores
 *  ekstra: live tools + token-forbrug. Vises fra session-start / ved resume af
 *  en gammel session (latch på hasHistory), forsvinder ved session-skift.
 *  Skjules af CodeView når fil-træ/preview er åbent eller vinduet er for smalt. */
export function EnvironmentPanel({
  config, kind, root, refreshKey = 0,
  working, workingStep, tokens, blocks = [], sessionId, hasHistory = false,
  isOwner = false, onChanged,
}: {
  config?: ApiConfig
  kind: 'container' | 'workstation'
  root: string
  refreshKey?: number
  working: boolean
  workingStep?: string
  tokens?: number
  blocks?: ContentBlock[]
  sessionId?: string | null
  hasHistory?: boolean
  isOwner?: boolean
  onChanged?: () => void
}) {
  const [git, setGit] = useState<GitStatus | null>(null)
  const [collapsed, setCollapsed] = useState(false)
  const [busy, setBusy] = useState<'' | 'commit' | 'pr'>('')
  const [note, setNote] = useState<{ text: string; url?: string; err?: boolean } | null>(null)

  // Git-actions er rolle-bestemt: server-repoet ('repo') KUN owner; workstation-
  // repo gælder alle roller på deres EGEN maskine (uid-routet på serveren).
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

  // Udled underagenter, kilder, live-tools fra stream-blokkene.
  const agents: string[] = []
  const toolNames: string[] = []
  const sources: string[] = []
  for (const b of blocks) {
    if (b.type !== 'tool_use') continue
    const nm = b.name || ''
    if (AGENT_TOOLS.has(nm)) { if (!agents.includes(nm)) agents.push(nm) }
    else {
      const src = SOURCE_RULES.find((r) => r.match(nm))
      if (src) { if (!sources.includes(src.label)) sources.push(src.label) }
      else if (nm && !toolNames.includes(nm)) toolNames.push(nm)
    }
  }
  const recentTools = toolNames.slice(-4)

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
                  <li className="env-row" key={a}>
                    <span className="env-label">
                      <Bot size={13} style={{ color: AGENT_COLORS[i % AGENT_COLORS.length] }} />
                      <span style={{ color: AGENT_COLORS[i % AGENT_COLORS.length] }}>{prettyTool(a)}</span>
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
              <div className="env-tools">
                {recentTools.map((t) => (
                  <span key={t} className="env-tool-chip" title={t}><Wrench size={11} /> {prettyTool(t)}</span>
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
        {typeof tokens === 'number' && tokens > 0 && <span className="env-tokens">{tokens} tokens</span>}
      </div>
    </aside>
  )
}
