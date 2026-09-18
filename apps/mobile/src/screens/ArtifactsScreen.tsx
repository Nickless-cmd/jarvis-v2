import { useEffect, useState } from 'react'
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native'
import { FileCode2, MessageSquare, X } from 'lucide-react-native'
import { fetchArtifacts, type ArtifactList } from '../lib/artifactsApi'
import { formatRelativeTime } from '../lib/relativeDate'
import { useAuth } from '../state/AuthContext'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'
import { StatusState } from '../components/StatusState'

/**
 * Artefakter — de filer Jarvis har skrevet og rettet i den valgte mappe, på
 * tværs af samtaler. Samme kilde og samme række som desk' artefakt-menu.
 *
 * Før viste skærmen kort med et «Preview»-ikon uden preview, en dato der kun
 * sagde «Senest», og ingen mulighed for at komme videre. Nu: navn, mappe,
 * grøn/rød linjetal, hvornår og hvor mange gange — og et tryk åbner samtalen
 * hvor filen sidst blev rørt.
 */
export function ArtifactsScreen({
  onClose,
  root = 'repo',
  onOpenSession,
  initial = null,
}: {
  onClose: () => void
  /** Mappen code står i — sti på din maskine, eller en navngiven server-rod. */
  root?: string
  onOpenSession?: (sessionId: string) => void
  initial?: ArtifactList | null
}) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  const { config } = useAuth()
  const [liste, setListe] = useState<ArtifactList | null>(initial)

  useEffect(() => {
    if (!config || initial) return
    let alive = true
    void fetchArtifacts(config, root).then((next) => { if (alive) setListe(next) })
    return () => { alive = false }
  }, [config, initial, root])

  const nu = new Date()

  return (
    <View style={styles.root}>
      <View style={styles.header}>
        <Pressable accessibilityRole="button" accessibilityLabel="Luk" onPress={onClose} style={styles.circle}>
          <X size={20} color={tokens.color.fg1} strokeWidth={2} />
        </Pressable>
        <View style={styles.titelBlok}>
          <Text style={styles.title}>Artefakter</Text>
          {liste?.ok ? (
            <Text style={styles.undertitel} numberOfLines={1}>
              {(liste.root.split('/').filter(Boolean).pop() || liste.root)} · {liste.total} filer
            </Text>
          ) : null}
        </View>
        <View style={styles.circleGhost} />
      </View>

      {liste === null ? (
        <StatusState title="Henter artefakter" loading />
      ) : !liste.ok ? (
        // En fejl er IKKE det samme som tomt. Den gamle skærm viste «Ingen
        // artifacts endnu» for begge, og derfor blev en brækket rute aldrig set.
        <StatusState title="Kunne ikke hente artefakter" detail={liste.error || 'Ukendt fejl'} />
      ) : liste.items.length === 0 ? (
        <StatusState title="Ingen artefakter endnu." detail="Jarvis har ikke skrevet eller rettet noget i denne mappe." />
      ) : (
        <ScrollView contentContainerStyle={styles.list}>
          {liste.items.map((a) => {
            const dele = a.rel.split('/')
            const navn = dele.pop() || a.rel
            const mappe = dele.join('/')
            const meta = [
              formatRelativeTime(a.lastAt, nu),
              a.edits > 1 ? `${a.edits} ændringer` : '',
              a.sessionCount > 1 ? `i ${a.sessionCount} samtaler` : '',
            ].filter(Boolean).join(' · ')
            return (
              <Pressable
                key={a.path}
                testID={`artefakt-${a.rel}`}
                accessibilityRole={onOpenSession && a.sessionId ? 'button' : 'text'}
                accessibilityLabel={`${a.rel}${a.sessionTitle ? `, fra ${a.sessionTitle}` : ''}`}
                onPress={() => { if (onOpenSession && a.sessionId) onOpenSession(a.sessionId) }}
                style={({ pressed }) => [styles.raekke, pressed ? styles.pressed : null]}
              >
                <FileCode2 size={18} color={tokens.color.fg3} strokeWidth={1.8} />
                <View style={styles.tekst}>
                  <View style={styles.navnRaekke}>
                    <Text style={styles.navn} numberOfLines={1}>{navn}</Text>
                    {a.add > 0 ? <Text style={[styles.tal, styles.plus]}>+{a.add}</Text> : null}
                    {a.del > 0 ? <Text style={[styles.tal, styles.minus]}>−{a.del}</Text> : null}
                  </View>
                  {mappe ? <Text style={styles.sti} numberOfLines={1}>{mappe}</Text> : null}
                  <Text style={styles.meta} numberOfLines={1}>{meta}</Text>
                  {a.sessionTitle ? (
                    <View style={styles.samtale}>
                      <MessageSquare size={11} color={tokens.color.fg3} strokeWidth={1.8} />
                      <Text style={styles.samtaleTekst} numberOfLines={1}>{a.sessionTitle}</Text>
                    </View>
                  ) : null}
                </View>
              </Pressable>
            )
          })}
          {/* Så et tal der ser lavt ud kan kontrolleres — intet vindue skjuler halen. */}
          <Text style={styles.fod}>Læst ud af {liste.scanned} svar</Text>
        </ScrollView>
      )}
    </View>
  )
}

const makestyles = (tokens: Theme) => StyleSheet.create({
  root: { flex: 1, backgroundColor: tokens.color.bg0, paddingTop: 48 },
  header: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    paddingHorizontal: tokens.spacing.md, paddingBottom: tokens.spacing.md
  },
  circle: {
    width: 40, height: 40, borderRadius: 20, alignItems: 'center',
    justifyContent: 'center', backgroundColor: tokens.color.bg2
  },
  circleGhost: { width: 40, height: 40 },
  titelBlok: { flex: 1, alignItems: 'center' },
  title: { color: tokens.color.fg1, fontSize: 17, fontWeight: '700' },
  undertitel: { color: tokens.color.fg3, fontSize: 12, marginTop: 2 },
  list: { paddingHorizontal: tokens.spacing.md, paddingBottom: tokens.spacing.xl, gap: 2 },
  raekke: {
    flexDirection: 'row', alignItems: 'flex-start', gap: tokens.spacing.sm,
    paddingVertical: 10, paddingHorizontal: tokens.spacing.sm, borderRadius: tokens.radius.md
  },
  pressed: { backgroundColor: tokens.color.bg2 },
  tekst: { flex: 1, minWidth: 0, gap: 2 },
  navnRaekke: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  navn: { color: tokens.color.fg1, fontSize: 15, fontWeight: '600', flexShrink: 1 },
  // Samme semantik som diff-tallene i tråden: ok/error, ikke accent.
  tal: { fontSize: 12.5, fontWeight: '600', fontVariant: ['tabular-nums'] },
  plus: { color: tokens.color.ok },
  minus: { color: tokens.color.error },
  sti: { color: tokens.color.fg3, fontSize: 12.5 },
  meta: { color: tokens.color.fg3, fontSize: 12 },
  samtale: { flexDirection: 'row', alignItems: 'center', gap: 4, marginTop: 1 },
  samtaleTekst: { color: tokens.color.fg3, fontSize: 12, flexShrink: 1 },
  fod: { color: tokens.color.fg3, fontSize: 11, textAlign: 'center', marginTop: tokens.spacing.md }
})
