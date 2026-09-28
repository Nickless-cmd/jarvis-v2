import { Pressable, StyleSheet, Text, View } from 'react-native'
import { X } from 'lucide-react-native'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'

/**
 * Varslet om arbejde der aldrig blev færdigt.
 *
 * Målt 28/9-2026: der var NUL forekomster af «recovery» i hele
 * mobil-kildekoden. Desk fik banneret 25/9. På telefonen stoppede en kørsel
 * der gik i genoptagelse bare — med den tekst den nåede, og ingen forklaring.
 * Det er dét man oplever som et tavst cut.
 *
 * Samtidig gik andelen af kørsler der ikke når «completed» fra 2-8 % til
 * 13-21 % (20.-28. september), drevet af `pending-tool-intent`: «Jarvis havde
 * stadig et værktøjskald klar». Næsten alle af dem HAVDE tekst — svaret var
 * der, det blev bare aldrig gjort færdigt, og ingen sagde hvorfor.
 *
 * To udgaver, fordi de betyder noget forskelligt: `continuing` er «den er på
 * vej igen», og så pulserer prikken. Er arbejdet opgivet, står den stille —
 * et dødt run må ikke ligne et levende.
 */
export function GenoptagelsesBanner({ varsel, onLuk }: {
  varsel: { reason: string; message: string; continuing: boolean } | null
  onLuk: () => void
}) {
  const tokens = useTheme()
  const styles = useStyles(makeStyles)
  if (!varsel?.message) return null
  return (
    <View
      testID="genoptagelses-banner"
      accessibilityRole="alert"
      accessibilityLabel={varsel.message}
      style={[styles.banner, varsel.continuing ? styles.igang : styles.opgivet]}
    >
      <View
        testID={varsel.continuing ? 'genoptagelses-prik-igang' : 'genoptagelses-prik-stille'}
        style={[styles.prik, { backgroundColor: varsel.continuing ? tokens.color.accent : tokens.color.warn }]}
      />
      <Text style={styles.tekst}>{varsel.message}</Text>
      <Pressable accessibilityRole="button" accessibilityLabel="Luk" onPress={onLuk} hitSlop={10}>
        <X size={16} color={tokens.color.fg3} strokeWidth={2} />
      </Pressable>
    </View>
  )
}

const makeStyles = (tokens: Theme) => StyleSheet.create({
  banner: {
    flexDirection: 'row', alignItems: 'center', gap: tokens.spacing.sm,
    marginHorizontal: tokens.spacing.lg, marginBottom: tokens.spacing.xs,
    paddingHorizontal: tokens.spacing.md, paddingVertical: 8,
    borderRadius: 10, borderWidth: StyleSheet.hairlineWidth,
    backgroundColor: tokens.color.bg2,
  },
  igang: { borderColor: tokens.color.accentDim },
  opgivet: { borderColor: tokens.color.warn },
  prik: { width: 8, height: 8, borderRadius: 4 },
  tekst: { flex: 1, color: tokens.color.fg2, fontSize: 13 },
})
