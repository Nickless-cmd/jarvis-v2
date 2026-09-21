import { useState } from 'react'
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native'
import { Activity, Clock3, PackageCheck, X } from 'lucide-react-native'
import type { ActiveRunSnapshot, Notifikation } from '../lib/apiClient'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'

export function ActivityCenterScreen({
  onClose,
  runs,
  outboxCount = 0,
  presenceSummary = '',
  notifikationer,
  notifFejl = false,
  onAfgoer,
  onGenhent
}: {
  onClose: () => void
  runs: ActiveRunSnapshot[]
  outboxCount?: number
  presenceSummary?: string
  /** `undefined`/`null` = endnu ikke hentet. `[]` = hentet og tom (god nyhed). */
  notifikationer?: Notifikation[] | null
  /** En fejlet hentning maa ALDRIG ligne en tom liste — de to er hver sin besked. */
  notifFejl?: boolean
  onAfgoer?: (id: string, approved: boolean) => Promise<{ ok: boolean; fejl: string }>
  onGenhent?: () => void
}) {
  const tokens = useTheme()
  const styles = useStyles(makes)
  // Id paa den post der lige nu venter paa et svar — deaktiverer dens egne
  // knapper saa et dobbelt-tryk ikke sender to afgoerelser.
  const [travl, setTravl] = useState('')
  // Fejl PR. POST: serveren kaster ikke ved en almindelig fejl (kortet
  // allerede besvaret) — den svarer {ok: false, fejl: "..."}. Ignoreres
  // `svar.ok`, forsvinder posten aldrig, men brugeren faar heller aldrig at
  // vide hvorfor knappen ikke virkede.
  const [handlingFejl, setHandlingFejl] = useState<Record<string, string>>({})

  const afgoer = async (id: string, approved: boolean) => {
    if (!onAfgoer) return
    setTravl(id)
    setHandlingFejl((f) => {
      if (!(id in f)) return f
      const naeste = { ...f }
      delete naeste[id]
      return naeste
    })
    try {
      const svar = await onAfgoer(id, approved)
      if (!svar.ok) {
        setHandlingFejl((f) => ({ ...f, [id]: svar.fejl || 'Svaret kunne ikke sendes.' }))
        return
      }
      onGenhent?.()
    } catch {
      setHandlingFejl((f) => ({ ...f, [id]: 'Svaret kunne ikke sendes. Prøv igen.' }))
    } finally {
      setTravl('')
    }
  }

  return (
    <View style={styles.root}>
      <View style={styles.header}>
        <Pressable accessibilityRole="button" accessibilityLabel="Luk" onPress={onClose} style={styles.circle}>
          <X size={20} color={tokens.color.fg1} strokeWidth={2} />
        </Pressable>
        <Text style={styles.title}>Aktivitet</Text>
        <View style={styles.circleGhost} />
      </View>
      <ScrollView contentContainerStyle={styles.body}>
        <Text style={styles.sektion}>Notifikationer</Text>
        {notifFejl ? (
          <View style={styles.card}>
            <Text style={styles.fejl}>Notifikationerne kunne ikke hentes.</Text>
            {onGenhent ? (
              <Pressable onPress={onGenhent} accessibilityRole="button">
                <Text style={styles.linkTekst}>Prøv igen</Text>
              </Pressable>
            ) : null}
          </View>
        ) : notifikationer === null || notifikationer === undefined ? (
          <Text style={styles.muted}>Henter notifikationer…</Text>
        ) : notifikationer.length === 0 ? (
          <Text style={styles.muted}>Ingen notifikationer — alt er klaret.</Text>
        ) : notifikationer.map((p) => (
          <View key={p.id} style={styles.card}>
            <Text style={styles.value}>{p.titel}</Text>
            {p.tekst ? <Text style={styles.muted}>{p.tekst}</Text> : null}
            {p.foraeldet ? (
              <Text style={styles.fejl}>Kunne ikke opdateres — det viste er sidste nyt.</Text>
            ) : null}
            {handlingFejl[p.id] ? <Text style={styles.fejl}>{handlingFejl[p.id]}</Text> : null}
            {p.kan_afgoere && onAfgoer ? (
              <View style={styles.knapRaekke}>
                <Pressable
                  accessibilityRole="button"
                  disabled={travl === p.id}
                  onPress={() => { void afgoer(p.id, true) }}
                >
                  <Text style={styles.linkTekst}>Godkend</Text>
                </Pressable>
                <Pressable
                  accessibilityRole="button"
                  disabled={travl === p.id}
                  onPress={() => { void afgoer(p.id, false) }}
                >
                  <Text style={styles.linkTekst}>Afvis</Text>
                </Pressable>
              </View>
            ) : null}
          </View>
        ))}

        <View style={styles.summary}>
          <Activity size={18} color={tokens.color.accent} strokeWidth={1.9} />
          <View style={styles.summaryText}>
            <Text style={styles.value}>{runs.length ? `${runs.length} aktive run` : 'Ingen aktive run'}</Text>
            <Text style={styles.muted}>{presenceSummary || 'Device routing ikke hentet endnu'}</Text>
          </View>
          <Text style={styles.badge}>{outboxCount} i kø</Text>
        </View>
        {runs.length ? runs.map((run) => (
          <View key={`${run.sessionId}:${run.runId}`} style={styles.card}>
            <View style={styles.cardHead}>
              <Clock3 size={15} color={tokens.color.fg2} strokeWidth={1.9} />
              <Text style={styles.cardMeta}>{run.status || 'working'}</Text>
            </View>
            <Text style={styles.runId}>{run.runId || 'ukendt run'}</Text>
            <Text style={styles.muted}>Session {run.sessionId}</Text>
          </View>
        )) : (
          <View style={styles.card}>
            <PackageCheck size={18} color={tokens.color.fg2} strokeWidth={1.8} />
            <Text style={styles.value}>Alt er roligt</Text>
            <Text style={styles.muted}>Når Jarvis arbejder i baggrunden, lander det her.</Text>
          </View>
        )}
      </ScrollView>
    </View>
  )
}

