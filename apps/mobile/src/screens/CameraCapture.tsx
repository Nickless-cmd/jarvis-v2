import { useRef, useState } from 'react'
import { Pressable, StyleSheet, Text, View } from 'react-native'
import { CameraView, useCameraPermissions } from 'expo-camera'
import { tokens } from '../theme/tokens'

export interface CapturedPhoto {
  uri: string
  name: string
  mime: string
}

/**
 * In-app kamera til at tage billeder direkte i appen (foto-mode). Bruges fra
 * composeren → billedet uploades og følger med beskeden til Jarvis.
 * (Ingen native kamera-app — alt foregår i Jarvis-appen.)
 */
export function CameraCapture({
  onCapture,
  onClose
}: {
  onCapture: (photo: CapturedPhoto) => void | Promise<void>
  onClose: () => void
}) {
  const [permission, requestPermission] = useCameraPermissions()
  const [busy, setBusy] = useState(false)
  const cam = useRef<CameraView>(null)

  const take = async () => {
    if (busy || !cam.current) return
    setBusy(true)
    try {
      const photo = await cam.current.takePictureAsync({ quality: 0.7 })
      if (photo?.uri) {
        await onCapture({ uri: photo.uri, name: `foto-${photo.uri.split('/').pop() || 'billede.jpg'}`, mime: 'image/jpeg' })
      }
    } catch {
      setBusy(false)
    }
  }

  if (!permission) {
    return <View style={styles.center}><Text style={styles.msg}>Tjekker kamera-tilladelse…</Text></View>
  }

  if (!permission.granted) {
    return (
      <View style={styles.center}>
        <Text style={styles.title}>Kamera-adgang</Text>
        <Text style={styles.msg}>Appen skal bruge kameraet for at tage billeder til Jarvis.</Text>
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
      <CameraView ref={cam} style={StyleSheet.absoluteFill} facing="back" />
      <View style={styles.topBar} pointerEvents="box-none">
        <Pressable accessibilityRole="button" accessibilityLabel="Luk" onPress={onClose} hitSlop={10} style={styles.close}>
          <Text style={styles.closeX}>✕</Text>
        </Pressable>
      </View>
      <View style={styles.bottomBar} pointerEvents="box-none">
        <Pressable accessibilityRole="button" accessibilityLabel="Tag billede" disabled={busy} onPress={() => void take()} style={[styles.shutter, busy ? styles.shutterBusy : null]}>
          <View style={styles.shutterInner} />
        </Pressable>
        {busy ? <Text style={styles.sending}>Sender…</Text> : null}
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#000' },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: tokens.spacing.xl, backgroundColor: tokens.color.bg0, gap: tokens.spacing.md },
  title: { color: tokens.color.fg1, fontSize: 22, fontWeight: '700' },
  msg: { color: tokens.color.fg2, textAlign: 'center', fontSize: 15, lineHeight: 22 },
  primary: { backgroundColor: tokens.color.accent, borderRadius: tokens.radius.md, paddingVertical: tokens.spacing.md, paddingHorizontal: tokens.spacing.xl },
  primaryText: { color: tokens.color.bg0, fontWeight: '700' },
  secondary: { padding: tokens.spacing.md },
  secondaryText: { color: tokens.color.fg2 },
  topBar: { position: 'absolute', top: 48, right: 0, paddingHorizontal: tokens.spacing.lg },
  close: { width: 40, height: 40, borderRadius: 20, alignItems: 'center', justifyContent: 'center', backgroundColor: 'rgba(0,0,0,0.5)' },
  closeX: { color: '#fff', fontSize: 18 },
  bottomBar: { position: 'absolute', bottom: 56, left: 0, right: 0, alignItems: 'center', gap: tokens.spacing.sm },
  shutter: { width: 76, height: 76, borderRadius: 38, borderWidth: 5, borderColor: '#fff', alignItems: 'center', justifyContent: 'center', backgroundColor: 'rgba(255,255,255,0.2)' },
  shutterBusy: { opacity: 0.5 },
  shutterInner: { width: 58, height: 58, borderRadius: 29, backgroundColor: '#fff' },
  sending: { color: '#fff', backgroundColor: 'rgba(0,0,0,0.5)', paddingHorizontal: tokens.spacing.md, paddingVertical: tokens.spacing.xs, borderRadius: tokens.radius.md }
})
