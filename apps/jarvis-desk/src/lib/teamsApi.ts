// Teams REST-klient (Teams-feature, spec 2026-06-20 §6). Tynd wrapper om apiFetch.
import { apiFetch, type ApiConfig } from './api'

export interface TeamMember {
  user_id: string
  team_role: string
}

export interface Team {
  team_id: string
  name: string
  owner_user_id: string
  members: TeamMember[]
}

export async function listTeams(config: ApiConfig): Promise<Team[]> {
  const r = await apiFetch<{ teams: Team[] }>(config, '/teams')
  return r.teams ?? []
}

export async function createTeam(config: ApiConfig, name: string): Promise<Team> {
  return apiFetch<Team>(config, '/teams', { method: 'POST', body: { name } })
}

export async function inviteToTeam(
  config: ApiConfig, teamId: string, invitee: { email?: string; user_id?: string },
): Promise<{ token: string; invited: string; delivered: Record<string, boolean> }> {
  return apiFetch(config, `/teams/${teamId}/invite`, { method: 'POST', body: invitee })
}

export async function acceptInvite(config: ApiConfig, token: string): Promise<{ team_id: string }> {
  return apiFetch(config, `/invites/${token}/accept`, { method: 'POST' })
}

export interface TeamSession {
  session_id: string
  title: string
}

export async function listTeamSessions(config: ApiConfig, teamId: string): Promise<TeamSession[]> {
  const r = await apiFetch<{ sessions: TeamSession[] }>(config, `/teams/${teamId}/sessions`)
  return r.sessions ?? []
}

export async function createTeamSession(config: ApiConfig, teamId: string, title: string): Promise<TeamSession> {
  return apiFetch(config, `/teams/${teamId}/sessions`, { method: 'POST', body: { title } })
}
