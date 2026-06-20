// Teams REST-klient (mobil). Tynd wrapper om apiFetch.
import { apiFetch } from './apiClient'
import type { ApiConfig } from './types'

export interface TeamMember { user_id: string; team_role: string }
export interface Team { team_id: string; name: string; members: TeamMember[] }
export interface TeamSession { session_id: string; title: string }

export async function listTeams(config: ApiConfig): Promise<Team[]> {
  const r = await apiFetch<{ teams: Team[] }>(config, '/teams')
  return r.teams ?? []
}
export async function createTeam(config: ApiConfig, name: string): Promise<Team> {
  return apiFetch<Team>(config, '/teams', { method: 'POST', body: { name } })
}
export async function listTeamSessions(config: ApiConfig, teamId: string): Promise<TeamSession[]> {
  const r = await apiFetch<{ sessions: TeamSession[] }>(config, `/teams/${teamId}/sessions`)
  return r.sessions ?? []
}
export async function createTeamSession(config: ApiConfig, teamId: string, title: string): Promise<TeamSession> {
  return apiFetch<TeamSession>(config, `/teams/${teamId}/sessions`, { method: 'POST', body: { title } })
}
export async function acceptInvite(config: ApiConfig, token: string): Promise<{ team_id: string }> {
  return apiFetch(config, `/invites/${encodeURIComponent(token)}/accept`, { method: 'POST' })
}
