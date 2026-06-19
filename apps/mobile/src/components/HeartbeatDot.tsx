import { useEffect, useRef } from 'react'
import { Animated } from 'react-native'
import { tokens } from '../theme/tokens'

/**
 * Lille accent-prik der pulserer som et HJERTE (to hurtige slag pr. løkke) —
 * ikke en hård alarm-blink. §3.9 notifikationsprik. Brug hvor en ulæst-/
 * aktivitets-indikator skal vise liv.
 */
export function HeartbeatDot({ size = 8, color = tokens.color.accent }: { size?: number; color?: string }) {
  const beat = useRef(new Animated.Value(0)).current
  useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(beat, { toValue: 1, duration: 140, useNativeDriver: true }),
        Animated.timing(beat, { toValue: 0, duration: 160, useNativeDriver: true }),
        Animated.timing(beat, { toValue: 1, duration: 140, useNativeDriver: true }),
        Animated.timing(beat, { toValue: 0, duration: 160, useNativeDriver: true }),
        Animated.delay(tokens.motion.heartbeat - 600)
      ])
    )
    loop.start()
    return () => loop.stop()
  }, [beat])
  const scale = beat.interpolate({ inputRange: [0, 1], outputRange: [1, 1.3] })
  return (
    <Animated.View
      style={{
        width: size,
        height: size,
        borderRadius: size / 2,
        backgroundColor: color,
        transform: [{ scale }]
      }}
    />
  )
}
