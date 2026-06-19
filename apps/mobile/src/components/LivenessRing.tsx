import { useEffect, useRef } from 'react'
import { Animated, Easing, StyleSheet, View } from 'react-native'
import Svg, { Circle, Defs, RadialGradient, Stop } from 'react-native-svg'
import { tokens } from '../theme/tokens'
import { useReducedMotion } from '../lib/useReducedMotion'

type Liveness = 'idle' | 'working' | 'error'

/**
 * Presence-ring der ÅNDER (pulserer) når Jarvis arbejder — ikke blinker.
 * Idle: rolig svag glød. Working: langsom åndedræts-puls. Error: rød tone.
 * Glød = ægte svg RadialGradient (blød fade, 1:1 med design-mockup, §3.1).
 */
export function LivenessRing({ status = 'idle', size = 28 }: { status?: Liveness; size?: number }) {
  const pulse = useRef(new Animated.Value(0)).current
  const reduced = useReducedMotion()

  useEffect(() => {
    if (status !== 'working' || reduced) {
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
  }, [status, pulse, reduced])

  const ringColor = status === 'error' ? tokens.color.error : tokens.color.accent
  const scale = pulse.interpolate({ inputRange: [0, 1], outputRange: [1, 1.18] })
  // Working ånder fra svag→fuld; idle/error viser en svag konstant glød.
  const haloOpacity: Animated.AnimatedInterpolation<number> | Animated.Value =
    status === 'working'
      ? pulse.interpolate({ inputRange: [0, 1], outputRange: [0.25, 1] })
      : new Animated.Value(status === 'error' ? 0.5 : 0.35)
  const inner = Math.round(size * 0.36)
  const glow = Math.round(size * 1.7)

  return (
    <View style={{ width: size, height: size, alignItems: 'center', justifyContent: 'center' }}>
      <Animated.View style={[styles.halo, { opacity: haloOpacity, transform: [{ scale }] }]}>
        <Svg width={glow} height={glow}>
          <Defs>
            <RadialGradient id="glow" cx="50%" cy="50%" r="50%">
              <Stop offset="0.55" stopColor={ringColor} stopOpacity="0" />
              <Stop offset="0.85" stopColor={ringColor} stopOpacity="0.55" />
              <Stop offset="1" stopColor={ringColor} stopOpacity="0" />
            </RadialGradient>
          </Defs>
          <Circle cx={glow / 2} cy={glow / 2} r={glow / 2} fill="url(#glow)" />
        </Svg>
      </Animated.View>
      <View style={[styles.ring, { width: size, height: size, borderRadius: size / 2, borderColor: ringColor }]}>
        <View style={{ width: inner, height: inner, borderRadius: inner / 2, backgroundColor: ringColor }} />
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  halo: { position: 'absolute', alignItems: 'center', justifyContent: 'center' },
  ring: { borderWidth: 2, alignItems: 'center', justifyContent: 'center' }
})
