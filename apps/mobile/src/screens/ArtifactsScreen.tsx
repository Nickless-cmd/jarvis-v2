import { useEffect, useState } from 'react'
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native'
import { FileCode2, X } from 'lucide-react-native'
import { fetchArtifacts, type ArtifactItem } from '../lib/artifactsApi'
import { useAuth } from '../state/AuthContext'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'

export function ArtifactsScreen({
  onClose,
  initialArtifacts = null
}: {
  onClose: () => void
  initialArtifacts?: ArtifactItem[] | null
}) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  const { config } = useAuth()
  const [items, setItems] = useState<ArtifactItem[] | null>(initialArtifacts)

  useEffect(() => {
    if (!config || initialArtifacts) return
    let alive = true
    void fetchArtifacts(config).then((next) => { if (alive) setItems(next) })
    return () => { alive = false }
  }, [config, initialArtifacts])

  return (
    <View style={styles.root}>
      <View style={styles.header}>
        <Pressable accessibilityRole="button" accessibilityLabel="Luk" onPress={onClose} style={styles.circle}>
          <X size={20} color={tokens.color.fg1} strokeWidth={2} />
        </Pressable>
        <Text style={styles.title}>Artifacts</Text>
        <View style={styles.circleGhost} />
      </View>

      {items === null ? (
        <View style={styles.center}><ActivityIndicator color={tokens.color.accent} /></View>
      ) : items.length === 0 ? (
        <View style={styles.center}>
          <FileCode2 size={26} color={tokens.color.fg3} strokeWidth={1.7} />
          <Text style={styles.empty}>Ingen artifacts endnu.</Text>
        </View>
      ) : (
        <ScrollView contentContainerStyle={styles.list}>
          {items.map((item) => (
            <View key={item.id} style={styles.card}>
              <View style={styles.row}>
                <FileCode2 size={17} color={tokens.color.fg2} strokeWidth={1.8} />
                <Text style={styles.kind}>Patch</Text>
              </View>
              <Text style={styles.itemTitle}>{item.title}</Text>
              <Text style={styles.detail}>{item.detail}</Text>
            </View>
          ))}
        </ScrollView>
      )}
    </View>
  )
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
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: tokens.spacing.sm },
  empty: { color: tokens.color.fg3, fontSize: 15 },
  list: { padding: tokens.spacing.lg, gap: tokens.spacing.sm, paddingBottom: tokens.spacing.xl },
  card: {
    backgroundColor: tokens.color.bg1,
    borderRadius: tokens.radius.lg,
    borderWidth: 1,
    borderColor: tokens.color.line,
    padding: tokens.spacing.lg,
    gap: 7
  },
  row: { flexDirection: 'row', alignItems: 'center', gap: tokens.spacing.sm },
  kind: { color: tokens.color.fg2, fontSize: 12, fontWeight: '700', textTransform: 'uppercase' },
  itemTitle: { color: tokens.color.fg1, fontSize: 15, fontWeight: '700', lineHeight: 21 },
  detail: { color: tokens.color.fg3, fontSize: 13, lineHeight: 18 }
})
