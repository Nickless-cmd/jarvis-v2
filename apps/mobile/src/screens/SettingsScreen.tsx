import { useEffect, useState } from 'react'
import { ActivityIndicator, Linking, Modal, Pressable, ScrollView, StyleSheet, Switch, Text, View } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'
import { QrScanScreen } from './QrScanScreen'
import {
  getAccountMe,
  googleLinkStart,
  googleLoginResult,
  health,
  listConnectors,
  setConnectorEnabled,
  type GoogleLoginResult
} from '../lib/apiClient'
import type { AccountProfile, Connector } from '../lib/types'
import { useAuth } from '../state/AuthContext'
import { useConnectivity } from '../lib/useConnectivity'
import { tokens } from '../theme/tokens'
import { bubble } from '../lib/bubbleModule'
import { loadBubblePersist, saveBubblePersist } from '../lib/bubbleSetting'
import { loadPrecision, savePrecision, type LocationPrecision } from '../lib/location'

const CONN_LABEL: Record<string, string> = {
  connected: 'Forbundet til Jarvis ✓',
  reconnecting: 'Genopretter forbindelse…',
  offline: 'Offline'
}

const GOOGLE_LINK_POLL_ATTEMPTS = 75
const GOOGLE_LINK_POLL_MS = 2000

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

/** Fuld Settings-skærm (Claude-parity): konto · plugins/connectors · Google ·
 *  diagnostik · log ud. Plugins bor HER — ikke i hovedpanelet (spec §"Settings
 *  vs Plugins"). Vises som fuldskærms-modal fra panelets tandhjul. */
