import { useEffect, useState } from 'react'
import { ActivityIndicator, FlatList, Pressable, StyleSheet, Text, View } from 'react-native'
import { Eye, X } from 'lucide-react-native'
import { fetchSenses, relativeAge, type SenseItem } from '../lib/companionClient'
import { useAuth } from '../state/AuthContext'
import { tokens } from '../theme/tokens'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'

/**
 * Sansernes Arkiv — hvad Jarvis har set i hjemmet.
 *
 * KUN FOR HUSSTANDEN (Bjørn og Michelle), og grænsen ligger IKKE her. Serveren
 * afviser alle andre roller med 403 på `/companion/senses`
 * (dependencies=[Depends(require_household)]).
 * Denne skærm skjuler bare noget, der allerede er lukket — forskellen på en dør
 * og et gardin. Bygger nogen en anden klient, holder døren stadig.
 *
 * Får vi null tilbage, siger vi det ærligt frem for at vise en tom liste: «tom»
 * og «du må ikke se det» er to forskellige ting, og de skal ikke ligne hinanden.
 */
export function SensesScreen({ onClose }: { onClose: () => void }) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  const { config } = useAuth()
  const [items, setItems] = useState<SenseItem[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [denied, setDenied] = useState(false)

  useEffect(() => {
    if (!config) return
    let cancelled = false
    void fetchSenses(config).then((res) => {
      if (cancelled) return
      if (res === null) setDenied(true)
      else setItems(res)
      setLoading(false)
    })
    return () => { cancelled = true }
  }, [config])

  return (
    <View style={styles.root}>
      <View style={styles.header}>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Luk"
          onPress={onClose}
          style={styles.circle}
        >
          <X size={20} color={tokens.color.fg1} strokeWidth={2} />
        </Pressable>
        <Text style={styles.title}>Sansernes Arkiv</Text>
        <View style={styles.circleGhost} />
      </View>

      {loading ? (
        <View style={styles.center}><ActivityIndicator color={tokens.color.accent} /></View>
      ) : denied ? (
        <View style={styles.center}>
          <Text style={styles.empty}>
Arkivet er privat for dem der bor i hjemmet.
          </Text>
        </View>
      ) : !items?.length ? (
        <View style={styles.center}>
          <Eye size={26} color={tokens.color.fg3} strokeWidth={1.6} />
          <Text style={styles.empty}>
            Han har ikke noteret noget endnu.
          </Text>
        </View>
      ) : (
        <FlatList
          data={items}
          keyExtractor={(it, i) => `${it.captured_at}-${i}`}
          contentContainerStyle={styles.list}
          renderItem={({ item }) => (
            <View style={styles.card}>
              <Text style={styles.when}>{whenLabel(item.captured_at)}</Text>
              <Text style={styles.desc}>{item.description}</Text>
            </View>
          )}
        />
      )}
    </View>
  )
}

function whenLabel(iso: string): string {
  const t = Date.parse(iso)
  if (Number.isNaN(t)) return ''
  return relativeAge(Math.max(0, Math.round((Date.now() - t) / 1000)))
}

const makestyles = (tokens: Theme) => StyleSheet.create({
  root: { flex: 1, backgroundColor: tokens.color.bg0, paddingTop: 48 },
  header: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    paddingHorizontal: tokens.spacing.md, paddingBottom: tokens.spacing.md
  },
  circle: {
    width: 40, height: 40, borderRadius: 20, alignItems: 'center',
    justifyContent: 'center', backgroundColor: tokens.color.bg2
  },
  circleGhost: { width: 40, height: 40 },
  title: { color: tokens.color.fg1, fontSize: 17, fontWeight: '700' },
  list: { padding: tokens.spacing.lg, gap: tokens.spacing.sm },
  card: {
    backgroundColor: tokens.color.bg2,
    borderRadius: tokens.radius.lg,
    padding: tokens.spacing.lg,
    gap: 6
  },
  when: { color: tokens.color.fg3, fontSize: 12.5 },
  desc: { color: tokens.color.fg1, fontSize: 15.5, lineHeight: 22 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: tokens.spacing.md, padding: tokens.spacing.xl },
  empty: { color: tokens.color.fg2, fontSize: 15, textAlign: 'center', lineHeight: 22 }
})
