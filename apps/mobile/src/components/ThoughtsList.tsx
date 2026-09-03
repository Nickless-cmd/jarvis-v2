import { StyleSheet, Text, View } from 'react-native'
import { Lightbulb } from 'lucide-react-native'
import { relativeAge, type Thought } from '../lib/companionClient'
import { tokens } from '../theme/tokens'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'

/**
 * Jarvis' tanker — dem han delte uden at blive spurgt.
 *
 * Hans eget ønske: «en besked fra Jarvis der ikke er et svar ... skal føles som
 * en tanke der deles, ikke en notifikation der afbryder.» En notifikation er
 * væk så snart man swiper den væk; her kan man finde den igen.
 *
 * TILBAGEHOLDTE tanker vises også, dæmpet og med grunden. Det er ikke støj:
 * uden dem kan man ikke se om grænserne er sat rigtigt — kun at der er stille.
 */
export function ThoughtsList({ items }: { items: Thought[] }) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  if (!items.length) {
    return (
      <View style={styles.empty}>
        <Lightbulb size={22} color={tokens.color.fg3} strokeWidth={1.6} />
        <Text style={styles.emptyText}>Han har ikke delt noget af sig selv endnu.</Text>
      </View>
    )
  }

  return (
    <>
      {items.map((t, i) => (
        <View
          key={`${t.at}-${i}`}
          testID={`thought-${i}`}
          style={[styles.card, !t.delivered && styles.held]}
        >
          <Text style={styles.text}>{t.text}</Text>
          <Text style={styles.meta}>
            {whenLabel(t.at)}
            {t.delivered ? '' : ` · holdt tilbage: ${t.reason || 'ukendt grund'}`}
          </Text>
        </View>
      ))}
    </>
  )
}

function whenLabel(iso: string): string {
  const t = Date.parse(iso)
  if (Number.isNaN(t)) return ''
  return relativeAge(Math.max(0, Math.round((Date.now() - t) / 1000)))
}

const makestyles = (tokens: Theme) => StyleSheet.create({
  card: {
    backgroundColor: tokens.color.bg2,
    borderRadius: tokens.radius.lg,
    padding: tokens.spacing.lg,
    gap: 6,
    marginBottom: tokens.spacing.sm
  },
  held: { opacity: 0.55 },
  text: { color: tokens.color.fg1, fontSize: 15.5, lineHeight: 22 },
  meta: { color: tokens.color.fg3, fontSize: 12.5 },
  empty: { alignItems: 'center', gap: tokens.spacing.md, paddingVertical: tokens.spacing.xl },
  emptyText: { color: tokens.color.fg3, fontSize: 14, textAlign: 'center' }
})
