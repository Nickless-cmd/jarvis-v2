import { useEffect, useState } from 'react'
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native'
import { Brain, Database, X } from 'lucide-react-native'
import { fetchMemoryOverview, type MemoryOverview } from '../lib/memoryApi'
import { useAuth } from '../state/AuthContext'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'

export function MemoryScreen({
  onClose,
  onOpenDataControls,
  initialMemory = null
}: {
  onClose: () => void
  onOpenDataControls: () => void
  initialMemory?: MemoryOverview | null
}) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  const { config } = useAuth()
  const [memory, setMemory] = useState<MemoryOverview | null>(initialMemory)

  useEffect(() => {
    if (!config || initialMemory) return
    let alive = true
    void fetchMemoryOverview(config).then((m) => { if (alive) setMemory(m) })
    return () => { alive = false }
  }, [config])

  return (
    <View style={styles.root}>
      <View style={styles.header}>
        <Pressable accessibilityRole="button" accessibilityLabel="Luk" onPress={onClose} style={styles.circle}>
          <X size={20} color={tokens.color.fg1} strokeWidth={2} />
        </Pressable>
        <Text style={styles.title}>Hukommelse</Text>
        <View style={styles.circleGhost} />
      </View>

      {memory === null ? (
        <View style={styles.center}><ActivityIndicator color={tokens.color.accent} /></View>
      ) : (
        <ScrollView contentContainerStyle={styles.list}>
          <View style={styles.summary}>
            <Brain size={18} color={tokens.color.fg2} strokeWidth={1.8} />
            <Text style={styles.summaryText}>{memory.brainCount} private brain-poster</Text>
          </View>

          {memory.identityPreview ? (
            <View style={styles.card}>
              <Text style={styles.cardTitle}>Hvem du er</Text>
              <Text style={styles.preview} numberOfLines={5}>{memory.identityPreview}</Text>
            </View>
          ) : null}

          {memory.sections.length ? (
            memory.sections.map((section) => (
              <View key={section.title} style={styles.card}>
                <Text style={styles.cardTitle}>{section.title}</Text>
                <Text style={styles.preview}>{section.preview || 'Ingen tekst i sektionen.'}</Text>
              </View>
            ))
          ) : (
            <Text style={styles.empty}>Ingen kuraterede memory-sektioner endnu.</Text>
          )}

          <Pressable
            accessibilityRole="button"
            onPress={onOpenDataControls}
            style={styles.dataCard}
          >
            <Database size={18} color={tokens.color.fg1} strokeWidth={1.8} />
            <View style={styles.dataText}>
              <Text style={styles.dataTitle}>Datastyring</Text>
              <Text style={styles.muted}>Eksportér eller slet lagvis, når noget skal væk.</Text>
            </View>
          </Pressable>
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
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  list: { padding: tokens.spacing.lg, gap: tokens.spacing.sm, paddingBottom: tokens.spacing.xl },
  summary: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: tokens.spacing.sm,
    backgroundColor: tokens.color.bg1,
    borderRadius: tokens.radius.lg,
    padding: tokens.spacing.md
  },
  summaryText: { color: tokens.color.fg1, fontWeight: '700' },
  card: {
    backgroundColor: tokens.color.bg2,
    borderRadius: tokens.radius.lg,
    padding: tokens.spacing.lg,
    gap: 6
  },
  cardTitle: { color: tokens.color.fg1, fontWeight: '700', fontSize: 15 },
  preview: { color: tokens.color.fg2, lineHeight: 20 },
  empty: { color: tokens.color.fg3, textAlign: 'center', paddingVertical: tokens.spacing.lg },
  dataCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: tokens.spacing.md,
    backgroundColor: tokens.color.bg1,
    borderRadius: tokens.radius.lg,
    padding: tokens.spacing.lg,
    marginTop: tokens.spacing.md
  },
  dataText: { flex: 1, gap: 3 },
  dataTitle: { color: tokens.color.fg1, fontWeight: '700' },
  muted: { color: tokens.color.fg3, fontSize: 13 }
})
