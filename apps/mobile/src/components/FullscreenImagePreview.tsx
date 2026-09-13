import { useEffect, useMemo, useRef, useState } from 'react'
import {
  Animated,
  Modal,
  PanResponder,
  Pressable,
  StyleSheet,
  Text,
  View
} from 'react-native'
import { AuthImage, hentTilCache } from './AuthImage'
import { useAuth } from '../state/AuthContext'
import { Download, X } from 'lucide-react-native'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'
import { filnavnMedEndelse, gemTilGalleriet, type GemUdfald } from '../lib/gemBillede'
import { begraensForskydning, begraensSkala, fingerAfstand } from '../lib/zoom'

/**
 * Billedet i fuld skærm — med knib, panorering og «gem i galleriet».
 *
 * ## Hvad der var galt (målt 13/9-2026 på Bjørns telefon)
 *
 * Visningen kunne ÉT: vise billedet og lukke igen. Bjørn kunne ikke gemme det
 * og ikke komme tættere på det. Et billede man har lavet, og som man ikke kan
 * få ud af appen, er halvt leveret.
 *
 * ## Hvorfor knib ikke bare er et bibliotek
 *
 * `react-native-gesture-handler` og `reanimated` giver det færdigt — men de er
 * NATIVE moduler, og appen har dem ikke. Et nyt native modul kræver en ny
 * APK-version, babel-ændringer og en risikovurdering for en funktion der kan
 * regnes ud i hånden. Her bruges `PanResponder` og `Animated`, som er i React
 * Native selv. Regningen ligger i `lib/zoom.ts`.
 */
