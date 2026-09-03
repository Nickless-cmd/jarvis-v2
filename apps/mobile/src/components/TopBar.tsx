import { ActivityIndicator, Pressable, StyleSheet, View } from 'react-native'
import { Menu, RefreshCw } from 'lucide-react-native'
import { SegmentedControl } from './SegmentedControl'
import { tokens } from '../theme/tokens'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'

export type AppMode = 'snak' | 'arbejde'

interface Props {
  mode: AppMode
  onModeChange: (next: AppMode) => void
  onMenu: () => void
  onSync: () => void
  pendingWork?: boolean
  syncing?: boolean
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

export function TopBar({ mode, onModeChange, onMenu, onSync, pendingWork, syncing }: Props) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  return (
    <View style={styles.bar}>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel="Menu"
        onPress={onMenu}
        hitSlop={8}
        style={styles.circle}
      >
        <Menu size={21} color={tokens.color.fg1} strokeWidth={2} />
      </Pressable>

      <View pointerEvents="box-none" style={styles.centerWrap}>
        <View style={styles.center}>
          <SegmentedControl<AppMode>
            options={[
              { value: 'snak', label: 'Snak' },
              { value: 'arbejde', label: 'Arbejde', badge: pendingWork }
            ]}
            value={mode}
            onChange={onModeChange}
          />
        </View>
      </View>

      <Pressable
        accessibilityRole="button"
        accessibilityLabel="Synkronisér"
        accessibilityState={{ busy: Boolean(syncing) }}
        onPress={onSync}
        hitSlop={8}
        style={styles.circle}
        testID="sync-button"
      >
        {syncing ? (
          <ActivityIndicator size="small" color={tokens.color.fg1} />
        ) : (
          <RefreshCw size={20} color={tokens.color.fg1} strokeWidth={2} />
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