export function SettingsScreen({ onClose }: { onClose?: () => void }) {
  const { config, signOut, signInWithToken } = useAuth()
  const connectivity = useConnectivity(config ?? null)
  const [qrOpen, setQrOpen] = useState(false)
  const insets = useSafeAreaInsets()
  const [diagnostic, setDiagnostic] = useState('Ikke testet')
  const [googleBusy, setGoogleBusy] = useState(false)
  const [googleMessage, setGoogleMessage] = useState('')
  const [profile, setProfile] = useState<AccountProfile | null>(null)
  const [connectors, setConnectors] = useState<Connector[]>([])
  const [connectorsLoading, setConnectorsLoading] = useState(false)
  const [pendingId, setPendingId] = useState<string | null>(null)
  const [persistBubble, setPersistBubble] = useState(false)
  const [bubbleOk, setBubbleOk] = useState(false)
  const [locPrecision, setLocPrecision] = useState<LocationPrecision>('off')
  useEffect(() => { void bubble.isSupported().then(setBubbleOk) }, [])
  useEffect(() => { void loadBubblePersist().then(setPersistBubble) }, [])
  useEffect(() => { void loadPrecision().then(setLocPrecision) }, [])

  useEffect(() => {
    if (!config) return
    let alive = true
    getAccountMe(config).then((p) => { if (alive) setProfile(p) }).catch(() => undefined)
    setConnectorsLoading(true)
    listConnectors(config)
      .then((items) => { if (alive) setConnectors(items) })
      .catch(() => undefined)
      .finally(() => { if (alive) setConnectorsLoading(false) })
    return () => { alive = false }
  }, [config])

  const toggleConnector = async (c: Connector, next: boolean) => {
    if (!config) return
    setPendingId(c.id)
    setConnectors((cur) => cur.map((i) => (i.id === c.id ? { ...i, enabled: next } : i)))
    try {
      await setConnectorEnabled(config, c.id, next)
    } catch {
      setConnectors((cur) => cur.map((i) => (i.id === c.id ? { ...i, enabled: !next } : i)))
    } finally {
      setPendingId(null)
    }
  }

  const checkApi = async () => {
    if (!config) { setDiagnostic('Ikke forbundet'); return }
    try {
      setDiagnostic((await health(config.apiBaseUrl)) ? 'API svarer' : 'API svarer ikke')
    } catch {
      setDiagnostic('Kunne ikke kontakte API')
    }
  }

  const linkGoogle = async () => {
    if (!config || googleBusy) return
    setGoogleBusy(true)
    setGoogleMessage('Åbner Google...')
    try {
      const start = await googleLinkStart(config)
      if (!start.authorize_url || !start.nonce) {
        setGoogleMessage('Google-link er ikke konfigureret på serveren.')
        return
      }
      await Linking.openURL(start.authorize_url)
      setGoogleMessage('Godkend i browseren - venter...')
      for (let i = 0; i < GOOGLE_LINK_POLL_ATTEMPTS; i += 1) {
        const result = await googleLoginResult(config.apiBaseUrl, start.nonce).catch(
          (): GoogleLoginResult => ({ status: 'pending' })
        )
        if (result.status === 'ok') { setGoogleMessage('Google-konto forbundet'); return }
        if (result.status === 'error') { setGoogleMessage('Kunne ikke forbinde Google-konto.'); return }
        await sleep(GOOGLE_LINK_POLL_MS)
      }
      setGoogleMessage('Timeout - prøv igen.')
    } catch {
      setGoogleMessage('Kunne ikke nå serveren.')
    } finally {
      setGoogleBusy(false)
    }
  }

  const linked = !!profile?.google_linked

  return (
    <View style={[styles.root, { paddingTop: insets.top }]}>
      <View style={styles.header}>
        <Text style={styles.heading}>Indstillinger</Text>
        {onClose ? (
          <Pressable accessibilityRole="button" accessibilityLabel="Luk" onPress={onClose} hitSlop={8} style={styles.close}>
            <Text style={styles.closeX}>✕</Text>
          </Pressable>
        ) : null}
      </View>

      <ScrollView contentContainerStyle={styles.body}>
        {/* Konto */}
        <View style={styles.card}>
          <Text style={styles.cardEmail}>{profile?.email || config?.apiBaseUrl || 'Konto'}</Text>
          <View style={styles.badges}>
            {profile?.role ? <Text style={styles.badge}>{profile.role}</Text> : null}
            {profile?.tier ? <Text style={styles.badge}>{profile.tier}</Text> : null}
          </View>
          <Text style={[styles.connLine, connectivity === 'connected' ? styles.ok : connectivity === 'offline' ? styles.connBad : styles.connWarn]}>
            ● {CONN_LABEL[connectivity]}
          </Text>
        </View>

        {/* Plugins / connectors */}
        <Text style={styles.sectionTitle}>Tilsluttede tjenester</Text>
        <View style={styles.card}>
          {connectorsLoading ? (
            <ActivityIndicator color={tokens.color.accent} style={styles.loader} />
          ) : connectors.length === 0 ? (
            <Text style={styles.muted}>Ingen plugins</Text>
          ) : (
            connectors.map((c, idx) => (
              <View key={c.id} style={[styles.connectorRow, idx > 0 ? styles.divider : null]}>
                <View style={styles.connectorInfo}>
                  <Text style={styles.connectorName} numberOfLines={1}>{c.name}</Text>
                  <Text style={styles.connectorMeta} numberOfLines={1}>{c.connected ? 'Forbundet' : c.category}</Text>
                </View>
                <Switch
                  value={c.enabled}
                  disabled={pendingId === c.id || c.status === 'coming_soon'}
                  onValueChange={(next) => void toggleConnector(c, next)}
                  trackColor={{ true: tokens.color.accent, false: tokens.color.bg3 }}
                />
              </View>
            ))
          )}
        </View>

        {/* Google */}
        <Text style={styles.sectionTitle}>Google</Text>
        <View style={styles.card}>
          {linked ? (
            <Text style={styles.value}><Text style={styles.ok}>Google forbundet ✓</Text>  Du kan logge ind med Google.</Text>
          ) : (
            <Text style={styles.muted}>Forbind kontoen for Google-login fremover.</Text>
          )}
          <Pressable
            accessibilityRole="button"
            disabled={googleBusy}
            onPress={linkGoogle}
            style={[styles.secondaryButton, googleBusy ? styles.buttonDisabled : null]}
          >
            <Text style={styles.secondaryButtonText}>
              {googleBusy ? 'Forbinder...' : linked ? 'Forbind en anden Google-konto' : 'Forbind Google-konto'}
            </Text>
          </Pressable>
          {googleMessage ? <Text style={styles.message}>{googleMessage}</Text> : null}
        </View>

        {/* Diagnostik */}
        <Text style={styles.sectionTitle}>Diagnostik</Text>
        <View style={styles.card}>
          <Text style={styles.value}>{diagnostic}</Text>
          <Pressable accessibilityRole="button" onPress={checkApi} style={styles.secondaryButton}>
            <Text style={styles.secondaryButtonText}>Test API</Text>
          </Pressable>
        </View>

        {/* Forbind enhed (scan QR fra desktop) */}
        <Text style={styles.sectionTitle}>Forbind enhed</Text>
        <View style={styles.card}>
          <Text style={styles.value}><Text style={styles.ok}>Denne enhed er forbundet ✓</Text></Text>
          <Text style={styles.muted}>Skal du parre en ny telefon? Scan "Forbind mobil-app"-QR'en i Jarvis-desk.</Text>
          <Pressable accessibilityRole="button" onPress={() => setQrOpen(true)} style={styles.secondaryButton}>
            <Text style={styles.secondaryButtonText}>Scan QR</Text>
          </Pressable>
        </View>

        <Text style={styles.sectionTitle}>Lokation</Text>
        <View style={styles.card}>
          <Text style={styles.value}>Del lokation med Jarvis</Text>
          <View style={styles.locRow}>
            {(['off', 'city', 'precise'] as LocationPrecision[]).map((p) => (
              <Pressable
                key={p}
                accessibilityRole="button"
                onPress={() => { setLocPrecision(p); void savePrecision(p) }}
                style={[styles.locChip, locPrecision === p && styles.locChipOn]}
              >
                <Text style={[styles.locChipText, locPrecision === p && styles.locChipTextOn]}>
                  {p === 'off' ? 'Fra' : p === 'city' ? 'By' : 'Præcis'}
                </Text>
              </Pressable>
            ))}
          </View>
          <Text style={styles.muted}>
            {locPrecision === 'off'
              ? 'Jarvis kan ikke se hvor du er. Ingen GPS- eller IP-opslag.'
              : locPrecision === 'city'
                ? 'By-niveau via IP — fx "Svendborg". Batterivenligt, ingen GPS.'
                : 'Præcis (gade) via GPS — fx "Toftegårdsvej, Svendborg". Kun mens appen er åben.'}
          </Text>
        </View>

        {bubbleOk ? (
          <>
            <Text style={styles.sectionTitle}>Chatboble</Text>
            <View style={styles.card}>
              <View style={styles.bubbleRow}>
                <Text style={styles.value}>Vedvarende Jarvis-boble</Text>
                <Switch
                  value={persistBubble}
                  onValueChange={(on) => {
                    setPersistBubble(on)
                    void saveBubblePersist(on)
                    bubble.setPersistent(on, '', 'Jarvis')
                  }}
                  trackColor={{ true: tokens.color.accent, false: tokens.color.bg3 }}
                />
              </View>
              <Text style={styles.muted}>En flydende chat-head der altid er tilgængelig oven på andre apps.</Text>
            </View>
          </>
        ) : null}

        <Pressable accessibilityRole="button" onPress={() => void signOut()} style={styles.signOut}>
          <Text style={styles.signOutText}>Log ud</Text>
        </Pressable>
      </ScrollView>

      <Modal visible={qrOpen} animationType="slide" onRequestClose={() => setQrOpen(false)}>
        <QrScanScreen
          onClose={() => setQrOpen(false)}
          onPaired={async (url, token) => {
            setQrOpen(false)
            try { await signInWithToken(url, token) } catch { /* fejl vises ikke kritisk her */ }
          }}
        />
      </Modal>
    </View>
  )
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: tokens.color.bg0 },
  bubbleRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  locRow: { flexDirection: 'row', gap: 8, marginTop: 10, marginBottom: 8 },
  locChip: {
    paddingVertical: 8, paddingHorizontal: 16, borderRadius: 999,
    backgroundColor: tokens.color.bg3, borderWidth: 1, borderColor: tokens.color.bg3,
  },
  locChipOn: { backgroundColor: tokens.color.accent, borderColor: tokens.color.accent },
  locChipText: { color: tokens.color.fg2, fontWeight: '600' },
  locChipTextOn: { color: '#0d1117' },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: tokens.spacing.lg,
    paddingVertical: tokens.spacing.md,
    borderBottomColor: tokens.color.line,
    borderBottomWidth: 1
  },
  heading: { color: tokens.color.fg1, fontSize: 22, fontWeight: '700' },
  close: { width: 32, height: 32, alignItems: 'center', justifyContent: 'center' },
  closeX: { color: tokens.color.fg2, fontSize: 18 },
  body: { padding: tokens.spacing.lg, paddingBottom: tokens.spacing.xl, gap: tokens.spacing.sm },
  card: {
    backgroundColor: tokens.color.bg1,
    borderRadius: tokens.radius.lg,
    padding: tokens.spacing.md,
    borderWidth: 1,
    borderColor: tokens.color.line
  },
  cardEmail: { color: tokens.color.fg1, fontSize: 16, fontWeight: '700' },
  badges: { flexDirection: 'row', gap: tokens.spacing.sm, marginTop: tokens.spacing.sm },
  badge: {
    color: tokens.color.fg2,
    backgroundColor: tokens.color.bg3,
    fontSize: 12,
    fontWeight: '700',
    paddingHorizontal: tokens.spacing.sm,
    paddingVertical: 2,
    borderRadius: tokens.radius.sm,
    overflow: 'hidden'
  },
  sectionTitle: {
    color: tokens.color.fg3,
    fontSize: 12,
    fontWeight: '700',
    textTransform: 'uppercase',
    marginTop: tokens.spacing.md,
    marginBottom: tokens.spacing.xs
  },
  value: { color: tokens.color.fg1 },
  ok: { color: tokens.color.accent, fontWeight: '700' },
  connLine: { marginTop: tokens.spacing.sm, fontSize: 13, fontWeight: '700' },
  connBad: { color: tokens.color.error },
  connWarn: { color: tokens.color.warn },
  muted: { color: tokens.color.fg3 },
  loader: { paddingVertical: tokens.spacing.sm },
  connectorRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: tokens.spacing.sm,
    gap: tokens.spacing.md
  },
  divider: { borderTopColor: tokens.color.line, borderTopWidth: 1 },
  connectorInfo: { flexShrink: 1 },
  connectorName: { color: tokens.color.fg1, fontWeight: '600' },
  connectorMeta: { color: tokens.color.fg3, fontSize: 12, marginTop: 2 },
  secondaryButton: {
    minHeight: 40,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: tokens.radius.md,
    borderColor: tokens.color.line,
    borderWidth: 1,
    marginTop: tokens.spacing.md
  },
  secondaryButtonText: { color: tokens.color.fg1, fontWeight: '700' },
  buttonDisabled: { opacity: 0.6 },
  message: { color: tokens.color.fg3, marginTop: tokens.spacing.sm },
  signOut: {
    minHeight: 48,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: tokens.radius.md,
    backgroundColor: tokens.color.bg3,
    marginTop: tokens.spacing.xl
  },
  signOutText: { color: tokens.color.error, fontWeight: '700' }
})