export function FullscreenImagePreview({
  visible,
  uri,
  title,
  filnavn,
  mime,
  onClose
}: {
  visible: boolean
  uri: string
  title?: string
  /** Filnavnet billedet gemmes under. Galleriet afgør typen ud fra endelsen. */
  filnavn?: string
  mime?: string
  onClose: () => void
}) {
  const tokens = useTheme()
  const styles = useStyles(makes)
  // Token'et hentes HER frem for at komme ind som `headers`: den prop gik til
  // en <Image> der tabte den. Se AuthImage.
  const { config } = useAuth()

  const [gemmer, setGemmer] = useState(false)
  const [status, setStatus] = useState<GemUdfald | null>(null)

  const skala = useRef(new Animated.Value(1)).current
  const forskydning = useRef(new Animated.ValueXY({ x: 0, y: 0 })).current

  // Tallene holdes VED SIDEN AF de animerede værdier: et Animated.Value kan
  // ikke læses synkront, og både klampningen og panoreringen skal bruge den
  // aktuelle skala MIDT i en bevægelse — ikke den fra sidste render.
  const skalaNu = useRef(1)
  const forskydningNu = useRef({ x: 0, y: 0 })
  const startAfstand = useRef(0)
  const startSkala = useRef(1)
  const sidstePunkt = useRef<{ x: number; y: number } | null>(null)
  const ramme = useRef({ bredde: 0, hoejde: 0 })
  const sidsteTap = useRef(0)
  const flyttede = useRef(false)

  function saetForskydning(p: { x: number; y: number }) {
    const klemt = begraensForskydning(p, skalaNu.current, ramme.current)
    forskydningNu.current = klemt
    forskydning.setValue(klemt)
  }

  function nulstil() {
    skalaNu.current = 1
    forskydningNu.current = { x: 0, y: 0 }
    skala.setValue(1)
    forskydning.setValue({ x: 0, y: 0 })
  }

  // Lukket visning skal åbne uzoomet næste gang. Komponenten afmonteres ganske
  // vist af sin kalder, men den må ikke være afhængig af det for at være rigtig.
  useEffect(() => {
    if (visible) return
    skalaNu.current = 1
    forskydningNu.current = { x: 0, y: 0 }
    skala.setValue(1)
    forskydning.setValue({ x: 0, y: 0 })
    setStatus(null)
  }, [visible, skala, forskydning])

  const pan = useMemo(
    () =>
      PanResponder.create({
        // IKKE `true`. Et gribbetag her ville stjæle trykket fra luk- og
        // gem-knapperne, og de ville holde op med at virke — den slags fejl
        // man først finder på en telefon.
        onStartShouldSetPanResponder: () => false,
        // To fingre: altid vores. Én finger: kun når der ER zoomet — ellers
        // skal et swipe kunne lukke/scrolles videre til det der ligger bag.
        onMoveShouldSetPanResponder: (_e, g) =>
          g.numberActiveTouches === 2 || (skalaNu.current > 1 && g.numberActiveTouches === 1),
        onPanResponderGrant: (e) => {
          const t = e.nativeEvent.touches
          startAfstand.current = fingerAfstand(t)
          startSkala.current = skalaNu.current
          sidstePunkt.current = t.length === 1 ? { x: t[0]!.pageX, y: t[0]!.pageY } : null
          flyttede.current = false
        },
        onPanResponderMove: (e) => {
          const t = e.nativeEvent.touches
          flyttede.current = true

          if (t.length >= 2) {
            const d = fingerAfstand(t)
            if (startAfstand.current <= 0) {
              // Første bevægelse med to fingre: her sættes ankeret, så skalaen
              // måles fra den afstand brugeren faktisk lagde fingrene i.
              startAfstand.current = d
              startSkala.current = skalaNu.current
              return
            }
            const s = begraensSkala(startSkala.current * (d / startAfstand.current))
            skalaNu.current = s
            skala.setValue(s)
            // Løftes den ene finger, skal panoreringen have et NYT anker —
            // ellers springer billedet det stykke fingeren allerede har flyttet.
            sidstePunkt.current = null
            return
          }

          if (t.length === 1 && skalaNu.current > 1) {
            if (startAfstand.current > 0) {
              startAfstand.current = 0
              sidstePunkt.current = null
            }
            const p = { x: t[0]!.pageX, y: t[0]!.pageY }
            if (sidstePunkt.current) {
              saetForskydning({
                x: forskydningNu.current.x + (p.x - sidstePunkt.current.x),
                y: forskydningNu.current.y + (p.y - sidstePunkt.current.y)
              })
            }
            sidstePunkt.current = p
          }
        },
        onPanResponderRelease: () => {
          startAfstand.current = 0
          sidstePunkt.current = null
          saetForskydning(forskydningNu.current)

          // Dobbelt-tryk nulstiller. Kun når fingeren IKKE flyttede sig —
          // ellers ville et hurtigt panorering ende med et spring tilbage.
          if (flyttede.current) {
            sidsteTap.current = 0
            return
          }
          const nu = Date.now()
          if (nu - sidsteTap.current < 300) {
            nulstil()
            sidsteTap.current = 0
            return
          }
          sidsteTap.current = nu
        },
        onPanResponderTerminate: () => {
          startAfstand.current = 0
          sidstePunkt.current = null
        }
      }),
    // Én gang: gribbetaget holder sine egne tal i refs og skal ikke genskabes
    // midt i en bevægelse.
    []
  )

  async function gem() {
    if (!config || gemmer) return
    setGemmer(true)
    setStatus(null)
    try {
      // Filnavnet bærer ENDELSEN — uden den ved galleriet ikke hvad det får,
      // og `hentTilCache` navngiver sin kopi efter netop det navn.
      const navn = filnavnMedEndelse(filnavn || title, mime)
      const lokal = await hentTilCache(config, uri, navn)
      setStatus(await gemTilGalleriet(lokal))
    } catch {
      setStatus('fejlet')
    }
    setGemmer(false)
  }

  return (
    <Modal visible={visible} transparent={false} animationType="fade" onRequestClose={onClose}>
      <View style={styles.root}>
        <View style={styles.top}>
          <Text style={styles.title} numberOfLines={1}>{title || 'Billede'}</Text>
          <View style={styles.knapper}>
            <Pressable
              testID="attachment-download"
              accessibilityRole="button"
              accessibilityLabel="Gem billedet i galleriet"
              accessibilityState={{ disabled: gemmer }}
              disabled={gemmer}
              onPress={() => { void gem() }}
              hitSlop={12}
              style={styles.knap}
            >
              <Download size={20} color={tokens.color.fg1} strokeWidth={2} />
            </Pressable>
            <Pressable
              testID="attachment-close"
              accessibilityRole="button"
              accessibilityLabel="Luk preview"
              onPress={onClose}
              hitSlop={12}
              style={styles.knap}
            >
              <X size={22} color={tokens.color.fg1} strokeWidth={2} />
            </Pressable>
          </View>
        </View>

        {status ? (
          <Text
            testID="attachment-download-status"
            style={[styles.status, status === 'gemt' ? styles.statusOk : styles.statusFejl]}
          >
            {status === 'gemt'
              ? 'Gemt i galleriet'
              : status === 'afvist'
                ? 'Galleriet blev ikke tilladt — billedet er ikke gemt'
                : 'Kunne ikke gemme billedet'}
          </Text>
        ) : null}

        <View
          testID="attachment-scene"
          style={styles.scene}
          onLayout={(e) => {
            const { width, height } = e.nativeEvent.layout
            ramme.current = { bredde: width, hoejde: height }
          }}
          {...pan.panHandlers}
        >
          {config ? (
            // To lag, ikke ét: yderst forskydningen (i skærmens punkt) og
            // inderst skalaen. I én transform ville rækkefølgen afgøre om
            // forskydningen blev skaleret med — og det er ikke til at se på
            // koden hvilken vej React Native læser listen.
            <Animated.View style={[styles.lag, { transform: forskydning.getTranslateTransform() }]}>
              <Animated.View style={[styles.lag, { transform: [{ scale: skala }] }]}>
                <AuthImage
                  testID="attachment-fullscreen-image"
                  config={config}
                  url={uri}
                  navn={uri}
                  resizeMode="contain"
                  style={styles.image}
                />
              </Animated.View>
            </Animated.View>
          ) : null}
        </View>
      </View>
    </Modal>
  )
}

const makes = (tokens: Theme) => StyleSheet.create({
  root: { flex: 1, backgroundColor: tokens.color.bg0 },
  top: {
    minHeight: 64,
    paddingHorizontal: tokens.spacing.lg,
    paddingTop: tokens.spacing.lg,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: tokens.spacing.md
  },
  title: { flex: 1, color: tokens.color.fg1, fontSize: 15, fontWeight: '700' },
  knapper: { flexDirection: 'row', alignItems: 'center', gap: tokens.spacing.sm },
  knap: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: tokens.color.bg2,
    alignItems: 'center',
    justifyContent: 'center'
  },
  status: { paddingHorizontal: tokens.spacing.lg, paddingBottom: tokens.spacing.sm, fontSize: 13 },
  statusOk: { color: tokens.color.fg1 },
  statusFejl: { color: tokens.color.fg3 },
  // `overflow: hidden` holder det panorerede billede inde i rammen, så det
  // ikke maler oven på topbjælken.
  scene: { flex: 1, overflow: 'hidden' },
  lag: { flex: 1, width: '100%' },
  image: { flex: 1, width: '100%', backgroundColor: tokens.color.bg0 }
})
