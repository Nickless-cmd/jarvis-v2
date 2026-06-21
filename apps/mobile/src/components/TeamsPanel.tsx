import { useEffect, useState } from 'react'
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native'
import type { ApiConfig } from '../lib/types'
import {
  listTeams, createTeam, listTeamSessions, createTeamSession, acceptInvite,
  type Team, type TeamSession,
} from '../lib/teamsApi'
import { tokens } from '../theme/tokens'

/** Teams i mobil-drawer'en: list teams + delte sessioner, opret team/session,
 *  acceptér invite-kode. En team-session åbnes via onSelectSession (samme som en
 *  almindelig session — synlig for alle medlemmer via scoping-regel B). */
export function TeamsPanel({ config, onSelectSession }: { config: ApiConfig | null; onSelectSession: (sessionId: string) => void }) {
  const [teams, setTeams] = useState<Team[]>([])
  const [openId, setOpenId] = useState<string | null>(null)
  const [sessions, setSessions] = useState<Record<string, TeamSession[]>>({})
  const [newTeam, setNewTeam] = useState('')
  const [code, setCode] = useState('')
  const [msg, setMsg] = useState('')

  const refresh = async () => {
    if (!config) return
    try { setTeams(await listTeams(config)) } catch { /* behold */ }
  }
  useEffect(() => { void refresh() }, [config?.authToken])

  const toggle = async (id: string) => {
    const next = openId === id ? null : id
    setOpenId(next)
    if (next && config && !sessions[id]) {
      try { const ss = await listTeamSessions(config, id); setSessions((m) => ({ ...m, [id]: ss })) } catch { /* noop */ }
    }
  }

  const onCreateTeam = async () => {
    if (!config || !newTeam.trim()) return
    try { await createTeam(config, newTeam.trim()); setNewTeam(''); await refresh() } catch { setMsg('Kunne ikke oprette team') }
  }

  const onNewSession = async (t: Team) => {
    if (!config) return
    try {
      const s = await createTeamSession(config, t.team_id, 'Team-chat')
      const ss = await listTeamSessions(config, t.team_id)
      setSessions((m) => ({ ...m, [t.team_id]: ss }))
      onSelectSession(s.session_id)
    } catch { setMsg('Kunne ikke oprette session') }
  }

  const onAccept = async () => {
    if (!config || !code.trim()) return
    try { await acceptInvite(config, code.trim()); setCode(''); setMsg('Tilmeldt team ✓'); await refresh() }
    catch { setMsg('Ugyldig eller udløbet kode') }
  }

  // Uden config (ingen gyldig auth — fx efter QR-paring der ikke gav et
  // login-token) ville alle handlers tavst no-oppe. Vis tilstanden i stedet,
  // så fejlen er synlig (Mikkel-test 2026-06-20: "knapper gør ingenting").
  if (!config) {
    return (
      <View style={styles.root}>
        <Text style={styles.heading}>TEAMS</Text>
        <Text style={styles.muted}>Log ind for at bruge teams</Text>
      </View>
    )
  }

  return (
    <View style={styles.root}>
      <Text style={styles.heading}>TEAMS</Text>
      {teams.length === 0 && <Text style={styles.muted}>Ingen teams endnu</Text>}
      {teams.map((t) => (
        <View key={t.team_id}>
          <Pressable onPress={() => void toggle(t.team_id)} style={styles.teamRow}>
            <Text style={styles.teamName}>{openId === t.team_id ? '▾' : '▸'} {t.name}</Text>
            <Text style={styles.count}>{t.members.length}</Text>
          </Pressable>
          {openId === t.team_id && (
            <View style={styles.body}>
              {(sessions[t.team_id] ?? []).map((s) => (
                <Pressable key={s.session_id} onPress={() => onSelectSession(s.session_id)} style={styles.sessRow}>
                  <Text style={styles.sess}># {s.title || 'Team-chat'}</Text>
                </Pressable>
              ))}
              <Pressable onPress={() => void onNewSession(t)} style={styles.mini}><Text style={styles.miniTxt}>+ Ny session</Text></Pressable>
            </View>
          )}
        </View>
      ))}
      <View style={styles.inputRow}>
        <TextInput value={newTeam} onChangeText={setNewTeam} placeholder="Nyt team-navn"
          placeholderTextColor={tokens.color.fg3} style={styles.input} />
        <Pressable onPress={() => void onCreateTeam()} style={styles.mini}><Text style={styles.miniTxt}>Opret</Text></Pressable>
      </View>
      <View style={styles.inputRow}>
        <TextInput value={code} onChangeText={setCode} placeholder="Invite-kode"
          placeholderTextColor={tokens.color.fg3} autoCapitalize="none" style={styles.input} />
        <Pressable onPress={() => void onAccept()} style={styles.mini}><Text style={styles.miniTxt}>Tilmeld</Text></Pressable>
      </View>
      {msg ? <Text style={styles.msg}>{msg}</Text> : null}
    </View>
  )
}

const styles = StyleSheet.create({
  root: { borderTopColor: tokens.color.line, borderTopWidth: 1, paddingTop: tokens.spacing.md, marginTop: tokens.spacing.md },
  heading: { color: tokens.color.fg3, fontSize: 12, fontWeight: '700', letterSpacing: 1, marginBottom: 6 },
  muted: { color: tokens.color.fg3, fontSize: 13, paddingVertical: 4 },
  teamRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 8 },
  teamName: { color: tokens.color.fg1, fontWeight: '600' },
  count: { color: tokens.color.fg3, fontSize: 12 },
  body: { paddingLeft: 12, paddingBottom: 6 },
  sessRow: { paddingVertical: 6 },
  sess: { color: tokens.color.fg1 },
  mini: { backgroundColor: tokens.color.bg1, borderRadius: 8, paddingVertical: 6, paddingHorizontal: 12, alignSelf: 'flex-start' },
  miniTxt: { color: tokens.color.accent, fontSize: 13 },
  inputRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 8 },
  input: { flex: 1, color: tokens.color.fg1, backgroundColor: tokens.color.bg1, borderRadius: 8, paddingHorizontal: 10, paddingVertical: 6 },
  msg: { color: tokens.color.accent, marginTop: 6, fontSize: 12 },
})
