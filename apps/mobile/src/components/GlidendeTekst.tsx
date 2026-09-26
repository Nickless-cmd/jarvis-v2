import { useEffect, useRef, useState } from 'react'
import { Animated, Easing, StyleSheet, Text, View, type TextStyle, type StyleProp } from 'react-native'
import Svg, { Defs, G, LinearGradient, Mask, Rect, Stop, Text as SvgText } from 'react-native-svg'
import { useReducedMotion } from '../lib/useReducedMotion'
import { useTheme } from '../theme/ThemeContext'

const VARIGHED_MS = 2250
const BAAND = 90
const DAEMPET = 0.5
const LYS_MOERK = '#eafff3'
const AnimatedG = Animated.createAnimatedComponent(G)

/** Én synlig SVG-tekstmaske: lyset kan kun ramme bogstaverne, og der er
 * ingen ekstra native tekstlag, som Android kan placere forskudt. */
export function GlidendeTekst({
  text, aktiv, style, numberOfLines,
}: {
  text: string
  aktiv: boolean
  style?: StyleProp<TextStyle>
  numberOfLines?: number
}) {
  const reduced = useReducedMotion()
  const theme = useTheme()
  const x = useRef(new Animated.Value(0)).current
  const [maal, setMaal] = useState({ width: 0, height: 0 })
  const animer = aktiv && !reduced && maal.width > 0 && maal.height > 0
  const lys = theme.scheme === 'light' ? theme.color.accentText : LYS_MOERK
  const tekstStyle = StyleSheet.flatten(style) || {}
  const skrift = tekstStyle.fontSize || 14
  const linje = tekstStyle.lineHeight || Math.round(skrift * 1.2)
  // SVG bruger en baseline; den usynlige native tekst bestemmer stadig
  // rækkehøjden og oplæsningsindholdet.
  const baseline = (maal.height - linje) / 2 + (linje + skrift) / 2 - 2

  useEffect(() => {
    if (!animer) {
      x.stopAnimation()
      x.setValue(0)
      return
    }
    x.setValue(0)
    const loop = Animated.loop(Animated.timing(x, {
      toValue: 1, duration: VARIGHED_MS,
      easing: Easing.linear, useNativeDriver: true,
    }))
    loop.start()
    return () => loop.stop()
  }, [animer, x])

  return (
    <View
      testID="glidende-tekst"
      style={styles.wrap}
      onLayout={(e) => {
        const { width, height } = e.nativeEvent.layout
        const w = Math.round(width)
        const h = Math.round(height)
        setMaal((old) => old.width === w && old.height === h ? old : { width: w, height: h })
      }}
    >
      <Text style={[style, animer && styles.skjult]} numberOfLines={numberOfLines}>{text}</Text>
      {animer ? (
        <Svg
          testID="glidende-lys"
          pointerEvents="none"
          accessibilityElementsHidden
          importantForAccessibility="no-hide-descendants"
          accessible={false}
          width={maal.width}
          height={maal.height}
          style={styles.svg}
        >
          <Defs>
            <Mask id="bogstaver" x={0} y={0} width={maal.width} height={maal.height} maskUnits="userSpaceOnUse" maskType="alpha">
              <SvgText
                x={0} y={baseline} fill="#fff"
                fontSize={skrift}
                fontFamily={tekstStyle.fontFamily}
                fontWeight={tekstStyle.fontWeight}
              >{text}</SvgText>
            </Mask>
            <LinearGradient id="lysboelge" x1="0" y1="0" x2="1" y2="0">
              <Stop offset="0" stopColor={lys} stopOpacity="0" />
              <Stop offset="0.5" stopColor={lys} stopOpacity="1" />
              <Stop offset="1" stopColor={lys} stopOpacity="0" />
            </LinearGradient>
          </Defs>
          <G mask="url(#bogstaver)">
            <Rect x={0} y={0} width={maal.width} height={maal.height} fill={tekstStyle.color || theme.color.fg2} opacity={DAEMPET} />
            <AnimatedG transform={[{
              translateX: x.interpolate({
                inputRange: [0, 1], outputRange: [-BAAND, maal.width + BAAND],
              }),
            }]}>
              <Rect x={0} y={0} width={BAAND} height={maal.height} fill="url(#lysboelge)" />
            </AnimatedG>
          </G>
        </Svg>
      ) : null}
    </View>
  )
}

const styles = StyleSheet.create({
  wrap: { flexShrink: 1, overflow: 'hidden', justifyContent: 'center' },
  skjult: { opacity: 0 },
  svg: { position: 'absolute', top: 0, left: 0 },
})
