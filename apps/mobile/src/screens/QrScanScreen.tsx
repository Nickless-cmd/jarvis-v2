import { useRef, useState } from 'react'
import { Pressable, StyleSheet, Text, View } from 'react-native'
import { CameraView, useCameraPermissions, type BarcodeScanningResult } from 'expo-camera'
import { redeemPairingCode } from '../lib/apiClient'
import { parsePairingPayload } from '../lib/pairing'
import { tokens } from '../theme/tokens'

/**
 * QR-pairing-scanner. Scanner QR'en fra desktop-appen ({url, code}), indløser
 * koden mod /api/auth/pair/redeem → friskt device-bundet token, og logger ind.
 * (Phase 4: mobil↔desktop-pairing — fundamentet for at Jarvis kan køre tools
 * på brugerens egen maskine via operator-broen.)
 */
export function QrScanScreen({
  onPaired,
  onClose
}: {
  onPaired: (url: string, token: string) => void | Promise<void>
  onClose: () => void
}) {
  const [permission, requestPermission] = useCameraPermissions()
  const [status, setStatus] = useState('Ret kameraet mod QR-koden i Jarvis-desk')
  const [busy, setBusy] = useState(false)
  const handled = useRef(false)

  const onScan = async (result: BarcodeScanningResult) => {
    if (handled.current || busy) return
    const parsed = parsePairingPayload(result.data)
    if (!parsed) {
      setStatus('QR-koden kunne ikke læses — prøv igen')
      return
    }
    handled.current = true
    setBusy(true)
    setStatus('Forbinder…')
    try {
      const res = await redeemPairingCode(parsed.url, parsed.code)
      if (res.status === 'ok' && res.token) {
        await onPaired(parsed.url, res.token)
        return
      }
      setStatus(res.error === 'invalid_or_expired' ? 'Koden er udløbet — lav en ny i Jarvis-desk' : 'Kunne ikke forbinde')
    } catch {
      setStatus('Kunne ikke nå serveren')
    } finally {
      setBusy(false)
      // tillad nyt forsøg efter en kort pause
      setTimeout(() => { handled.current = false }, 1500)
    }
  }

  if (!permission) {
    return (
      <View style={styles.center}>
        <Text style={styles.msg}>Tjekker kamera-tilladelse…</Text>
      </View>
    )
  }

  if (!permission.granted) {
    return (
      <View style={styles.center}>
        <Text style={styles.title}>Kamera-adgang</Text>
        <Text style={styles.msg}>Companion'en skal bruge kameraet for at scanne QR-koden fra Jarvis-desk.</Text>
        <Pressable accessibilityRole="button" onPress={() => void requestPermission()} style={styles.primary}>
          <Text style={styles.primaryText}>Tillad kamera</Text>
        </Pressable>
        <Pressable accessibilityRole="button" onPress={onClose} style={styles.secondary}>
          <Text style={styles.secondaryText}>Annullér</Text>
        </Pressable>
      </View>
    )
  }

  return (
    <View style={styles.root}>
      <CameraView
        style={StyleSheet.absoluteFill}
        facing="back"
        barcodeScannerSettings={{ barcodeTypes: ['qr'] }}
        onBarcodeScanned={(r) => void onScan(r)}
      />
      <View style={styles.overlay} pointerEvents="box-none">
        <View style={styles.topBar}>
          <Pressable accessibilityRole="button" accessibilityLabel="Luk" onPress={onClose} hitSlop={10} style={styles.close}>
            <Text style={styles.closeX}>✕</Text>
          </Pressable>
        </View>
        <View style={styles.frame} />
        <Text style={styles.status}>{status}</Text>
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#000' },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: tokens.spacing.xl, backgroundColor: tokens.color.bg0, gap: tokens.spacing.md },
  title: { color: tokens.color.fg1, fontSize: 22, fontWeight: '700' },
  msg: { color: tokens.color.fg2, textAlign: 'center', fontSize: 15, lineHeight: 22 },
  primary: { backgroundColor: tokens.color.accent, borderRadius: tokens.radius.md, paddingVertical: tokens.spacing.md, paddingHorizontal: tokens.spacing.xl, alignItems: 'center' },
  primaryText: { color: tokens.color.bg0, fontWeight: '700' },
  secondary: { padding: tokens.spacing.md },
  secondaryText: { color: tokens.color.fg2 },
  overlay: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  topBar: { position: 'absolute', top: 48, left: 0, right: 0, alignItems: 'flex-end', paddingHorizontal: tokens.spacing.lg },
  close: { width: 40, height: 40, borderRadius: 20, alignItems: 'center', justifyContent: 'center', backgroundColor: 'rgba(0,0,0,0.5)' },
  closeX: { color: '#fff', fontSize: 18 },
  frame: { width: 240, height: 240, borderRadius: 24, borderWidth: 3, borderColor: tokens.color.accent, backgroundColor: 'transparent' },
  status: { color: '#fff', marginTop: tokens.spacing.xl, fontSize: 15, textAlign: 'center', paddingHorizontal: tokens.spacing.xl, backgroundColor: 'rgba(0,0,0,0.4)', paddingVertical: tokens.spacing.sm, borderRadius: tokens.radius.md }
})
