import { useCallback, useEffect, useState } from 'react'
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native'
import { useAuth } from '../state/AuthContext'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'
import { steerRun } from '../lib/apiClient'
import { fetchRunDetail } from '../lib/mcClient'
import type { McRun, McRunStep } from '../lib/mcTypes'

/**
 * R6 — opgave-tråden (dykke-niveauet).
 *
 * Spec 2026-09-02: «Ingen tabs, ingen sektioner — ren tråd. Godkendelser og
 * diffs må dukke op INDE i dette flow.» Det man lander i efter at trykke på
 * et opgave-kort.
 *
 * Bagenden fandtes allerede (/mc/runs/{run_id} → run + steps). Det der
 * manglede var dykke-niveauet: et tryk på et kort førte ingen steder hen, så
 * man kunne se AT noget kørte og aldrig hvad der faktisk skete undervejs.
 *
 * Komponisten er STEER-input til agenten, ikke en besked til Jarvis — derfor
 * «Arbejd på …» som placeholder frem for «Spørg Jarvis…». Den forskel er
 * hele grunden til at tråden ikke bare er en chat.
 */
export function TaskThreadScreen({
  run, topInset = 72, onClose,
}: {
  run: McRun
  topInset?: number
  onClose: () => void
}) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  const { config } = useAuth()
  const [steps, setSteps] = useState<McRunStep[]>([])
  const [detalje, setDetalje] = useState<McRun | null>(run)
  const [loading, setLoading] = useState(true)
  const [fejl, setFejl] = useState<string | null>(null)
  const [styring, setStyring] = useState('')
  const [sender, setSender] = useState(false)

  const load = useCallback(async () => {
    if (!config) return
    try {
      const d = await fetchRunDetail(config, run.run_id)
      setSteps(d.steps)
      if (d.run) setDetalje(d.run)
      setFejl(null)
    } catch (e) {
      // Tråden viser stadig det kort vi kom fra — en fejl her maa ikke
      // efterlade et tomt vindue uden kontekst.
      setFejl(e instanceof Error ? e.message : 'Kunne ikke hente tråden')
    } finally {
      setLoading(false)
    }
  }, [config, run.run_id])

  useEffect(() => { void load() }, [load])

  // Kun aktive runs kan styres. Et afsluttet run tager ikke imod mere.
  const aktiv = (detalje?.status ?? run.status) === 'running'

  const send = async () => {
    const tekst = styring.trim()
    if (!config || !tekst || !aktiv) return
    setSender(true)
    try {
      await steerRun(config, run.run_id, tekst)
      setStyring('')
      await load()
    } catch (e) {
      setFejl(e instanceof Error ? e.message : 'Kunne ikke sende')
    } finally {
      setSender(false)
    }
  }

  const r = detalje ?? run
  return (
    <View style={[styles.root, { paddingTop: topInset }]}>
      {/* Kontekst-pille: hvor kører det, og hvad er det. Spec R6. */}
      <View style={styles.pilleRaekke}>
        <Pressable onPress={onClose} accessibilityRole="button" style={styles.tilbage}>
          <Text style={styles.tilbageTekst}>‹</Text>
        </Pressable>
        <View style={styles.pille}>
          <Text style={styles.pilleTekst} numberOfLines={1}>
            {r.lane === 'visible' ? 'CheifOne' : r.lane} · {r.status}
          </Text>
        </View>
      </View>

      {loading ? (
        <View style={styles.midt}><ActivityIndicator color={tokens.color.accent} /></View>
      ) : (
        <ScrollView contentContainerStyle={styles.traad}>
          {r.text_preview ? <Text style={styles.agentTekst}>{r.text_preview}</Text> : null}

          {steps.length === 0 ? (
            <Text style={styles.tomt}>Ingen trin registreret for denne opgave endnu.</Text>
          ) : (
            steps.map((s, i) => (
              <View key={`${s.at}-${i}`} style={styles.trin}>
                <Text style={styles.trinTid}>{formatérTid(s.at)}</Text>
                <View style={styles.trinKrop}>
                  <Text style={styles.trinKind}>{s.kind}</Text>
                  {s.summary ? <Text style={styles.trinTekst}>{s.summary}</Text> : null}
                </View>
              </View>
            ))
          )}
          {fejl ? <Text style={styles.fejl}>{fejl}</Text> : null}
        </ScrollView>
      )}

      {/* Steer-komponist. Placeholder siger MASKINE, ikke «spørg» — det er en
          instruks til agenten, ikke en samtale. */}
      <View style={styles.komponist}>
        <TextInput
          style={styles.input}
          value={styring}
          onChangeText={setStyring}
          editable={aktiv && !sender}
          placeholder={aktiv ? 'Arbejd på CheifOne' : 'Opgaven er afsluttet'}
          placeholderTextColor={tokens.color.fg3}
        />
        <Pressable
          accessibilityRole="button"
          disabled={!aktiv || sender || !styring.trim()}
          onPress={() => void send()}
          style={[styles.sendKnap, (!aktiv || !styring.trim()) && styles.sendKnapSlukket]}
        >
          <Text style={styles.sendTekst}>{sender ? '…' : '↑'}</Text>
        </Pressable>
      </View>
    </View>
  )
}

