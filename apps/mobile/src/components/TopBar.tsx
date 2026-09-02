import { Pressable, StyleSheet, Text, View } from 'react-native'
import { SegmentedControl } from './SegmentedControl'
import { tokens } from '../theme/tokens'

export type AppMode = 'snak' | 'arbejde'

interface Props {
  mode: AppMode
  onModeChange: (next: AppMode) => void
  onMenu: () => void
  onSync: () => void
  /** Prik på Arbejde når noget venter på Bjørn. */
  pendingWork?: boolean
  syncing?: boolean
}

/**
 * Appens øverste bjælke: menu · [Snak|Arbejde] · sync.
 *
 * Ét sted ejer toppen. ChatScreen havde tidligere sin egen header — to
 * komponenter der forhandler om samme areal giver «hoppen» ved tilstandsskift,
 * præcis det speccens mikro-interaktions-afsnit lover at undgå.
 */
export function TopBar({ mode, onModeChange, onMenu, onSync, pendingWork, syncing }: Props) {
  return (
    <View style={styles.bar}>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel="Menu"
        onPress={onMenu}
        style={styles.circle}
      >
        <View style={styles.menuLine} />
        <View style={styles.menuLine} />
      </Pressable>

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

      <Pressable
        accessibilityRole="button"
        accessibilityLabel="Synkronisér"
        accessibilityState={{ busy: Boolean(syncing) }}
        onPress={onSync}
        style={styles.circle}
      >
        <Text style={[styles.syncGlyph, syncing && styles.syncBusy]}>⟳</Text>
      </Pressable>
    </View>
  )
}

const CIRCLE = 34

const styles = StyleSheet.create({
  bar: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: tokens.spacing.sm,
    paddingHorizontal: tokens.spacing.md,
    paddingVertical: tokens.spacing.sm,
    backgroundColor: tokens.color.bg0
  },
  center: {
    flex: 1,
    maxWidth: 260,
    alignSelf: 'center'
  },
  circle: {
    width: CIRCLE,
    height: CIRCLE,
    borderRadius: CIRCLE / 2,
    backgroundColor: tokens.color.bg2,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 3
  },
  menuLine: {
    width: 14,
    height: 1.5,
    borderRadius: 1,
    backgroundColor: tokens.color.fg1
  },
  syncGlyph: {
    color: tokens.color.fg1,
    fontSize: 16,
    lineHeight: 18
  },
  syncBusy: {
    color: tokens.color.accent
  }
})
