import { useEffect, useState } from 'react'
import { useSettings } from '../../hooks/useSettings'
import {
  listTeams, createTeam, inviteToTeam, listTeamSessions, createTeamSession,
  type Team, type TeamSession,
} from '../../lib/teamsApi'

/** Teams-sektion i sidebar (Teams-feature §6.1). Separat foldbar liste UNDER de
 *  private sessioner. Lister teams + delte sessioner; opret team/session; inviter.
 *  En team-session åbnes i chat-fladen via onOpenSession (synlig for alle medlemmer
 *  via scoping-regel B). */
export function TeamsSection({ onOpenSession }: { onOpenSession: (sessionId: string) => void }) {
  const { settings } = useSettings()
  const [teams, setTeams] = useState<Team[]>([])
  const [open, setOpen] = useState<Record<string, boolean>>({})
  const [sessionsByTeam, setSessionsByTeam] = useState<Record<string, TeamSession[]>>({})
  const cfg = settings ? { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken } : undefined

  const refresh = async () => {
    if (!cfg) return
    try { setTeams(await listTeams(cfg)) } catch { /* behold */ }
  }
  useEffect(() => { void refresh() }, [settings?.authToken])

  const loadSessions = async (teamId: string) => {
    if (!cfg) return
    try {
      const ss = await listTeamSessions(cfg, teamId)
      setSessionsByTeam((m) => ({ ...m, [teamId]: ss }))
    } catch { /* noop */ }
  }

  const toggle = (teamId: string) => {
    setOpen((o) => {
      const next = !o[teamId]
      if (next) void loadSessions(teamId)
      return { ...o, [teamId]: next }
    })
  }

  const onNew = async () => {
    if (!cfg) return
    const name = window.prompt('Navn på nyt team?')?.trim()
    if (!name) return
    try { await createTeam(cfg, name); await refresh() } catch { /* noop */ }
  }

  const onNewSession = async (t: Team) => {
    if (!cfg) return
    const title = window.prompt(`Ny delt session i "${t.name}":`, 'Team-chat')?.trim()
    if (!title) return
    try {
      const s = await createTeamSession(cfg, t.team_id, title)
      await loadSessions(t.team_id)
      onOpenSession(s.session_id)
    } catch { /* noop */ }
  }

  const onInvite = async (t: Team) => {
    if (!cfg) return
    const v = window.prompt(`Inviter til "${t.name}" — email eller bruger-id:`)?.trim()
    if (!v) return
    try {
      const r = await inviteToTeam(cfg, t.team_id, v.includes('@') ? { email: v } : { user_id: v })
      const ways = Object.entries(r.delivered).filter(([, on]) => on).map(([k]) => k)
      window.alert(ways.length ? `Invite sendt via ${ways.join(', ')}.` : 'Invite oprettet (kode i app).')
    } catch { window.alert('Kunne ikke invitere (kun owner kan).') }
  }

  return (
    <div className="teams-section">
      <div className="teams-head">
        <span className="teams-title">TEAMS</span>
        <button type="button" className="teams-new" onClick={() => void onNew()} title="Nyt team">＋</button>
      </div>
      {teams.length === 0 && <div className="teams-empty">Ingen teams endnu</div>}
      {teams.map((t) => (
        <div key={t.team_id} className="team-row">
          <button type="button" className="team-name" onClick={() => toggle(t.team_id)}>
            <span className="team-caret">{open[t.team_id] ? '▾' : '▸'}</span> {t.name}
            <span className="team-count">{t.members.length}</span>
          </button>
          {open[t.team_id] && (
            <div className="team-body">
              {(sessionsByTeam[t.team_id] ?? []).map((s) => (
                <button key={s.session_id} type="button" className="team-session"
                  onClick={() => onOpenSession(s.session_id)}># {s.title || 'Team-chat'}</button>
              ))}
              <div className="team-actions">
                <button type="button" className="team-mini" onClick={() => void onNewSession(t)}>+ Session</button>
                <button type="button" className="team-mini" onClick={() => void onInvite(t)}>+ Inviter</button>
              </div>
              <div className="team-members">
                {t.members.map((m) => <span key={m.user_id} className="team-member">{m.user_id}{m.team_role === 'owner' ? ' ⭐' : ''}</span>)}
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
