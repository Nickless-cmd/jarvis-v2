import { useEffect, useState } from 'react'
import {
  ActivityIndicator,
  FlatList,
  Image,
  Modal,
  Pressable,
  StyleSheet,
  Text,
  View
} from 'react-native'
// expo-media-library 56 flyttede den nye API til rod-indgangen. Vi bruger den
// LEGACY-indgang bevidst: getAssetsAsync giver ét fladt kald til «de N nyeste
// billeder», hvilket er præcis det gitteret skal bruge. Den nye Query-API kan
// det samme, men koster mere kode for ingen gevinst her.
import * as MediaLibrary from 'expo-media-library/legacy'
import { Camera, Images, Upload, X } from 'lucide-react-native'
import { tokens } from '../theme/tokens'
import type { CapturedPhoto } from '../screens/CameraCapture'

/**
 * «Tilføj filer» — bygget efter ChatGPT-appens flade (set 2026-09-02).
 *
 * Den gamle var en lille bundmenu med tre tekstrækker. Deres er en HEL flade:
 * lukkekryds og titel øverst, «Upload filer» som én række, og derunder
 * «Seneste» som et gitter af faktiske miniaturer man kan trykke direkte på.
 *
 * Forskellen er ikke kosmetisk. I bundmenuen skal man vælge en KILDE først og
 * derefter finde billedet i en anden app. I gitteret ser man billedet med det
 * samme og er færdig i ét tryk — det er derfor deres føles hurtigere.
 */

const COLS = 2
const PAGE = 12

