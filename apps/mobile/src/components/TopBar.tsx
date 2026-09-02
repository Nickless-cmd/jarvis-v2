import { ActivityIndicator, Pressable, StyleSheet, View } from 'react-native'
import { Menu, RefreshCw } from 'lucide-react-native'
import { SegmentedControl } from './SegmentedControl'
import { tokens } from '../theme/tokens'

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
 * Appens øverste bjælke — geometrien er MÅLT i ChatGPT-appen (1080 px, 3×):
 *
 *   venstre cirkel   x 37..152    → 38 dp, 12 dp fra kanten
 *   segmented        x 314..765   → 150 dp bred, centrum x=539,5 = SKÆRMENS MIDTE
 *   højre cirkel     x 926..1042  → 39 dp, 13 dp fra højre kant
 *
 * Kontrollen er derfor ABSOLUT centreret, ikke flex-strakt mellem cirklerne.
 * Med flex bliver midten et gennemsnit af de to knappers bredde — og den var
 * synligt skæv. Absolut centrering er den eneste måde midten faktisk bliver
 * midten på.
 */
const CIRCLE = 38
const EDGE = 12
const SEGMENT_W = 150

export function TopBar({ mode, onModeChange, onMenu, onSync, pendingWork, syncing }: Props) {
  return (
    <View style={styles.bar}>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel="Menu"
        onPress={onMenu}
        hitSlop={8}
        style={styles.circle}
      >
        <Menu size={20} color={tokens.color.fg1} strokeWidth={2} />
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
          <RefreshCw size={19} color={tokens.color.fg1} strokeWidth={2} />
        )}
      </Pressable>
    </View>
  )
}

const styles = StyleSheet.create({
  bar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: EDGE,
    paddingVertical: 10,
    backgroundColor: tokens.color.bg0
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
    backgroundColor: tokens.color.bg2,
    alignItems: 'center',
    justifyContent: 'center'
  }
})
