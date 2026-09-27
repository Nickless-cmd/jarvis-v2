import { useEffect, useRef } from 'react'
import { Animated, Easing, StyleSheet, Text, View } from 'react-native'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'
import { useReducedMotion } from '../lib/useReducedMotion'

/** Rammens mål. Bjælken starter lige over kanten og ender lige under. */
const RAMME_H = 148
const BJAELKE_H = 34

/**
 * Billedanalyse under kørslen.
 *
 * Hvorfor: målt på CT105 27/9-2026 over fjorten dage er `analyze_image`
 * **232 kald, median 8,49 s**, p90 28,6 s (219 ok). Otte sekunder hvor der
 * intet sker er rigeligt til at tro turen er gået i stå.
 *
 * Den ligner med vilje ikke [ImageGenerationCard]'s prik-gitter: gitteret
 * siger «noget bliver til», scanningen siger «der bliver kigget på noget der
 * allerede er». Ingen procent — værktøjet leverer ingen.
 */
export function ImageAnalysisCard({ kilde }: { kilde?: string }) {
  const tokens = useTheme()
  const styles = useStyles(makeStyles)
  const reducedMotion = useReducedMotion()
  const scan = useRef(new Animated.Value(0)).current
  const navn = (kilde || '').trim()

  useEffect(() => {
    if (reducedMotion) {
      scan.setValue(0.5)
      return
    }
    const animation = Animated.loop(Animated.sequence([
      Animated.timing(scan, { toValue: 1, duration: 2200, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
      Animated.timing(scan, { toValue: 0, duration: 2200, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
    ]))
    animation.start()
    return () => animation.stop()
  }, [scan, reducedMotion])

  const hjoerne = { borderColor: tokens.color.accent }
  return (
    <View testID="image-analysis-progress" accessibilityRole="progressbar"
      accessibilityLabel={navn ? `Analyserer ${navn}` : 'Analyserer billede'} style={styles.wrap}>
      <Text style={styles.label} numberOfLines={2}>
        Analyserer billede{navn ? ` · ${navn}` : ''}…
      </Text>
      <View style={styles.ramme}>
        <Animated.View testID="image-analysis-scan" style={[styles.scan, {
          backgroundColor: tokens.color.accentGhost,
          borderBottomColor: tokens.color.accentDim,
          transform: [{
            translateY: scan.interpolate({ inputRange: [0, 1], outputRange: [-BJAELKE_H, RAMME_H] }),
          }],
        }]} />
        <View style={[styles.hjoerne, styles.tv, hjoerne]} />
        <View style={[styles.hjoerne, styles.th, hjoerne]} />
        <View style={[styles.hjoerne, styles.bv, hjoerne]} />
        <View style={[styles.hjoerne, styles.bh, hjoerne]} />
      </View>
    </View>
  )
}

const makeStyles = (tokens: Theme) => StyleSheet.create({
  wrap: { width: 280, alignSelf: 'flex-start', marginHorizontal: tokens.spacing.lg,
    marginVertical: tokens.spacing.md, gap: tokens.spacing.md },
  label: { color: tokens.color.fg2, fontSize: 14 },
  ramme: {
    width: 256, height: RAMME_H, maxWidth: '100%', borderRadius: 6,
    overflow: 'hidden', backgroundColor: tokens.color.bg2,
    borderWidth: StyleSheet.hairlineWidth, borderColor: tokens.color.line,
  },
  // RN har ingen gradient uden et bibliotek; et svagt bånd med en lysere
  // underkant giver samme aflæsning. Farverne er temaets egne gennemsigtige
  // accenter — en `opacity` på selve View'et ville også dæmpe kanten, og så
  // var der ingen kant at se.
  scan: {
    position: 'absolute', left: 0, right: 0, top: 0, height: BJAELKE_H,
    borderBottomWidth: 1,
  },
  hjoerne: { position: 'absolute', width: 14, height: 14, borderWidth: 2, opacity: 0.65 },
  tv: { top: 10, left: 10, borderRightWidth: 0, borderBottomWidth: 0 },
  th: { top: 10, right: 10, borderLeftWidth: 0, borderBottomWidth: 0 },
  bv: { bottom: 10, left: 10, borderRightWidth: 0, borderTopWidth: 0 },
  bh: { bottom: 10, right: 10, borderLeftWidth: 0, borderTopWidth: 0 },
})
