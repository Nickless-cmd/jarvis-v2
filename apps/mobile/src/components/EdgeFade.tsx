import { StyleSheet, View } from 'react-native'
import Svg, { Defs, LinearGradient, Rect, Stop } from 'react-native-svg'
import { useTheme } from '../theme/ThemeContext'

/**
 * Udtoning i kanten, hvor tråden ruller ind under en svævende flade.
 *
 * Headeren og komposeren ligger OVENPÅ tråden. Uden en udtoning bliver teksten
 * skåret tværs over midt i en linje lige dér hvor de begynder, og det ligner et
 * uheld frem for to lag. Med den opløses linjen i stedet i fladen, og øjet
 * læser den svævende flade som noget der ligger over — hvilket den gør.
 *
 * Gradienten går til GENNEMSIGTIG og ikke til baggrundsfarven: en «usynlig»
 * kant malet i baggrundsfarven ville stadig dække tråden, og så ville det
 * kun se rigtigt ud, når man ikke rullede.
 */
export function EdgeFade({
  height,
  edge,
}: {
  height: number
  /** 'top' = massiv foroven (under headeren). 'bottom' = massiv forneden (over komposeren). */
  edge: 'top' | 'bottom'
}) {
  const tokens = useTheme()
  const id = `fade-${edge}`
  // SVG kræver voksende offsets, så retningen kan ikke laves ved bare at bytte
  // enderne om — stoppene skal spejles. Den massive ende holder næsten fuld
  // dækning et stykke ind, så teksten er helt væk INDEN kanten, og først
  // derefter toner den ud.
  // Fuld dækning HELE vejen forbi den svævende flade, og først derefter en
  // udtoning. Med en gradient der begynder at slippe med det samme skinner der
  // et par procent tekst igennem bag knapperne — nok til at man ser stumper af
  // ord uden at kunne læse dem, hvilket er værre end begge dele.
  const stops = edge === 'top'
    ? [{ o: '0', a: '1' }, { o: '0.64', a: '1' }, { o: '1', a: '0' }]
    : [{ o: '0', a: '0' }, { o: '0.36', a: '1' }, { o: '1', a: '1' }]
  return (
    <View style={[styles.wrap, edge === 'top' ? styles.top : styles.bottom, { height }]} pointerEvents="none">
      <Svg width="100%" height={height}>
        <Defs>
          <LinearGradient id={id} x1="0" y1="0" x2="0" y2="1">
            {stops.map((st) => (
              <Stop key={st.o} offset={st.o} stopColor={tokens.color.bg0} stopOpacity={st.a} />
            ))}
          </LinearGradient>
        </Defs>
        <Rect x="0" y="0" width="100%" height={height} fill={`url(#${id})`} />
      </Svg>
    </View>
  )
}

const styles = StyleSheet.create({
  wrap: { position: 'absolute', left: 0, right: 0 },
  top: { top: 0 },
  bottom: { bottom: 0 },
})