const makes = (tokens: Theme) => StyleSheet.create({
  root: { flex: 1, backgroundColor: tokens.color.bg0, paddingTop: 48 },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: tokens.spacing.md, paddingBottom: tokens.spacing.md },
  circle: { width: 40, height: 40, borderRadius: 20, alignItems: 'center', justifyContent: 'center', backgroundColor: tokens.color.bg2 },
  circleGhost: { width: 40, height: 40 },
  title: { color: tokens.color.fg1, fontSize: 17, fontWeight: '700' },
  body: { padding: tokens.spacing.lg, gap: tokens.spacing.sm, paddingBottom: tokens.spacing.xl },
  summary: { flexDirection: 'row', alignItems: 'center', gap: tokens.spacing.md, backgroundColor: tokens.color.bg1, borderRadius: tokens.radius.lg, padding: tokens.spacing.lg },
  summaryText: { flex: 1, gap: 3 },
  value: { color: tokens.color.fg1, fontWeight: '700' },
  muted: { color: tokens.color.fg3, fontSize: 13, lineHeight: 19 },
  badge: { color: tokens.color.accentText, fontSize: 12, fontWeight: '800' },
  card: { backgroundColor: tokens.color.bg2, borderRadius: tokens.radius.lg, padding: tokens.spacing.lg, gap: 7 },
  cardHead: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  cardMeta: { color: tokens.color.fg2, fontSize: 12, fontWeight: '800', textTransform: 'uppercase' },
  runId: { color: tokens.color.fg1, fontSize: 15, fontWeight: '700' },
  sektion: { color: tokens.color.fg3, fontSize: 12, fontWeight: '700', letterSpacing: 1, textTransform: 'uppercase' },
  fejl: { color: tokens.color.error, fontSize: 13, lineHeight: 19 },
  linkTekst: { color: tokens.color.accentText, fontSize: 13, fontWeight: '700' },
  knapRaekke: { flexDirection: 'row', gap: tokens.spacing.lg, marginTop: 2 }
})
