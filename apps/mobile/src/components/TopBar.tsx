import { ActivityIndicator, Pressable, StyleSheet, View } from 'react-native'
import { ArrowLeft, Menu, MoreVertical } from 'lucide-react-native'
import { SegmentedControl } from './SegmentedControl'
import { ContextRing } from './ContextRing'
import { tokens } from '../theme/tokens'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'
import type { ContextUsage } from '../lib/apiClient'

export type AppMode = 'snak' | 'arbejde'

interface Props {
  mode: AppMode
  onModeChange: (next: AppMode) => void
  onMenu: () => void
  onSync: () => void
  pendingWork?: boolean
  syncing?: boolean
  /** Code-fladen: venstre felt bliver en tilbage-pil og segmentet siger «Code». */
  kodeTilstand?: boolean
  onBack?: () => void
  /** Kontekst-fyld. Ringen tegner sig selv væk når den er null. */
  kontekst?: ContextUsage | null
  /** Åbner tre-prik menuen. Opdatér bor derinde nu. */
  onMereMenu?: () => void
}

/**
 * Appens øverste bjælke — geometrien er MÅLT i ChatGPT-appen på Bjørns enhed.
 *
 * DENSITETEN ER 2,625 — IKKE 3,0. Telefonen har `Override density: 420` mod
 * de fysiske 480 (display-zoom, en helt almindelig indstilling). Første forsøg
 * regnede med 3,0 og blev derfor 14 % for lille hele vejen: jeg satte 150 dp
 * og målte 394 px tilbage, hvilket kun går op ved 2,625. Måler man px i et
 * skærmbillede, skal man kende enhedens FAKTISKE densitet — ikke panelets.
 *
 *   venstre cirkel   115 px  →  44 dp
 *   segmented        452 px  → 172 dp, centrum x=539,5 = SKÆRMENS MIDTE
 *   kantmargen        37 px  →  14 dp
 *
 * BEVIDST AFVIGELSE: cirklerne er sat til 40 dp og bjælken gjort lavere, fordi
 * Bjørn bad om «et nummer mindre». Segmentets bredde og centrering følger
 * stadig målingen — det var dét der sad skævt.
 *
 * Kontrollen er ABSOLUT centreret, ikke flex-strakt mellem cirklerne. Med flex
 * bliver midten et gennemsnit af de to knappers bredde — og den var synligt
 * skæv.
 */
const CIRCLE = 40
const EDGE = 14
const SEGMENT_W = 172

export function TopBar({
  mode, onModeChange, onMenu, onSync, pendingWork, syncing,
  kodeTilstand, onBack, kontekst, onMereMenu,
}: Props) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  // I code-fladen er venstre felt en VEJ UD, ikke en menu. At lade det blive
  // ved med at aabne sessionslisten ville efterlade code-fladen uden udgang
  // paa den plads oejet leder efter den.
  const tilbage = Boolean(kodeTilstand && onBack)
  return (
    <View style={styles.bar}>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={tilbage ? 'Tilbage til chat' : 'Menu'}
        onPress={tilbage ? onBack : onMenu}
        hitSlop={8}
        style={styles.circle}
        testID="topbar-venstre"
      >
        {tilbage
          ? <ArrowLeft size={21} color={tokens.color.fg1} strokeWidth={2} />
          : <Menu size={21} color={tokens.color.fg1} strokeWidth={2} />}
      </Pressable>

      <View pointerEvents="box-none" style={styles.centerWrap}>
        <View style={styles.center}>
          <SegmentedControl<AppMode>
            options={[
              // «Code» naar man staar i code-fladen. Samme plads, samme
              // kontakt - men et navn der siger hvor man er.
              { value: 'snak', label: kodeTilstand ? 'Code' : 'Snak' },
              { value: 'arbejde', label: 'Arbejde', badge: pendingWork }
            ]}
            value={mode}
            onChange={onModeChange}
          />
        </View>
      </View>

      {/* Hoejre felt: ringen FOERST, saa prikkerne - i samme felt. Ringen er
          det man laeser, prikkerne er det man trykker. Star de hver for sig
          bliver bjaelken til tre knapper der ligner hinanden. */}
      <Pressable
        accessibilityRole="button"
        accessibilityLabel="Mere"
        accessibilityState={{ busy: Boolean(syncing) }}
        onPress={onMereMenu ?? onSync}
        hitSlop={8}
        style={[styles.circle, kontekst ? styles.pille : null]}
        testID="topbar-mere"
      >
        {syncing ? (
          <ActivityIndicator size="small" color={tokens.color.fg1} />
        ) : (
          <>
            <ContextRing brug={kontekst ?? null} />
            <MoreVertical size={20} color={tokens.color.fg1} strokeWidth={2} />
          </>
        )}
      </Pressable>
    </View>
  )
}

const makestyles = (tokens: Theme) => StyleSheet.create({
  bar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: EDGE,
    paddingVertical: 6,
    // Halvgennemsigtig: tråden ANES bagved frem for at blive klippet af
    // en massiv bjælke. Det er dét der giver følelsen af ét sammenhængende
    // rum i stedet for tre etager.
    backgroundColor: tokens.color.scrim
  },
  // Fylder hele bjælken og lader tryk gå igennem til cirklerne udenfor.
  centerWrap: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    alignItems: 'center',
    justifyContent: 'center'
  },
  center: { width: SEGMENT_W },
  // Feltet vokser til en pille naar ringen er der. Segmentet er ABSOLUT
  // centreret, saa den maalte geometri i midten staar stille alligevel.
  pille: {
    width: undefined,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 9,
    borderRadius: CIRCLE / 2,
  },
  circle: {
    width: CIRCLE,
    height: CIRCLE,
    borderRadius: CIRCLE / 2,
    backgroundColor: tokens.color.bgFloat,
    ...tokens.elevation,
    alignItems: 'center',
    justifyContent: 'center'
  }
})
