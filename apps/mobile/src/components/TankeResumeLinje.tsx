import { StyleSheet, Text, View } from 'react-native'
import { Brain } from 'lucide-react-native'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'

/**
 * Resuméet af tænkningen over en værktøjsgruppe — visningen «Tænkning»
 * (Claude Desktop: «a one-line recap of Claude's thinking above each tool
 * group»). Samme 20 dp-celle og indrykning som linjen under — dæmpet og
 * kursiv: det er optakten til gruppen, ikke en handling. Som desk.
 */
export function TankeResumeLinje({ tekst }: { tekst: string }) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  return (
    <View style={styles.row} testID="tanke-resume">
      <View style={styles.ikon}>
        <Brain size={16} color={tokens.color.fg3} strokeWidth={1.8} />
      </View>
      <Text style={styles.tekst} numberOfLines={1}>{tekst}</Text>
    </View>
  )
}

const makestyles = (tokens: Theme) => StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', gap: tokens.spacing.sm, paddingHorizontal: tokens.spacing.lg, paddingTop: 4 },
  ikon: { width: 20, height: 20, marginRight: 2, alignItems: 'center', justifyContent: 'center' },
  tekst: { color: tokens.color.fg3, fontSize: 14, fontStyle: 'italic', flexShrink: 1 },
})
