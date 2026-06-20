import { useEffect, useMemo, useRef, useState } from 'react'
import { Animated, Dimensions, Modal, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'
import { formatRelativeDate } from '../lib/relativeDate'
import { HeartbeatDot } from './HeartbeatDot'
import type { ChatSession } from '../lib/types'
import { tokens } from '../theme/tokens'

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
  workingIds = [],
  unreadIds = {},
  onFloatActive,
  bubbleSupported = false
}: {
  open: boolean
  onClose: () => void
  displayName: string
  sessions: ChatSession[]
  activeId: string | null
  onSelectSession: (sessionId: string) => void
  onNewSession: () => void
  onOpenSettings: () => void
  workingIds?: string[]
  unreadIds?: Record<string, boolean>
  onFloatActive?: () => void
  bubbleSupported?: boolean
}) {
  const insets = useSafeAreaInsets()
  const translateX = useRef(new Animated.Value(-PANEL_WIDTH)).current
  const [mounted, setMounted] = useState(open)
  const [query, setQuery] = useState('')

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
            <Pressable
              accessibilityRole="button"
              onPress={onNewSession}
              style={({ pressed }) => [styles.newButton, pressed ? styles.pressed : null]}
            >
              <Text style={styles.newButtonText}>+ Ny samtale</Text>
            </Pressable>

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
          </ScrollView>
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
  scrim: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)' },
  panel: {
    backgroundColor: tokens.color.bg1,
    borderRightColor: tokens.color.line,
    borderRightWidth: 1
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: tokens.spacing.md,
    paddingBottom: tokens.spacing.md,
    borderBottomColor: tokens.color.line,
    borderBottomWidth: 1
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
  name: { color: tokens.color.fg1, fontSize: 16, fontWeight: '700', flexShrink: 1 },
  gear: { width: 36, height: 36, alignItems: 'center', justifyContent: 'center', borderRadius: 18, backgroundColor: tokens.color.bg3 },
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
  newButton: {
    minHeight: 44,
    borderRadius: tokens.radius.md,
    backgroundColor: tokens.color.accent,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: tokens.spacing.md
  },
  newButtonText: { color: tokens.color.bg0, fontWeight: '700' },
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
