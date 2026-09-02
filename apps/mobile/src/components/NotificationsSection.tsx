import { useEffect, useState } from 'react'
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native'
import { apiFetch } from '../lib/apiClient'
import type { ApiConfig } from '../lib/types'
import { tokens } from '../theme/tokens'

type Channel = 'auto' | 'mobile' | 'desktop' | 'push' | 'discord' | 'telegram'
interface Prefs {
  global: Channel
  briefing: Channel | null; reminder: Channel | null; reach_out: Channel | null
  team_invite: Channel | null; wakeup: Channel | null
  quiet_start: string; quiet_end: string
}

const CHANNELS: Channel[] = ['auto', 'mobile', 'desktop', 'push', 'discord', 'telegram']
const TYPES: { key: keyof Prefs; label: string }[] = [
  { key: 'global', label: 'Standard (alle)' },
  { key: 'briefing', label: 'Morgenbriefing' },
  { key: 'reminder', label: 'Påmindelser' },
  { key: 'reach_out', label: 'Jarvis tager kontakt' },
  { key: 'team_invite', label: 'Team-invitationer' },
  { key: 'wakeup', label: 'Wakeups' },
]

/** Notifikations-routing (spec §6): vælg hvor proaktive notifikationer lander +
 *  quiet hours. Gemmer via /notifications/preferences. */
export function NotificationsSection({ config }: { config: ApiConfig | null }) {
  const [prefs, setPrefs] = useState<Prefs | null>(null)
  const [status, setStatus] = useState('')

  useEffect(() => {
    if (!config) return
    void apiFetch<{ preferences: Prefs }>(config, '/notifications/preferences')
      .then((r) => setPrefs(r.preferences)).catch(() => setStatus('Kunne ikke hente'))
  }, [config?.authToken])

  const save = async (patch: Partial<Prefs>) => {
    if (!config || !prefs) return
    setPrefs({ ...prefs, ...patch })
    try {
      const r = await apiFetch<{ preferences: Prefs }>(config, '/notifications/preferences',
        { method: 'POST', body: patch })
      setPrefs(r.preferences); setStatus('Gemt ✓')
    } catch { setStatus('Kunne ikke gemme') }
  }

  if (!config) return null
  if (!prefs) {
    return (
      <View style={styles.root}>
        <Text style={styles.heading}>NOTIFIKATIONER</Text>
        <Text style={styles.muted}>{status || 'Henter…'}</Text>
      </View>
    )
  }

  return (
    <View style={styles.root}>
      <Text style={styles.heading}>NOTIFIKATIONER</Text>
      <Text style={styles.muted}>Hvor Jarvis' proaktive beskeder lander. "Standard" gælder alle; vælg per type for at overstyre.</Text>
      {TYPES.map((t) => {
        const isGlobal = t.key === 'global'
        const val = (prefs[t.key] as Channel | null) ?? null
        return (
          <View key={t.key} style={styles.typeRow}>
            <Text style={styles.typeLabel}>{t.label}</Text>
            <View style={styles.chips}>
              {!isGlobal && (
                <Pressable onPress={() => void save({ [t.key]: null } as Partial<Prefs>)}
                  style={[styles.chip, val === null && styles.chipOn]}>
                  <Text style={[styles.chipTxt, val === null && styles.chipTxtOn]}>standard</Text>
                </Pressable>
              )}
              {CHANNELS.map((c) => (
                <Pressable key={c} onPress={() => void save({ [t.key]: c } as Partial<Prefs>)}
                  style={[styles.chip, val === c && styles.chipOn]}>
                  <Text style={[styles.chipTxt, val === c && styles.chipTxtOn]}>{c}</Text>
                </Pressable>
              ))}
            </View>
          </View>
        )
      })}
      <View style={styles.typeRow}>
        <Text style={styles.typeLabel}>Stille-timer</Text>
        <View style={styles.quiet}>
          <TextInput value={prefs.quiet_start} onChangeText={(v) => setPrefs({ ...prefs, quiet_start: v })}
            onEndEditing={() => void save({ quiet_start: prefs.quiet_start })}
            placeholder="23:00" placeholderTextColor={tokens.color.fg3} style={styles.time} />
          <Text style={styles.muted}> – </Text>
          <TextInput value={prefs.quiet_end} onChangeText={(v) => setPrefs({ ...prefs, quiet_end: v })}
            onEndEditing={() => void save({ quiet_end: prefs.quiet_end })}
            placeholder="07:00" placeholderTextColor={tokens.color.fg3} style={styles.time} />
        </View>
      </View>
      {status ? <Text style={styles.msg}>{status}</Text> : null}
    </View>
  )
}

const styles = StyleSheet.create({
  root: { borderTopColor: tokens.color.line, borderTopWidth: 1, paddingTop: tokens.spacing.md, marginTop: tokens.spacing.md },
  heading: { color: tokens.color.fg3, fontSize: 12, fontWeight: '700', letterSpacing: 1, marginBottom: 6 },
  muted: { color: tokens.color.fg3, fontSize: 12 },
  typeRow: { marginVertical: 6 },
  typeLabel: { color: tokens.color.fg1, fontSize: 13, fontWeight: '600', marginBottom: 4 },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  chip: { borderWidth: 1, borderColor: tokens.color.line, borderRadius: 999, paddingVertical: 3, paddingHorizontal: 10 },
  chipOn: { backgroundColor: tokens.color.accent, borderColor: tokens.color.accent },
  chipTxt: { color: tokens.color.fg2, fontSize: 12 },
  chipTxtOn: { color: tokens.color.bg0, fontWeight: '700' },
  quiet: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  time: { color: tokens.color.fg1, backgroundColor: tokens.color.bg1, borderRadius: 8, paddingHorizontal: 10, paddingVertical: 4, minWidth: 64, textAlign: 'center' },
  msg: { color: tokens.color.accent, marginTop: 6, fontSize: 12 },
})
