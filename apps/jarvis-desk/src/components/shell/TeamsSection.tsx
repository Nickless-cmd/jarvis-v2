import { useEffect, useState } from 'react'
import { useSettings } from '../../hooks/useSettings'
import {
  listTeams, createTeam, inviteToTeam, listTeamSessions, createTeamSession,
  type Team, type TeamSession,
} from '../../lib/teamsApi'

/** Teams-sektion i sidebar (Teams-feature §6.1). Separat foldbar liste UNDER de
 *  private sessioner. Lister teams + delte sessioner; opret team/session; inviter.
 *  En team-session åbnes i chat-fladen via onOpenSession (synlig for alle medlemmer
 *  via scoping-regel B).
 *
 *  VIGTIGT: Electron understøtter IKKE window.prompt()/window.alert() — de returnerer
 *  null/no-op, hvilket fik knapperne til at "gøre ingenting uden fejl" (Mikkel-test
 *  2026-06-20). Derfor bruger sektionen inline input-felter + en status-linje, samme
 *  mønster som mobil-TeamsPanel. */
export function TeamsSection({ onOpenSession }: { onOpenSession: (sessionId: string) => void }) {
  const { settings } = useSettings()
  const [teams, setTeams] = useState<Team[]>([])
  const [open, setOpen] = useState<Record<string, boolean>>({})
  const [sessionsByTeam, setSessionsByTeam] = useState<Record<string, TeamSession[]>>({})
  const [newTeam, setNewTeam] = useState('')
  const [showNew, setShowNew] = useState(false)
  const [sessTitle, setSessTitle] = useState<Record<string, string>>({})
  const [inviteVal, setInviteVal] = useState<Record<string, string>>({})
  const [msg, setMsg] = useState('')
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

  const onCreateTeam = async () => {
    const name = newTeam.trim()
    if (!cfg || !name) return
    try { await createTeam(cfg, name); setNewTeam(''); setShowNew(false); setMsg(''); await refresh() }
    catch { setMsg('Kunne ikke oprette team') }
  }

  const onNewSession = async (t: Team) => {
    if (!cfg) return
    const title = (sessTitle[t.team_id] ?? '').trim() || 'Team-chat'
    try {
      const s = await createTeamSession(cfg, t.team_id, title)
      setSessTitle((m) => ({ ...m, [t.team_id]: '' }))
      await loadSessions(t.team_id)
      onOpenSession(s.session_id)
    } catch { setMsg('Kunne ikke oprette session') }
  }

  const onInvite = async (t: Team) => {
    if (!cfg) return
    const v = (inviteVal[t.team_id] ?? '').trim()
    if (!v) return
    try {
      const r = await inviteToTeam(cfg, t.team_id, v.includes('@') ? { email: v } : { user_id: v })
      const ways = Object.entries(r.delivered).filter(([, on]) => on).map(([k]) => k)
      setInviteVal((m) => ({ ...m, [t.team_id]: '' }))
      setMsg(ways.length ? `Invite sendt via ${ways.join(', ')}.` : 'Invite oprettet (kode i app).')
    } catch { setMsg('Kunne ikke invitere (kun owner kan).') }
  }

  return (
    <div className="teams-section">
      <div className="teams-head">
        <span className="teams-title">TEAMS</span>
        <button type="button" className="teams-new" onClick={() => setShowNew((s) => !s)} title="Nyt team">＋</button>
      </div>
      {showNew && (
        <div className="team-actions">
          <input className="team-input" value={newTeam} placeholder="Nyt team-navn" aria-label="Nyt team-navn"
            onChange={(e) => setNewTeam(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') void onCreateTeam() }} autoFocus />
          <button type="button" className="team-mini" onClick={() => void onCreateTeam()}>Opret</button>
        </div>
      )}
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
                <input className="team-input" value={sessTitle[t.team_id] ?? ''} placeholder="Session-titel"
                  aria-label="Session-titel"
                  onChange={(e) => setSessTitle((m) => ({ ...m, [t.team_id]: e.target.value }))}
                  onKeyDown={(e) => { if (e.key === 'Enter') void onNewSession(t) }} />
                <button type="button" className="team-mini" onClick={() => void onNewSession(t)}>+ Session</button>
              </div>
              <div className="team-actions">
                <input className="team-input" value={inviteVal[t.team_id] ?? ''} placeholder="Email eller bruger-id"
                  aria-label="Inviter"
                  onChange={(e) => setInviteVal((m) => ({ ...m, [t.team_id]: e.target.value }))}
                  onKeyDown={(e) => { if (e.key === 'Enter') void onInvite(t) }} />
                <button type="button" className="team-mini" onClick={() => void onInvite(t)}>+ Inviter</button>
              </div>
              <div className="team-members">
                {t.members.map((m) => <span key={m.user_id} className="team-member">{m.user_id}{m.team_role === 'owner' ? ' ⭐' : ''}</span>)}
              </div>
            </div>
          )}
        </div>
      ))}
      {msg && <div className="teams-msg">{msg}</div>}
    </div>
  )
}
