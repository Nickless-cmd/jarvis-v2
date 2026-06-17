import { useEffect, useRef, useState } from 'react'
import {
  ActivityIndicator,
  Animated,
  Dimensions,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  View
} from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'
import { listConnectors, setConnectorEnabled } from '../lib/apiClient'
import type { ApiConfig, ChatSession, Connector } from '../lib/types'
import { tokens } from '../theme/tokens'

const PANEL_WIDTH = Math.min(360, Math.round(Dimensions.get('window').width * 0.86))

/**
 * Slide-in panel der åbnes ved tryk på Jarvis-ringen. Indeholder:
 * sessioner (fortsæt i en anden), plugins (per-bruger — samme som desktop
 * når man er logget ind som samme bruger) og log ud. Lukkes ved at trykke
 * på ringen igen, vælge en session, eller trykke udenfor.
 */
export function SidePanel({
  open,
  onClose,
  config,
  displayName,
  sessions,
  activeId,
  onSelectSession,
  onNewSession,
  onSignOut
}: {
  open: boolean
  onClose: () => void
  config: ApiConfig
  displayName: string
  sessions: ChatSession[]
  activeId: string | null
  onSelectSession: (sessionId: string) => void
  onNewSession: () => void
  onSignOut: () => void
}) {
  const insets = useSafeAreaInsets()
  const translateX = useRef(new Animated.Value(-PANEL_WIDTH)).current
  const [mounted, setMounted] = useState(open)
  const [connectors, setConnectors] = useState<Connector[]>([])
  const [connectorsLoading, setConnectorsLoading] = useState(false)
  const [pendingId, setPendingId] = useState<string | null>(null)

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

  useEffect(() => {
    if (!open) return
    let alive = true
    setConnectorsLoading(true)
    listConnectors(config)
      .then((items) => {
        if (alive) setConnectors(items)
      })
      .catch(() => undefined)
      .finally(() => {
        if (alive) setConnectorsLoading(false)
      })
    return () => {
      alive = false
    }
  }, [open, config])

  const toggleConnector = async (connector: Connector, next: boolean) => {
    setPendingId(connector.id)
    setConnectors((current) =>
      current.map((item) => (item.id === connector.id ? { ...item, enabled: next } : item))
    )
    try {
      await setConnectorEnabled(config, connector.id, next)
    } catch {
      // Roll back on failure so the switch reflects server truth.
      setConnectors((current) =>
        current.map((item) => (item.id === connector.id ? { ...item, enabled: !next } : item))
      )
    } finally {
      setPendingId(null)
    }
  }

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
            <View style={styles.identity}>
              <View style={styles.ring}>
                <View style={styles.ringInner} />
              </View>
              <Text style={styles.name} numberOfLines={1}>
                {displayName || 'Jarvis'}
              </Text>
            </View>
            <Pressable accessibilityRole="button" onPress={onSignOut} style={styles.signOut}>
              <Text style={styles.signOutText}>Log ud</Text>
            </Pressable>
          </View>

          <ScrollView contentContainerStyle={styles.body} keyboardShouldPersistTaps="handled">
            <Pressable
              accessibilityRole="button"
              onPress={onNewSession}
              style={({ pressed }) => [styles.newButton, pressed ? styles.pressed : null]}
            >
              <Text style={styles.newButtonText}>+ Ny samtale</Text>
            </Pressable>

            <Text style={styles.sectionTitle}>Sessioner</Text>
            {sessions.length === 0 ? (
              <Text style={styles.empty}>Ingen samtaler endnu</Text>
            ) : (
              sessions.map((session) => (
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
                  <Text style={styles.sessionMeta}>{session.message_count ?? 0} beskeder</Text>
                </Pressable>
              ))
            )}

            <Text style={styles.sectionTitle}>Plugins</Text>
            {connectorsLoading ? (
              <ActivityIndicator color={tokens.color.accent} style={styles.loader} />
            ) : connectors.length === 0 ? (
              <Text style={styles.empty}>Ingen plugins</Text>
            ) : (
              connectors.map((connector) => (
                <View key={connector.id} style={styles.connectorRow}>
                  <View style={styles.connectorInfo}>
                    <Text style={styles.connectorName} numberOfLines={1}>
                      {connector.name}
                    </Text>
                    <Text style={styles.connectorMeta} numberOfLines={1}>
                      {connector.connected ? 'Forbundet' : connector.category}
                    </Text>
                  </View>
                  <Switch
                    value={connector.enabled}
                    disabled={pendingId === connector.id || connector.status === 'coming_soon'}
                    onValueChange={(next) => void toggleConnector(connector, next)}
                    trackColor={{ true: tokens.color.accent, false: tokens.color.bg3 }}
                  />
                </View>
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
  overlay: {
    flex: 1,
    flexDirection: 'row'
  },
  scrim: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)'
  },
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
  identity: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: tokens.spacing.sm,
    flexShrink: 1
  },
  ring: {
    width: 28,
    height: 28,
    borderRadius: 14,
    borderWidth: 2,
    borderColor: tokens.color.accent,
    alignItems: 'center',
    justifyContent: 'center'
  },
  ringInner: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: tokens.color.accent
  },
  name: {
    color: tokens.color.fg1,
    fontSize: 16,
    fontWeight: '700',
    flexShrink: 1
  },
  signOut: {
    paddingVertical: tokens.spacing.xs,
    paddingHorizontal: tokens.spacing.md,
    borderRadius: tokens.radius.md,
    backgroundColor: tokens.color.bg3
  },
  signOutText: {
    color: tokens.color.fg1,
    fontWeight: '700'
  },
  body: {
    padding: tokens.spacing.md,
    paddingBottom: tokens.spacing.xl
  },
  newButton: {
    minHeight: 44,
    borderRadius: tokens.radius.md,
    backgroundColor: tokens.color.accent,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: tokens.spacing.md
  },
  newButtonText: {
    color: tokens.color.bg0,
    fontWeight: '700'
  },
  sectionTitle: {
    color: tokens.color.fg3,
    fontSize: 12,
    fontWeight: '700',
    textTransform: 'uppercase',
    marginTop: tokens.spacing.md,
    marginBottom: tokens.spacing.sm
  },
  empty: {
    color: tokens.color.fg3,
    paddingVertical: tokens.spacing.sm
  },
  loader: {
    paddingVertical: tokens.spacing.md
  },
  sessionRow: {
    paddingVertical: tokens.spacing.md,
    paddingHorizontal: tokens.spacing.sm,
    borderRadius: tokens.radius.md,
    borderBottomColor: tokens.color.line,
    borderBottomWidth: 1
  },
  sessionActive: {
    backgroundColor: tokens.color.bg3
  },
  sessionTitle: {
    color: tokens.color.fg1,
    fontWeight: '700'
  },
  sessionMeta: {
    color: tokens.color.fg3,
    marginTop: tokens.spacing.xs,
    fontSize: 12
  },
  connectorRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: tokens.spacing.sm,
    gap: tokens.spacing.md
  },
  connectorInfo: {
    flexShrink: 1
  },
  connectorName: {
    color: tokens.color.fg1,
    fontWeight: '600'
  },
  connectorMeta: {
    color: tokens.color.fg3,
    fontSize: 12,
    marginTop: 2
  },
  pressed: {
    opacity: 0.7
  }
})
