import { useEffect, useRef, useState } from 'react'
import { GitBranch, Monitor, Server, Activity, Wrench, Bot, FileText } from 'lucide-react'
import { getGitStatus, type GitStatus, type ApiConfig } from '../../lib/api'
import type { ContentBlock } from '../../lib/sseProtocol'

/** Tool-navne der er agent-dispatch (vises som "agenter", ikke almindelige tools). */
const AGENT_TOOLS = new Set(['dispatch_code_mode_task', 'dispatch_to_claude_code', 'spawn_subagent'])

/** Pænt tool-navn: snake_case → "Snake case". */
function prettyTool(name: string): string {
  const n = (name || '').replace(/_/g, ' ').trim()
  return n ? n.charAt(0).toUpperCase() + n.slice(1) : 'tool'
}

/** Miljø-felt (code mode) — som Codex' "Miljø"-panel. Viser ændringer (+/-),
 *  branch, workspace-type, berørte filer, samt LIVE de tools + agenter Jarvis
 *  kalder, plus token-forbrug. Når et run først er startet i en session, BLIVER
 *  panelet stående hele sessionen (Bjørn 2026-06-17) — ikke kun mens han arbejder.
 *  Nulstilles når sessionen skifter. */
export function EnvironmentPanel({
  config, kind, root, refreshKey = 0,
  working, workingStep, tokens, blocks = [], sessionId, hasHistory = false,
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
}) {
  const [git, setGit] = useState<GitStatus | null>(null)

  // Session-latch: panelet vises fra første run OG når en gammel session med
  // historik loades (fx ved app-genstart) — resten af sessionen. Nulstilles ved
  // session-skift, så ny tom samtale starter rent.
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

  // Udled live tools/agenter + berørte filer fra stream-blokkene.
  const agentNames: string[] = []
  const toolNames: string[] = []
  const fileSet = new Set<string>()
  for (const b of blocks) {
    if (b.type !== 'tool_use') continue
    const nm = b.name || ''
    if (AGENT_TOOLS.has(nm)) { if (!agentNames.includes(nm)) agentNames.push(nm) }
    else if (nm && !toolNames.includes(nm)) toolNames.push(nm)
    const tp = b.input?.target_path
    if (typeof tp === 'string' && tp) fileSet.add(tp)
  }
  const files = Array.from(fileSet)
  const recentTools = toolNames.slice(-4)

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
        {files.length > 0 && (
          <li className="env-row">
            <span className="env-label"><FileText size={13} /> Filer</span>
            <span className="env-val">{files.length}</span>
          </li>
        )}
      </ul>

      {(recentTools.length > 0 || agentNames.length > 0) && (
        <div className="env-tools">
          {recentTools.map((t) => (
            <span key={t} className="env-tool-chip" title={t}><Wrench size={11} /> {prettyTool(t)}</span>
          ))}
          {agentNames.map((a) => (
            <span key={a} className="env-tool-chip is-agent" title={a}><Bot size={11} /> {prettyTool(a)}</span>
          ))}
        </div>
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
