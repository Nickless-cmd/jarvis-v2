import { useEffect, useMemo, useRef, useState } from 'react'
import { Animated, Dimensions, Modal, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'
import { Activity, Boxes, Eye, MessageCircle, Search, Settings, SquarePen, SlidersHorizontal } from 'lucide-react-native'
import { formatRelativeDate } from '../lib/relativeDate'
import { HeartbeatDot } from './HeartbeatDot'
import type { ChatSession } from '../lib/types'
import { tokens } from '../theme/tokens'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'
import { TeamsPanel } from './TeamsPanel'

const PANEL_WIDTH = Math.min(360, Math.round(Dimensions.get('window').width * 0.86))

/**
 * Slide-in panel (åbnes via presence-ringen). Sessioner med søg + datoer,
 * "Ny samtale", og et tandhjul → Settings (hvor plugins/connectors + log ud
 * bor — spec §"Settings vs Plugins"). Lukker ved ring-tryk, valg, eller udenfor.
 */
/** En raekke i panelet: ikon + navn. Erstatter de navnloese ikoner i toppen —
 *  en oejenpaere og en kasse siger ikke hvad de goer, og man skulle trykke for
 *  at finde ud af det. */
function Felt({
  ikon, navn, onPress, testID,
}: { ikon: React.ReactNode; navn: string; onPress?: () => void; testID?: string }) {
  const styles = useStyles(makestyles)
  return (
    <Pressable
      testID={testID}
      accessibilityRole="button"
      accessibilityLabel={navn}
      onPress={onPress}
      style={({ pressed }) => [styles.felt, pressed ? styles.pressed : null]}
    >
      {ikon}
      <Text style={styles.feltTekst} numberOfLines={1}>{navn}</Text>
    </Pressable>
  )
}


export function SidePanel({
  open,
  onClose,
  displayName,
  sessions,
  activeId,
  onSelectSession,
  onNewSession,
  onOpenSettings,
  onOpenChatSettings,
  onOpenSenses,
  onOpenArtifacts,
  onOpenActivity,
  isOwner: inHousehold = false,
  workingIds = [],
  unreadIds = {},
  onFloatActive,
  bubbleSupported = false,
  config = null
}: {
  open: boolean
  onClose: () => void
  displayName: string
  sessions: ChatSession[]
  activeId: string | null
  onSelectSession: (sessionId: string) => void
  onNewSession: () => void
  onOpenSettings: () => void
  /** Indstillinger for den AKTIVE samtale — model, værktøjer, stemme. */
  onOpenChatSettings?: () => void
  /** Sansernes Arkiv. Kun sat for husstanden — men serveren er den ægte grænse. */
  onOpenSenses?: () => void
  onOpenArtifacts?: () => void
  onOpenActivity?: () => void
  /** Bor brugeren i hjemmet (owner eller partner)? Skjuler kun indgangen. */
  isOwner?: boolean
  workingIds?: string[]
  unreadIds?: Record<string, boolean>
  onFloatActive?: () => void
  bubbleSupported?: boolean
  config?: import('../lib/types').ApiConfig | null
}) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  const insets = useSafeAreaInsets()
  const translateX = useRef(new Animated.Value(-PANEL_WIDTH)).current
  const [mounted, setMounted] = useState(open)
  const [query, setQuery] = useState('')
  // Soegefeltet er foldet sammen som standard: det blev brugt sjaeldent og
  // fyldte en linje hele tiden. Ikonet i toppen folder det ud.
  const [soegAaben, setSoegAaben] = useState(false)
  // Initialer som R4's «BS»-cirkel. To bogstaver, aldrig flere.
  const initials = useMemo(
    () =>
      (displayName || 'J')
        .split(/\s+/)
        .filter(Boolean)
        .slice(0, 2)
        .map((w) => w[0]?.toUpperCase() ?? '')
        .join('') || 'J',
    [displayName]
  )

  useEffect(() => {
    if (open) setMounted(true)
    Animated.timing(translateX, {
      toValue: open ? 0 : -PANEL_WIDTH,
      duration: 220,
      useNativeDriver: true
    }).start(({ finished }) => {
      if (finished && !open) setMounted(false)
    })
  }, [open, translateX])

  const now = new Date()
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return sessions
    return sessions.filter((s) => (s.title || '').toLowerCase().includes(q))
  }, [sessions, query])

  if (!mounted) return null

  return (
    <Modal transparent visible={mounted} animationType="none" onRequestClose={onClose}>
      <View style={styles.overlay}>
        <Animated.View
          style={[
            styles.panel,
            { width: PANEL_WIDTH, paddingTop: insets.top + tokens.spacing.md, transform: [{ translateX }] }
          ]}
        >
          <View style={styles.headerRow}>
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Luk panel"
              onPress={onClose}
              hitSlop={8}
              style={styles.identity}
            >
              <View style={styles.ring}>
                <View style={styles.ringInner} />
              </View>
              <Text style={styles.name} numberOfLines={1}>
                {displayName || 'Jarvis'}
              </Text>
            </Pressable>
            {/* SØGNINGEN ER ET IKON HER, ikke et felt nedenfor. Feltet stod og
                fyldte en linje hele tiden for noget man goer sjaeldent, mens de
                fem genveje sad som ikoner uden navn — altsaa det modsatte af
                hvor tit de bruges. */}
            <Pressable
              testID="panel-search-toggle"
              accessibilityRole="button"
              accessibilityLabel={soegAaben ? 'Luk søgning' : 'Søg samtaler'}
              accessibilityState={{ expanded: soegAaben }}
              onPress={() => setSoegAaben((v) => !v)}
              hitSlop={8}
              style={styles.gear}
            >
              <Search size={18} color={soegAaben ? tokens.color.accent : tokens.color.fg2} strokeWidth={1.8} />
            </Pressable>
          </View>

          {soegAaben ? (
            <View style={styles.searchWrap}>
              <Search size={15} color={tokens.color.fg3} strokeWidth={1.8} />
              <TextInput
                autoFocus
                value={query}
                onChangeText={setQuery}
                placeholder="Søg samtaler"
                placeholderTextColor={tokens.color.fg3}
                style={styles.search}
              />
            </View>
          ) : null}

          {/* De fem som FELTER. Som ikoner sagde de ikke hvad de var — en oejenpaere
              og en kasse er ikke selvforklarende, og man skulle trykke for at finde
              ud af det. Et felt baerer sit eget navn. */}
          <View style={styles.felter}>
            {bubbleSupported && activeId ? (
              <Felt ikon={<MessageCircle size={17} color={tokens.color.fg2} strokeWidth={1.8} />}
                    navn="Flyt chat til boble" onPress={onFloatActive} />
            ) : null}
            {inHousehold && onOpenSenses ? (
              // Skjuler kun noget der ALLEREDE er lukket: /companion/senses
              // afviser alle uden for husstanden med 403 i auth-laget.
              // Forskellen på en dør og et gardin — her er gardinet.
              <Felt testID="open-senses"
                    ikon={<Eye size={18} color={tokens.color.fg2} strokeWidth={1.8} />}
                    navn="Sansernes Arkiv" onPress={onOpenSenses} />
            ) : null}
            {onOpenArtifacts ? (
              <Felt testID="open-artifacts"
                    ikon={<Boxes size={17} color={tokens.color.fg2} strokeWidth={1.8} />}
                    navn="Artifacts" onPress={onOpenArtifacts} />
            ) : null}
            {onOpenActivity ? (
              <Felt testID="open-activity"
                    ikon={<Activity size={17} color={tokens.color.fg2} strokeWidth={1.8} />}
                    navn="Aktivitet" onPress={onOpenActivity} />
            ) : null}
            {onOpenChatSettings ? (
              <Felt testID="open-chat-settings"
                    ikon={<SlidersHorizontal size={17} color={tokens.color.fg2} strokeWidth={1.8} />}
                    navn="Denne samtale" onPress={onOpenChatSettings} />
            ) : null}
          </View>

          <ScrollView contentContainerStyle={styles.body} keyboardShouldPersistTaps="handled">
            {filtered.length === 0 ? (
              <Text style={styles.empty}>{query ? 'Ingen match' : 'Ingen samtaler endnu'}</Text>
            ) : (
              filtered.map((session) => (
                <Pressable
                  key={session.id}
                  accessibilityRole="button"
                  onPress={() => onSelectSession(session.id)}
                  style={({ pressed }) => [
                    styles.sessionRow,
                    session.id === activeId ? styles.sessionActive : null,
                    pressed ? styles.pressed : null
                  ]}
                >
                  <Text style={styles.sessionTitle} numberOfLines={1}>
                    {session.title || 'Ny samtale'}
                  </Text>
                  <Text style={styles.sessionMeta}>
                    {formatRelativeDate(session.updated_at, now)} · {session.message_count ?? 0} beskeder
                  </Text>
                  <View style={styles.sessionIndicator}>
                    {workingIds.includes(session.id) ? (
                      <HeartbeatDot size={8} />
                    ) : unreadIds[session.id] ? (
                      <View style={styles.unreadDot} />
                    ) : null}
                  </View>
                </Pressable>
              ))
            )}
            <TeamsPanel config={config} onSelectSession={onSelectSession} />
          </ScrollView>

          {/* Indstillinger NEDERST. Den sad som et af seks ikoner i toppen, hvor
              den konkurrerede med fem genveje man bruger oftere. Nederst er den
              hvor man leder efter den — og fastlaast, saa den ikke ruller vaek. */}
          <Pressable
            testID="open-settings"
            accessibilityRole="button"
            accessibilityLabel="Indstillinger"
            onPress={onOpenSettings}
            style={({ pressed }) => [styles.felt, styles.feltBund, pressed ? styles.pressed : null]}
          >
            <Settings size={17} color={tokens.color.fg2} strokeWidth={1.8} />
            <Text style={styles.feltTekst}>Indstillinger</Text>
          </Pressable>

          {/* Bundlaget, målt på R4: en lilla pille med blyant + label i
              venstre side, og brugerens initial-cirkel til højre. Den flyder
              OVER listen frem for at ligge i den — så «ny samtale» altid er
              inden for rækkevidde, uanset hvor langt man har rullet. */}
          <View style={styles.dock} pointerEvents="box-none">
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Ny samtale"
              onPress={onNewSession}
              style={({ pressed }) => [styles.fab, pressed ? styles.pressed : null]}
            >
              <SquarePen size={18} color={tokens.color.bg0} strokeWidth={2} />
              <Text style={styles.fabText}>Ny samtale</Text>
            </Pressable>
            <View style={styles.avatar}>
              <Text style={styles.avatarText}>{initials}</Text>
            </View>
          </View>
        </Animated.View>

        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Luk panel"
          style={styles.scrim}
          onPress={onClose}
        />
      </View>
    </Modal>
  )
}