/** «14:32» — tidspunktet betyder noget i en tidslinje, datoen sjældent. */
export function formatérTid(iso: string): string {
  try {
    const d = new Date(iso)
    if (Number.isNaN(d.getTime())) return ''
    return d.toLocaleTimeString('da-DK', { hour: '2-digit', minute: '2-digit' })
  } catch {
    return ''
  }
}

const makestyles = (tokens: Theme) => StyleSheet.create({
  root: { flex: 1, backgroundColor: tokens.color.bg0 },
  pilleRaekke: {
    flexDirection: 'row', alignItems: 'center', gap: tokens.spacing.sm,
    paddingHorizontal: tokens.spacing.lg, paddingBottom: tokens.spacing.sm,
  },
  tilbage: {
    width: 32, height: 32, borderRadius: 16, alignItems: 'center',
    justifyContent: 'center', backgroundColor: tokens.color.bg1,
  },
  tilbageTekst: { color: tokens.color.fg1, fontSize: 20, lineHeight: 22 },
  pille: {
    flex: 1, paddingHorizontal: tokens.spacing.md, paddingVertical: 6,
    borderRadius: 999, backgroundColor: tokens.color.bg1,
  },
  pilleTekst: { color: tokens.color.fg3, fontSize: 12 },
  midt: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  traad: { padding: tokens.spacing.lg, gap: tokens.spacing.md },
  agentTekst: { color: tokens.color.fg1, fontSize: 14, lineHeight: 20 },
  tomt: { color: tokens.color.fg3, fontSize: 13 },
  trin: { flexDirection: 'row', gap: tokens.spacing.md },
  trinTid: { color: tokens.color.fg3, fontSize: 11, width: 44, paddingTop: 2 },
  trinKrop: { flex: 1, gap: 2 },
  trinKind: { color: tokens.color.fg3, fontSize: 11, fontWeight: '600' },
  trinTekst: { color: tokens.color.fg1, fontSize: 13, lineHeight: 18 },
  fejl: { color: tokens.color.warn, fontSize: 12 },
  komponist: {
    flexDirection: 'row', alignItems: 'center', gap: tokens.spacing.sm,
    padding: tokens.spacing.lg, paddingTop: tokens.spacing.sm,
  },
  input: {
    flex: 1, borderRadius: 999, paddingHorizontal: tokens.spacing.md,
    paddingVertical: 10, backgroundColor: tokens.color.bg1, color: tokens.color.fg1,
    fontSize: 14,
  },
  sendKnap: {
    width: 36, height: 36, borderRadius: 18, alignItems: 'center',
    justifyContent: 'center', backgroundColor: tokens.color.accent,
  },
  sendKnapSlukket: { opacity: 0.35 },
  sendTekst: { color: '#fff', fontSize: 16, fontWeight: '700' },
})
