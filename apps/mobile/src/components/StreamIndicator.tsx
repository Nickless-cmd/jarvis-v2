import { useEffect, useRef, useState } from 'react'
import { Animated, View, type LayoutChangeEvent } from 'react-native'
import Svg, { Defs, LinearGradient, Rect, Stop } from 'react-native-svg'
import { tokens } from '../theme/tokens'
import { useReducedMotion } from '../lib/useReducedMotion'

/**
 * Tynd glødende linje (svg LinearGradient) der glider venstre→højre mens Jarvis
 * streamer. Skjult når inaktiv. §3.5 stream-indikator (1:1 med mockup).
 *
 * Sømløs loop: baren er præcis container-bred og glider fra -W til +W, så
 * teleporten tilbage til start ALTID sker mens baren er helt uden for skærmen
 * (ingen synlig stutter). Container-bredden måles via onLayout.
 */
export function StreamIndicator({ active }: { active: boolean }) {
  const x = useRef(new Animated.Value(0)).current
  const [width, setWidth] = useState(0)
  const reduced = useReducedMotion()

  const onLayout = (e: LayoutChangeEvent) => {
    const w = Math.round(e.nativeEvent.layout.width)
    if (w > 0 && w !== width) setWidth(w)
  }

  useEffect(() => {
    if (!active || reduced || width <= 0) {
      x.stopAnimation()
      x.setValue(0)
      return
    }
    x.setValue(0)
    const loop = Animated.loop(
      Animated.timing(x, { toValue: 1, duration: 1400, useNativeDriver: true }),
    )
    loop.start()
    return () => loop.stop()
  }, [active, reduced, width, x])

  if (!active) return null
  // -W → +W: ved begge yderpunkter er den W-brede bar helt uden for containeren,
  // så loop-resettet er usynligt.
  const translateX = width > 0
    ? x.interpolate({ inputRange: [0, 1], outputRange: [-width, width] })
    : 0
  return (
    <View style={{ height: 2, width: '100%', overflow: 'hidden' }} onLayout={onLayout}>
      {width > 0 ? (
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
      ) : null}
    </View>
  )
}