const makestyles = (tokens: Theme) => StyleSheet.create({
  overlay: { flex: 1, flexDirection: 'row' },
  // Målt i ChatGPT-appen (R4 + live 2026-09-02): panelet er SORT som resten af
  // appen, ikke en lysere flade, og der er hverken kant mod chatten eller
  // streg under overskriften. Dybden kommer alene af at chatten bag den
  // dæmpes. Det er dét der gør menuen rolig frem for kasse-agtig.
  scrim: { flex: 1, backgroundColor: 'rgba(0,0,0,0.6)' },
  panel: {
    backgroundColor: tokens.color.bg0
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: tokens.spacing.lg,
    paddingBottom: tokens.spacing.lg
  },
  identity: { flexDirection: 'row', alignItems: 'center', gap: tokens.spacing.sm, flexShrink: 1 },
  ring: {
    width: 28,
    height: 28,
    borderRadius: 14,
    borderWidth: 2,
    borderColor: tokens.color.accent,
    alignItems: 'center',
    justifyContent: 'center'
  },
  ringInner: { width: 10, height: 10, borderRadius: 5, backgroundColor: tokens.color.accent },
  name: { color: tokens.color.fg1, fontSize: 24, fontWeight: '700', flexShrink: 1 },
  gear: { width: 40, height: 40, alignItems: 'center', justifyContent: 'center', borderRadius: 20, backgroundColor: tokens.color.bg2 },
  felter: { paddingHorizontal: tokens.spacing.sm, paddingBottom: tokens.spacing.xs },
  felt: {
    flexDirection: 'row', alignItems: 'center', gap: tokens.spacing.sm,
    paddingVertical: 10, paddingHorizontal: tokens.spacing.sm, borderRadius: 10,
  },
  feltBund: {
    marginHorizontal: tokens.spacing.sm,
    borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: tokens.color.bg2,
    borderRadius: 0, paddingTop: 12,
  },
  feltTekst: { color: tokens.color.fg1, fontSize: 14, flexShrink: 1 },
  searchWrap: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: tokens.spacing.sm,
    margin: tokens.spacing.md,
    marginBottom: 0,
    paddingHorizontal: tokens.spacing.md,
    height: 40,
    borderRadius: tokens.radius.lg,
    backgroundColor: tokens.color.bg2
  },
  search: { flex: 1, color: tokens.color.fg1, fontSize: 15, padding: 0 },
  body: { padding: tokens.spacing.md, paddingBottom: tokens.spacing.xl },
  dock: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: tokens.spacing.lg,
    paddingBottom: tokens.spacing.lg,
    paddingTop: tokens.spacing.sm,
    gap: tokens.spacing.md
  },
  fab: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: tokens.spacing.sm,
    height: 48,
    paddingHorizontal: tokens.spacing.lg,
    borderRadius: tokens.radius.pill,
    backgroundColor: tokens.color.accent
  },
  fabText: { color: tokens.color.bg0, fontWeight: '700', fontSize: 15 },
  avatar: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: tokens.color.bg2,
    alignItems: 'center',
    justifyContent: 'center'
  },
  avatarText: { color: tokens.color.fg1, fontWeight: '700', fontSize: 14 },
  empty: { color: tokens.color.fg3, paddingVertical: tokens.spacing.sm },
  sessionRow: {
    paddingVertical: tokens.spacing.md,
    paddingHorizontal: tokens.spacing.sm,
    borderRadius: tokens.radius.md,
    borderBottomColor: tokens.color.line,
    borderBottomWidth: 1
  },
  sessionActive: { backgroundColor: tokens.color.bg3 },
  sessionIndicator: { position: 'absolute', right: tokens.spacing.sm, top: tokens.spacing.md, alignItems: 'center', justifyContent: 'center' },
  unreadDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: tokens.color.accent },
  sessionTitle: { color: tokens.color.fg1, fontWeight: '700' },
  sessionMeta: { color: tokens.color.fg3, marginTop: tokens.spacing.xs, fontSize: 12 },
  pressed: { opacity: 0.7 }
})
