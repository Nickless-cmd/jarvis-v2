import { useEffect, useRef, useState } from 'react'
import { Image, Pressable, StyleSheet, Text, View } from 'react-native'
import { CameraView, useCameraPermissions } from 'expo-camera'
import { FlipHorizontal, RotateCcw, Send, Volume2, VolumeX, Zap } from 'lucide-react-native'
import { loadCameraPrefs, saveCameraPrefs, type CameraFlash, type CameraPrefs } from '../lib/cameraPrefs'
import { tokens } from '../theme/tokens'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'

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
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  const [permission, requestPermission] = useCameraPermissions()
  const [busy, setBusy] = useState(false)
  const [prefs, setPrefs] = useState<CameraPrefs>({ facing: 'back', flash: 'off', shutterSound: true })
  const [zoom, setZoom] = useState(0)
  const [preview, setPreview] = useState<CapturedPhoto | null>(null)
  const cam = useRef<CameraView>(null)

  useEffect(() => {
    void loadCameraPrefs().then(setPrefs)
  }, [])

  const updatePrefs = (patch: Partial<CameraPrefs>) => {
    setPrefs((cur) => {
      const next = { ...cur, ...patch }
      void saveCameraPrefs(next)
      return next
    })
  }

  const nextFlash = (flash: CameraFlash): CameraFlash =>
    flash === 'off' ? 'on' : flash === 'on' ? 'auto' : 'off'

  const take = async () => {
    if (busy || !cam.current) return
    setBusy(true)
    try {
      const photo = await cam.current.takePictureAsync({
        quality: 0.85,
        shutterSound: prefs.shutterSound
      } as { quality: number; shutterSound: boolean })
      if (photo?.uri) {
        setPreview({ uri: photo.uri, name: `foto-${photo.uri.split('/').pop() || 'billede.jpg'}`, mime: 'image/jpeg' })
      }
    } catch {
      /* behold kameraet åbent */
    } finally {
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

  if (preview) {
    return (
      <View style={styles.root}>
        <Image source={{ uri: preview.uri }} style={StyleSheet.absoluteFill} resizeMode="contain" />
        <View style={styles.topBar} pointerEvents="box-none">
          <Pressable accessibilityRole="button" accessibilityLabel="Tag om" onPress={() => setPreview(null)} hitSlop={10} style={styles.close}>
            <RotateCcw size={21} color="#fff" strokeWidth={2} />
          </Pressable>
          <Pressable accessibilityRole="button" accessibilityLabel="Luk" onPress={onClose} hitSlop={10} style={styles.close}>
            <Text style={styles.closeX}>×</Text>
          </Pressable>
        </View>
        <View style={styles.bottomBar} pointerEvents="box-none">
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Brug billede"
            disabled={busy}
            onPress={() => void onCapture(preview)}
            style={({ pressed }) => [styles.useButton, pressed ? styles.pressed : null]}
          >
            <Send size={19} color={tokens.color.bg0} strokeWidth={2.4} />
            <Text style={styles.useText}>Brug billede</Text>
          </Pressable>
        </View>
      </View>
    )
  }

  return (
    <View style={styles.root}>
      <CameraView
        ref={cam}
        style={StyleSheet.absoluteFill}
        facing={prefs.facing}
        flash={prefs.flash}
        zoom={zoom}
      />
      <View style={styles.topBar} pointerEvents="box-none">
        <View style={styles.toolRow}>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Skift kamera"
            onPress={() => updatePrefs({ facing: prefs.facing === 'back' ? 'front' : 'back' })}
            hitSlop={10}
            style={styles.close}
          >
            <FlipHorizontal size={21} color="#fff" strokeWidth={2} />
          </Pressable>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={`Flash ${prefs.flash}`}
            onPress={() => updatePrefs({ flash: nextFlash(prefs.flash) })}
            hitSlop={10}
            style={styles.close}
          >
            <Zap size={20} color={prefs.flash === 'off' ? '#fff' : tokens.color.accent} strokeWidth={2} />
          </Pressable>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={prefs.shutterSound ? 'Slå kameralyd fra' : 'Slå kameralyd til'}
            onPress={() => updatePrefs({ shutterSound: !prefs.shutterSound })}
            hitSlop={10}
            style={styles.close}
          >
            {prefs.shutterSound ? (
              <Volume2 size={20} color="#fff" strokeWidth={2} />
            ) : (
              <VolumeX size={20} color={tokens.color.accent} strokeWidth={2} />
            )}
          </Pressable>
        </View>
        <Pressable accessibilityRole="button" accessibilityLabel="Luk" onPress={onClose} hitSlop={10} style={styles.close}>
          <Text style={styles.closeX}>×</Text>
        </Pressable>
      </View>
      <View style={styles.bottomBar} pointerEvents="box-none">
        <View style={styles.zoomRow}>
          {[0, 0.25, 0.5].map((z) => (
            <Pressable
              key={z}
              accessibilityRole="button"
              accessibilityLabel={`Zoom ${z === 0 ? '1' : z === 0.25 ? '2' : '3'}x`}
              onPress={() => setZoom(z)}
              style={[styles.zoomChip, zoom === z ? styles.zoomChipOn : null]}
            >
              <Text style={[styles.zoomText, zoom === z ? styles.zoomTextOn : null]}>
                {z === 0 ? '1x' : z === 0.25 ? '2x' : '3x'}
              </Text>
            </Pressable>
          ))}
        </View>
        <Pressable accessibilityRole="button" accessibilityLabel="Tag billede" disabled={busy} onPress={() => void take()} style={[styles.shutter, busy ? styles.shutterBusy : null]}>
          <View style={styles.shutterInner} />
        </Pressable>
        {busy ? <Text style={styles.sending}>Tager billede…</Text> : null}
      </View>
    </View>
  )
}

const makestyles = (tokens: Theme) => StyleSheet.create({
  root: { flex: 1, backgroundColor: '#000' },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: tokens.spacing.xl, backgroundColor: tokens.color.bg0, gap: tokens.spacing.md },
  title: { color: tokens.color.fg1, fontSize: 22, fontWeight: '700' },
  msg: { color: tokens.color.fg2, textAlign: 'center', fontSize: 15, lineHeight: 22 },
  primary: { backgroundColor: tokens.color.accent, borderRadius: tokens.radius.md, paddingVertical: tokens.spacing.md, paddingHorizontal: tokens.spacing.xl },
  primaryText: { color: tokens.color.bg0, fontWeight: '700' },
  secondary: { padding: tokens.spacing.md },
  secondaryText: { color: tokens.color.fg2 },
  topBar: {
    position: 'absolute',
    top: 48,
    left: 0,
    right: 0,
    paddingHorizontal: tokens.spacing.lg,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between'
  },
  toolRow: { flexDirection: 'row', alignItems: 'center', gap: tokens.spacing.sm },
  close: { width: 40, height: 40, borderRadius: 20, alignItems: 'center', justifyContent: 'center', backgroundColor: 'rgba(0,0,0,0.5)' },
  closeX: { color: '#fff', fontSize: 18 },
  bottomBar: { position: 'absolute', bottom: 56, left: 0, right: 0, alignItems: 'center', gap: tokens.spacing.sm },
  zoomRow: { flexDirection: 'row', gap: tokens.spacing.sm, backgroundColor: 'rgba(0,0,0,0.45)', borderRadius: 999, padding: 4 },
  zoomChip: { minWidth: 44, paddingVertical: 8, alignItems: 'center', borderRadius: 999 },
  zoomChipOn: { backgroundColor: '#fff' },
  zoomText: { color: '#fff', fontWeight: '700', fontSize: 12 },
  zoomTextOn: { color: '#000' },
  shutter: { width: 76, height: 76, borderRadius: 38, borderWidth: 5, borderColor: '#fff', alignItems: 'center', justifyContent: 'center', backgroundColor: 'rgba(255,255,255,0.2)' },
  shutterBusy: { opacity: 0.5 },
  shutterInner: { width: 58, height: 58, borderRadius: 29, backgroundColor: '#fff' },
  sending: { color: '#fff', backgroundColor: 'rgba(0,0,0,0.5)', paddingHorizontal: tokens.spacing.md, paddingVertical: tokens.spacing.xs, borderRadius: tokens.radius.md },
  useButton: {
    minHeight: 52,
    flexDirection: 'row',
    alignItems: 'center',
    gap: tokens.spacing.sm,
    backgroundColor: tokens.color.accent,
    borderRadius: 999,
    paddingHorizontal: tokens.spacing.xl
  },
  useText: { color: tokens.color.bg0, fontWeight: '800' },
  pressed: { opacity: 0.7 }
})