export function AttachMenu({
  visible,
  onCamera,
  onGallery,
  onPick,
  onClose
}: {
  visible: boolean
  onCamera: () => void
  onGallery: () => void
  /** Et tryk direkte på en miniature — springer systemvælgeren helt over. */
  onPick?: (photo: CapturedPhoto) => void
  onClose: () => void
}) {
  const [assets, setAssets] = useState<MediaLibrary.Asset[]>([])
  const [loading, setLoading] = useState(false)
  // null = ikke spurgt endnu. false = nægtet → vis knappen til systemvælgeren
  // i stedet for et tomt gitter, så fladen aldrig står og lyver om ingenting.
  const [granted, setGranted] = useState<boolean | null>(null)

  const load = async (ask: boolean) => {
    setLoading(true)
    try {
      // SPØRG IKKE af sig selv. Første udgave kaldte requestPermissionsAsync()
      // så snart fladen åbnede, og Android svarede med sin egen billedvælger
      // OVEN PÅ vores — man blev mødt af en systemdialog før man havde bedt om
      // noget. Nu læses tilladelsen tavst, og der spørges først når man trykker
      // på kortet der beder om det.
      const perm = ask
        ? await MediaLibrary.requestPermissionsAsync()
        : await MediaLibrary.getPermissionsAsync()
      setGranted(perm.granted)
      if (!perm.granted) return
      const page = await MediaLibrary.getAssetsAsync({
        first: PAGE,
        mediaType: ['photo'],
        sortBy: ['creationTime']
      })
      setAssets(page.assets)
    } catch {
      setGranted(false)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!visible) return
    void load(false)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visible])

  const choose = async (asset: MediaLibrary.Asset) => {
    if (!onPick) return onGallery()
    try {
      // localUri er den sti vi faktisk kan læse; asset.uri er en ph://-lignende
      // reference der ikke altid kan uploades direkte.
      const info = await MediaLibrary.getAssetInfoAsync(asset)
      onPick({
        uri: info.localUri || asset.uri,
        name: asset.filename || 'billede.jpg',
        mime: 'image/jpeg'
      })
    } catch {
      onGallery()
    }
  }

  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose} statusBarTranslucent>
      <View style={styles.root}>
        <View style={styles.header}>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Luk"
            onPress={onClose}
            style={({ pressed }) => [styles.circle, pressed && styles.pressed]}
          >
            <X size={20} color={tokens.color.fg1} strokeWidth={2} />
          </Pressable>
          <Text style={styles.title}>Tilføj filer</Text>
          <View style={styles.circleGhost} />
        </View>

        <Pressable
          accessibilityRole="button"
          onPress={onGallery}
          style={({ pressed }) => [styles.uploadRow, pressed && styles.pressed]}
        >
          <Upload size={22} color={tokens.color.fg1} strokeWidth={2} />
          <Text style={styles.uploadText}>Upload filer</Text>
        </Pressable>
        <View style={styles.divider} />

        <Text style={styles.section}>Seneste</Text>

        {loading ? (
          <View style={styles.center}><ActivityIndicator color={tokens.color.accent} /></View>
        ) : !granted ? (
          <View style={styles.center}>
            <Pressable
              testID="attach-camera"
              accessibilityRole="button"
              onPress={onCamera}
              style={({ pressed }) => [styles.wideCard, pressed && styles.pressed]}
            >
              <Camera size={24} color={tokens.color.fg1} strokeWidth={1.8} />
              <Text style={styles.wideText}>Tag billede</Text>
            </Pressable>
            <Pressable
              testID="attach-grant"
              accessibilityRole="button"
              onPress={() => void load(true)}
              style={({ pressed }) => [styles.wideCard, pressed && styles.pressed]}
            >
              <Images size={24} color={tokens.color.fg1} strokeWidth={1.8} />
              <Text style={styles.wideText}>Vis mine seneste billeder</Text>
            </Pressable>
            <Pressable
              accessibilityRole="button"
              onPress={onGallery}
              style={({ pressed }) => [styles.wideCard, pressed && styles.pressed]}
            >
              <Upload size={24} color={tokens.color.fg1} strokeWidth={1.8} />
              <Text style={styles.wideText}>Vælg via systemets vælger</Text>
            </Pressable>
          </View>
        ) : (
          <FlatList
            // Kamera-kortet er en RÆKKE I DATAEN, ikke en liste-header. Som
            // header spændte det over begge kolonner og brød gitteret; som
            // første celle står det side om side med det nyeste billede —
            // præcis som Google Drive-kortet gør i referencen.
            data={[{ kind: 'camera' as const }, ...assets.map((a) => ({ kind: 'asset' as const, asset: a }))]}
            numColumns={COLS}
            keyExtractor={(it) => (it.kind === 'camera' ? 'camera' : it.asset.id)}
            columnWrapperStyle={styles.row}
            contentContainerStyle={styles.grid}
            renderItem={({ item }) =>
              item.kind === 'camera' ? (
                <Pressable
                  testID="attach-camera"
                  accessibilityRole="button"
                  onPress={onCamera}
                  style={({ pressed }) => [styles.cameraCard, pressed && styles.pressed]}
                >
                  <Camera size={26} color={tokens.color.fg1} strokeWidth={1.8} />
                  <Text style={styles.cameraText}>Tag billede</Text>
                </Pressable>
              ) : (
                <Pressable
                  accessibilityRole="button"
                  accessibilityLabel={item.asset.filename}
                  onPress={() => void choose(item.asset)}
                  style={({ pressed }) => [styles.thumbWrap, pressed && styles.pressed]}
                >
                  <Image source={{ uri: item.asset.uri }} style={styles.thumb} />
                </Pressable>
              )
            }
          />
        )}
      </View>
    </Modal>
  )
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: tokens.color.bg0, paddingTop: 48 },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: tokens.spacing.md,
    paddingBottom: tokens.spacing.md
  },
  circle: {
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: tokens.color.bg2
  },
  circleGhost: { width: 40, height: 40 },
  title: { color: tokens.color.fg1, fontSize: 17, fontWeight: '700' },
  uploadRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: tokens.spacing.md,
    paddingHorizontal: tokens.spacing.lg,
    paddingVertical: tokens.spacing.md
  },
  uploadText: { color: tokens.color.fg1, fontSize: 17 },
  divider: { height: StyleSheet.hairlineWidth, backgroundColor: tokens.color.line, marginHorizontal: tokens.spacing.lg },
  section: {
    color: tokens.color.fg1,
    fontSize: 15,
    fontWeight: '700',
    paddingHorizontal: tokens.spacing.lg,
    paddingTop: tokens.spacing.lg,
    paddingBottom: tokens.spacing.sm
  },
  grid: { paddingHorizontal: tokens.spacing.md, paddingBottom: tokens.spacing.xl },
  row: { gap: tokens.spacing.sm, marginBottom: tokens.spacing.sm },
  cameraCard: {
    flex: 1,
    height: 190,
    borderRadius: tokens.radius.lg,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: tokens.color.line,
    alignItems: 'center',
    justifyContent: 'center',
    gap: tokens.spacing.sm
  },
  cameraText: { color: tokens.color.fg2, fontSize: 15 },
  thumbWrap: { flex: 1, height: 190, borderRadius: tokens.radius.lg, overflow: 'hidden', backgroundColor: tokens.color.bg2 },
  thumb: { width: '100%', height: '100%' },
  center: { flex: 1, alignItems: 'stretch', justifyContent: 'flex-start', padding: tokens.spacing.lg, gap: tokens.spacing.sm },
  wideCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: tokens.spacing.md,
    paddingHorizontal: tokens.spacing.lg,
    paddingVertical: tokens.spacing.lg,
    borderRadius: tokens.radius.lg,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: tokens.color.line
  },
  wideText: { color: tokens.color.fg1, fontSize: 16 },
  pressed: { opacity: 0.7 }
})
