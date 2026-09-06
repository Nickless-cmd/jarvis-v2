import { useEffect, useState } from 'react'
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native'
import { Brain, CheckCircle2, Database, Eye, Pencil, Pin, Trash2, X } from 'lucide-react-native'
import { fetchMemoryOverview, type MemoryOverview } from '../lib/memoryApi'
import { useAuth } from '../state/AuthContext'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'
import { StatusState } from '../components/StatusState'

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
  const [hidden, setHidden] = useState<string[]>([])
  const [pinned, setPinned] = useState<string[]>([])
  const [editing, setEditing] = useState<string | null>(null)
  const [drafts, setDrafts] = useState<Record<string, string>>({})

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
        <StatusState title="Henter hukommelse" loading />
      ) : (
        <ScrollView contentContainerStyle={styles.list}>
          <View style={styles.summary}>
            <Brain size={18} color={tokens.color.fg2} strokeWidth={1.8} />
            <View style={styles.summaryCopy}>
              <Text style={styles.summaryText}>{memory.brainCount} private brain-poster</Text>
              <Text style={styles.summaryMeta}>Reviewable memory</Text>
            </View>
          </View>

          {memory.identityPreview ? (
            <View style={styles.card}>
              <Text style={styles.cardTitle}>Hvem du er</Text>
              <Text style={styles.preview} numberOfLines={5}>{memory.identityPreview}</Text>
            </View>
          ) : null}

          {memory.sections.filter((section) => !hidden.includes(section.title)).length ? (
            memory.sections.filter((section) => !hidden.includes(section.title)).map((section) => (
              <View key={section.title} style={styles.card}>
                <View style={styles.cardHead}>
                  <Text style={styles.cardTitle}>{section.title}</Text>
                  <View style={styles.contextPill}>
                    {pinned.includes(section.title) ? (
                      <Pin size={13} color={tokens.color.accent} strokeWidth={1.9} />
                    ) : (
                      <CheckCircle2 size={13} color={tokens.color.accent} strokeWidth={1.9} />
                    )}
                    <Text style={styles.contextText}>{pinned.includes(section.title) ? 'Pinned' : 'Brugt som kontekst'}</Text>
                  </View>
                </View>
                {editing === section.title ? (
                  <TextInput
                    multiline
                    value={drafts[section.title] ?? section.preview}
                    onChangeText={(text) => setDrafts((cur) => ({ ...cur, [section.title]: text }))}
                    placeholderTextColor={tokens.color.fg3}
                    style={styles.editBox}
                  />
                ) : (
                  <Text style={styles.preview}>{(drafts[section.title] ?? section.preview) || 'Ingen tekst i sektionen.'}</Text>
                )}
                <View style={styles.actions}>
                  <Pressable accessibilityRole="button" onPress={() => setPinned((cur) => cur.includes(section.title) ? cur.filter((x) => x !== section.title) : [...cur, section.title])} style={styles.actionBtn}>
                    <Pin size={14} color={tokens.color.fg2} strokeWidth={1.8} />
                    <Text style={styles.actionText}>Pin</Text>
                  </Pressable>
                  <Pressable accessibilityRole="button" onPress={() => setEditing((cur) => cur === section.title ? null : section.title)} style={styles.actionBtn}>
                    <Pencil size={14} color={tokens.color.fg2} strokeWidth={1.8} />
                    <Text style={styles.actionText}>{editing === section.title ? 'Gem' : 'Rediger'}</Text>
                  </Pressable>
                  <Pressable accessibilityRole="button" onPress={() => setHidden((cur) => [...cur, section.title])} style={styles.actionBtn}>
                    <Trash2 size={14} color={tokens.color.error} strokeWidth={1.8} />
                    <Text style={[styles.actionText, styles.deleteText]}>Glem</Text>
                  </Pressable>
                </View>
              </View>
            ))
          ) : (
            <StatusState title="Ingen memory til review" detail="Når Jarvis foreslår eller bruger memory, kan du styre den herfra." />
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
            <Eye size={16} color={tokens.color.fg2} strokeWidth={1.8} />
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
  summaryCopy: { flex: 1, gap: 2 },
  summaryText: { color: tokens.color.fg1, fontWeight: '700' },
  summaryMeta: { color: tokens.color.fg3, fontSize: 12, fontWeight: '700', textTransform: 'uppercase' },
  card: {
    backgroundColor: tokens.color.bg2,
    borderRadius: tokens.radius.lg,
    padding: tokens.spacing.lg,
    gap: 6
  },
  cardHead: { gap: tokens.spacing.sm },
  cardTitle: { color: tokens.color.fg1, fontWeight: '700', fontSize: 15 },
  contextPill: {
    alignSelf: 'flex-start',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    borderRadius: tokens.radius.pill,
    backgroundColor: tokens.color.accentGhost,
    paddingHorizontal: tokens.spacing.sm,
    paddingVertical: 4
  },
  contextText: { color: tokens.color.accentText, fontSize: 11, fontWeight: '800' },
  preview: { color: tokens.color.fg2, lineHeight: 20 },
  editBox: {
    minHeight: 86,
    color: tokens.color.fg1,
    backgroundColor: tokens.color.bg3,
    borderRadius: tokens.radius.md,
    padding: tokens.spacing.md,
    textAlignVertical: 'top'
  },
  actions: { flexDirection: 'row', flexWrap: 'wrap', gap: tokens.spacing.sm, marginTop: tokens.spacing.sm },
  actionBtn: {
    minHeight: 34,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: tokens.spacing.md,
    borderRadius: tokens.radius.pill,
    backgroundColor: tokens.color.bg3
  },
  actionText: { color: tokens.color.fg2, fontSize: 12, fontWeight: '700' },
  deleteText: { color: tokens.color.error },
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
