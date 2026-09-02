import { useEffect, useMemo, useRef, useState } from 'react'
import { Animated, Dimensions, Modal, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'
import { Eye, SquarePen } from 'lucide-react-native'
import { formatRelativeDate } from '../lib/relativeDate'
import { HeartbeatDot } from './HeartbeatDot'
import type { ChatSession } from '../lib/types'
import { tokens } from '../theme/tokens'
import { TeamsPanel } from './TeamsPanel'

const PANEL_WIDTH = Math.min(360, Math.round(Dimensions.get('window').width * 0.86))

/**
 * Slide-in panel (åbnes via presence-ringen). Sessioner med søg + datoer,
 * "Ny samtale", og et tandhjul → Settings (hvor plugins/connectors + log ud
 * bor — spec §"Settings vs Plugins"). Lukker ved ring-tryk, valg, eller udenfor.
 */
export function SidePanel({
  open,
  onClose,
  displayName,
  sessions,
  activeId,
  onSelectSession,
  onNewSession,
  onOpenSettings,
  onOpenSenses,
  isOwner = false,
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
  /** Sansernes Arkiv. Kun sat for owner — men serveren er den ægte grænse. */
  onOpenSenses?: () => void
  isOwner?: boolean
  workingIds?: string[]
  unreadIds?: Record<string, boolean>
  onFloatActive?: () => void
  bubbleSupported?: boolean
  config?: import('../lib/types').ApiConfig | null
}) {
  const insets = useSafeAreaInsets()
  const translateX = useRef(new Animated.Value(-PANEL_WIDTH)).current
  const [mounted, setMounted] = useState(open)
  const [query, setQuery] = useState('')
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
            {bubbleSupported && activeId ? (
              <Pressable
                accessibilityRole="button"
                accessibilityLabel="Flyt chat til boble"
                onPress={onFloatActive}
                hitSlop={8}
                style={styles.gear}
              >
                <Text style={styles.gearIcon}>🫧</Text>
              </Pressable>
            ) : null}
            {isOwner && onOpenSenses ? (
              // Skjuler kun noget der ALLEREDE er lukket: /companion/senses
              // afviser enhver anden rolle med 403 i auth-laget. Forskellen på
              // en dør og et gardin — her er gardinet.
              <Pressable
                testID="open-senses"
                accessibilityRole="button"
                accessibilityLabel="Sansernes Arkiv"
                onPress={onOpenSenses}
                hitSlop={8}
                style={styles.gear}
              >
                <Eye size={19} color={tokens.color.fg2} strokeWidth={1.8} />
              </Pressable>
            ) : null}
            <Pressable accessibilityRole="button" accessibilityLabel="Indstillinger" onPress={onOpenSettings} hitSlop={8} style={styles.gear}>
              <Text style={styles.gearIcon}>⚙</Text>
            </Pressable>
          </View>

          <View style={styles.searchWrap}>
            <Text style={styles.searchIcon}>🔍</Text>
            <TextInput
              value={query}
              onChangeText={setQuery}
              placeholder="Søg samtaler"
              placeholderTextColor={tokens.color.fg3}
              style={styles.search}
            />
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

const styles = StyleSheet.create({
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
  gearIcon: { fontSize: 16 },
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
  searchIcon: { fontSize: 13 },
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
