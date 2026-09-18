import { useEffect, useRef, useState } from 'react'
import { Animated, Easing, StyleSheet, Text, View, type StyleProp, type TextStyle } from 'react-native'
import { Code2 } from 'lucide-react-native'
import { useReducedMotion } from '../lib/useReducedMotion'
import { GlidendeTekst } from './GlidendeTekst'

/**
 * Label-skiftet på tool-linjen — Claude Desktops `GS`, portet til React
 * Native (19/9-2026). Samme regler og tal som desk (`LabelSkift.tsx` dér):
 *
 * | hændelse             | spark | gammel label      | nyt label          |
 * |----------------------|-------|-------------------|--------------------|
 * | arbejdet slutter     | ja    | ud .15 s, + 30 dp | ind .25 s efter .21 s |
 * | arbejdet starter     | nej   | ingen exit        | ind .25 s          |
 * | kun teksten skifter  | nej   | ud .15 s          | ind .25 s          |
 *
 * Sparken (Code2-glyfen, Bjørns valg) holder i 210 ms og toner ud over de
 * næste 210 (kildens .42 s linear, 0-50 % fuld). Første tegning animerer
 * intet — en genindlæst tråd skal ikke skifte. Reduceret bevægelse: skiftet
 * sker uden animation, og de udgående lag vises slet ikke (kildens regel).
 */
type Label = { tekst: string; arbejder: boolean; id: number }

export function LabelSkift({
  tekst, arbejder, style, farve, fastIkon = false,
}: {
  tekst: string
  arbejder: boolean
  style?: StyleProp<TextStyle>
  /** Sparkens farve. */
  farve: string
  /**
   * Står `</>` fast foran linjen (Bjørn 19/9-2026: «må gerne komme tilbage»),
   * bliver afslutningen et almindeligt tekstskift uden spark.
   */
  fastIkon?: boolean
}) {
  const reduced = useReducedMotion()
  const [vist, setVist] = useState<Label>({ tekst, arbejder, id: 0 })
  const [gammel, setGammel] = useState<Label | null>(null)
  const [spark, setSpark] = useState(false)
  const [efterSpark, setEfterSpark] = useState(false)

  // Afledt i render, som kilden: skiftet skal ligge i SAMME tegning som den
  // nye tekst, ellers står den nye alene én frame.
  const slutter = vist.arbejder && !arbejder
  const starter = !vist.arbejder && arbejder
  if (vist.tekst !== tekst || slutter || starter) {
    if (starter) { setGammel(null); setSpark(false); setEfterSpark(false) }
    else { setGammel(vist); setSpark(slutter && !fastIkon); setEfterSpark(slutter && !fastIkon) }
    setVist({ tekst, arbejder, id: vist.id + 1 })
  }

  const ind = useRef(new Animated.Value(1)).current
  const ud = useRef(new Animated.Value(0)).current
  const sparkLys = useRef(new Animated.Value(0)).current

  useEffect(() => {
    if (vist.id === 0 || reduced) { ind.setValue(1); return }
    ind.setValue(0)
    Animated.timing(ind, {
      toValue: 1, duration: 250, delay: efterSpark ? 210 : 0,
      easing: Easing.inOut(Easing.ease), useNativeDriver: true,
    }).start()
  }, [vist.id]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!gammel) return
    ud.setValue(1)
    const a = Animated.timing(ud, { toValue: 0, duration: 150, easing: Easing.out(Easing.ease), useNativeDriver: true })
    a.start(({ finished }) => { if (finished) setGammel(null) })
    // Sikkerhedsnet som kilden: et afbrudt skift må ikke efterlade laget.
    const t = setTimeout(() => setGammel(null), 600)
    return () => { a.stop(); clearTimeout(t) }
  }, [gammel?.id]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!spark) return
    sparkLys.setValue(1)
    const a = Animated.sequence([
      Animated.delay(210),
      Animated.timing(sparkLys, { toValue: 0, duration: 210, easing: Easing.linear, useNativeDriver: true }),
    ])
    a.start(({ finished }) => { if (finished) setSpark(false) })
    const t = setTimeout(() => setSpark(false), 600)
    return () => { a.stop(); clearTimeout(t) }
  }, [spark])

  return (
    <View style={styles.celle}>
      <Animated.View style={{ opacity: ind }}>
        {arbejder
          ? <GlidendeTekst text={vist.tekst} aktiv style={style} numberOfLines={1} />
          : <Text style={style} numberOfLines={1} testID="linje-titel">{vist.tekst}</Text>}
      </Animated.View>
      {gammel && !reduced ? (
        <Animated.View
          pointerEvents="none"
          testID="ls-gammel"
          style={[styles.lag, { opacity: ud, paddingLeft: spark ? 30 : 0 }]}
        >
          <Text style={style} numberOfLines={1}>{gammel.tekst}</Text>
        </Animated.View>
      ) : null}
      {spark && !reduced ? (
        <Animated.View pointerEvents="none" testID="ls-spark" style={[styles.lag, styles.spark, { opacity: sparkLys }]}>
          <Code2 size={16} color={farve} strokeWidth={1.8} />
        </Animated.View>
      ) : null}
    </View>
  )
}

const styles = StyleSheet.create({
  celle: { flexShrink: 1, minWidth: 0 },
  lag: { position: 'absolute', left: 0, top: 0, right: 0 },
  // h-5 w-5 pt-1 i kilden
  spark: { width: 20, height: 20, alignItems: 'center', justifyContent: 'center', paddingTop: 2 },
})
