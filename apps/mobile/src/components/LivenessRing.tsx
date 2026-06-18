import { useEffect, useRef } from 'react'
import { Animated, Easing, StyleSheet, View } from 'react-native'
import { tokens } from '../theme/tokens'

type Liveness = 'idle' | 'working' | 'error'

/**
 * Presence-ring der ÅNDER (pulserer) når Jarvis arbejder — ikke blinker.
 * Idle: rolig statisk ring. Working: langsom åndedræts-puls. Error: rød tone.
 * (Spec §"Visual Design" pkt. 1 — signalér liv uden at forstyrre.)
 */
export function LivenessRing({ status = 'idle', size = 28 }: { status?: Liveness; size?: number }) {
  const pulse = useRef(new Animated.Value(0)).current

  useEffect(() => {
    if (status !== 'working') {
      pulse.stopAnimation()
      pulse.setValue(0)
      return
    }
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, { toValue: 1, duration: 1100, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
        Animated.timing(pulse, { toValue: 0, duration: 1100, easing: Easing.inOut(Easing.ease), useNativeDriver: true })
      ])
    )
    loop.start()
    return () => loop.stop()
  }, [status, pulse])

  const ringColor = status === 'error' ? tokens.color.error : tokens.color.accent
  const scale = pulse.interpolate({ inputRange: [0, 1], outputRange: [1, 1.18] })
  const haloOpacity = pulse.interpolate({ inputRange: [0, 1], outputRange: [0, 0.35] })
  const inner = Math.round(size * 0.36)

  return (
    <View style={{ width: size, height: size, alignItems: 'center', justifyContent: 'center' }}>
      {/* åndende halo */}
      <Animated.View
        style={[
          styles.halo,
          {
            width: size,
            height: size,
            borderRadius: size / 2,
            backgroundColor: ringColor,
            opacity: haloOpacity,
            transform: [{ scale }]
          }
        ]}
      />
      <View style={[styles.ring, { width: size, height: size, borderRadius: size / 2, borderColor: ringColor }]}>
        <View style={{ width: inner, height: inner, borderRadius: inner / 2, backgroundColor: ringColor }} />
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  halo: { position: 'absolute' },
  ring: { borderWidth: 2, alignItems: 'center', justifyContent: 'center' }
})
