import { useRef } from 'react'
import { PanResponder, Pressable, StyleSheet, Text, View } from 'react-native'
import { tokens } from '../theme/tokens'

/** Flydende tommel-venlige hop-knapper ved højre kant + en tynd scrubber-track.
 *  Skjult når der er for få beskeder. onScrub(fraction): 0=nyeste, 1=ældste. */
export function SaveRail({
  visible,
  onJumpTop,
  onJumpBottom,
  onOlderUser,
  onNewerUser,
  onScrub,
}: {
  visible: boolean
  onJumpTop: () => void
  onJumpBottom: () => void
  onOlderUser: () => void
  onNewerUser: () => void
  onScrub: (fraction: number) => void
}) {
  const trackTop = useRef(0)
  const trackH = useRef(1)
  const pan = useRef(
    PanResponder.create({
      onMoveShouldSetPanResponder: () => true,
      onPanResponderMove: (_e, g) => {
        const rel = g.moveY - trackTop.current
        const f = Math.max(0, Math.min(1, rel / Math.max(1, trackH.current)))
        onScrub(f)
      },
    }),
  ).current

  if (!visible) return null
  return (
    <View style={styles.root} pointerEvents="box-none">
      <Btn label="⤓" hint="Nyeste" onPress={onJumpBottom} />
      <Btn label="▼" hint="Næste besked" onPress={onNewerUser} />
      <View
        style={styles.track}
        onLayout={(e) => { trackTop.current = e.nativeEvent.layout.y; trackH.current = e.nativeEvent.layout.height }}
        {...pan.panHandlers}
      />
      <Btn label="▲" hint="Forrige besked" onPress={onOlderUser} />
      <Btn label="⤒" hint="Ældste" onPress={onJumpTop} />
    </View>
  )
}

function Btn({ label, hint, onPress }: { label: string; hint: string; onPress: () => void }) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={hint}
      onPress={onPress}
      hitSlop={8}
      style={({ pressed }) => [styles.btn, pressed && styles.pressed]}
    >
      <Text style={styles.btnText}>{label}</Text>
    </Pressable>
  )
}

const styles = StyleSheet.create({
  root: { position: 'absolute', right: tokens.spacing.sm, top: '20%', alignItems: 'center', gap: tokens.spacing.xs },
  btn: { width: 36, height: 36, borderRadius: 18, backgroundColor: tokens.color.bg2, alignItems: 'center', justifyContent: 'center', opacity: 0.85 },
  pressed: { opacity: 1 },
  btnText: { color: tokens.color.fg1, fontSize: 16 },
  track: { width: 4, height: 90, borderRadius: 2, backgroundColor: tokens.color.line, marginVertical: tokens.spacing.xs },
})
