import { useEffect, useState } from 'react'
import { useSettings } from '../../hooks/useSettings'
import { listTeams, createTeam, inviteToTeam, type Team } from '../../lib/teamsApi'

/** Teams-sektion i sidebar (Teams-feature §6.1). Separat foldbar liste UNDER de
 *  private sessioner. Lister teams + medlemmer; opret nyt team; inviter medlem.
 *  Delte team-sessioner under hvert team kommer når session↔team-binding er wiret
 *  (Fase 2c). MVP: gør Teams synligt + oprettbart fra appen. */
export function TeamsSection() {
  const { settings } = useSettings()
  const [teams, setTeams] = useState<Team[]>([])
  const [open, setOpen] = useState<Record<string, boolean>>({})
  const cfg = settings ? { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken } : undefined

  const refresh = async () => {
    if (!cfg) return
    try { setTeams(await listTeams(cfg)) } catch { /* behold */ }
  }
  useEffect(() => { void refresh() }, [settings?.authToken])

  const onNew = async () => {
    if (!cfg) return
    const name = window.prompt('Navn på nyt team?')?.trim()
    if (!name) return
    try { await createTeam(cfg, name); await refresh() } catch { /* noop */ }
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
          <button type="button" className="team-name"
            onClick={() => setOpen((o) => ({ ...o, [t.team_id]: !o[t.team_id] }))}>
            <span className="team-caret">{open[t.team_id] ? '▾' : '▸'}</span> {t.name}
            <span className="team-count">{t.members.length}</span>
          </button>
          {open[t.team_id] && (
            <div className="team-body">
              <div className="team-members">
                {t.members.map((m) => <span key={m.user_id} className="team-member">{m.user_id}{m.team_role === 'owner' ? ' ⭐' : ''}</span>)}
              </div>
              <button type="button" className="team-invite" onClick={() => void onInvite(t)}>+ Inviter</button>
              <div className="team-sessions-hint">Delte sessioner kommer her</div>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
