import { useEffect, useRef } from 'react'
import { Animated, View } from 'react-native'
import Svg, { Defs, LinearGradient, Rect, Stop } from 'react-native-svg'
import { tokens } from '../theme/tokens'

/**
 * Tynd glødende linje (svg LinearGradient) der glider venstre→højre mens Jarvis
 * streamer. Skjult når inaktiv. §3.5 stream-indikator (1:1 med mockup).
 */
export function StreamIndicator({ active, width = 320 }: { active: boolean; width?: number }) {
  const x = useRef(new Animated.Value(0)).current
  useEffect(() => {
    if (!active) {
      x.stopAnimation()
      return
    }
    const loop = Animated.loop(
      Animated.timing(x, { toValue: 1, duration: 1200, useNativeDriver: true })
    )
    loop.start()
    return () => loop.stop()
  }, [active, x])
  if (!active) return null
  const translateX = x.interpolate({ inputRange: [0, 1], outputRange: [-width, width] })
  return (
    <View style={{ height: 2, width: '100%', overflow: 'hidden' }}>
      <Animated.View style={{ width, transform: [{ translateX }] }}>
        <Svg width={width} height={2}>
          <Defs>
            <LinearGradient id="stream" x1="0" y1="0" x2="1" y2="0">
              <Stop offset="0" stopColor={tokens.color.accent} stopOpacity="0" />
              <Stop offset="0.5" stopColor={tokens.color.accent} stopOpacity="1" />
              <Stop offset="1" stopColor={tokens.color.accent} stopOpacity="0" />
            </LinearGradient>
          </Defs>
          <Rect width={width} height={2} fill="url(#stream)" />
        </Svg>
      </Animated.View>
    </View>
  )
}
