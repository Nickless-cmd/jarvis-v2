import { FlatList, Modal, Pressable, StyleSheet, Text, View } from 'react-native'
import { tokens } from '../theme/tokens'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'

export interface ModelChoice {
  model: string // konkret id (owner) eller 'standard'|'pro' (member)
  providerChoice: string // provider (owner) — tom for member
  label: string
}

export type ThinkingMode = 'think' | 'fast'
export type ApprovalMode = 'ask' | 'trust'

/**
 * Bottom-sheet model-vælger. Rolle-bevidst indhold leveres af kalderen:
 * owner får hele paletten, member får kun Standard/Pro (= ollama flash/pro).
 */
export function ModelPicker({
  open,
  choices,
  selectedLabel,
  thinkingMode,
  approvalMode,
  onThinkingModeChange,
  onApprovalModeChange,
  onSelect,
  onClose
}: {
  open: boolean
  choices: ModelChoice[]
  selectedLabel?: string
  thinkingMode?: ThinkingMode
  approvalMode?: ApprovalMode
  onThinkingModeChange?: (mode: ThinkingMode) => void
  onApprovalModeChange?: (mode: ApprovalMode) => void
  onSelect: (c: ModelChoice) => void
  onClose: () => void
}) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  return (
    <Modal transparent visible={open} animationType="slide" onRequestClose={onClose}>
      <Pressable style={styles.scrim} onPress={onClose}>
        <Pressable style={styles.sheet} onPress={(e) => e.stopPropagation()}>
          <View style={styles.grabber} />
          <Text style={styles.title}>Model</Text>
          {onThinkingModeChange ? (
            <>
              <Text style={styles.subTitle}>Tænkning</Text>
              <View style={styles.segmentRow}>
                {(['think', 'fast'] as ThinkingMode[]).map((m) => (
                  <Pressable
                    key={m}
                    accessibilityRole="button"
                    onPress={() => onThinkingModeChange(m)}
                    style={[styles.segment, thinkingMode === m && styles.segmentOn]}
                  >
                    <Text style={[styles.segmentText, thinkingMode === m && styles.segmentTextOn]}>
                      {m === 'think' ? 'Think' : 'Fast'}
                    </Text>
                  </Pressable>
                ))}
              </View>
            </>
          ) : null}
          {onApprovalModeChange ? (
            <>
              <Text style={styles.subTitle}>Godkendelser</Text>
              <View style={styles.segmentRow}>
                {(['ask', 'trust'] as ApprovalMode[]).map((m) => (
                  <Pressable
                    key={m}
                    accessibilityRole="button"
                    onPress={() => onApprovalModeChange(m)}
                    style={[styles.segment, approvalMode === m && styles.segmentOn]}
                  >
                    <Text style={[styles.segmentText, approvalMode === m && styles.segmentTextOn]}>
                      {m === 'ask' ? 'Ask' : 'Trust'}
                    </Text>
                  </Pressable>
                ))}
              </View>
            </>
          ) : null}
          <FlatList
            data={choices}
            keyExtractor={(c) => c.label}
            style={styles.list}
            renderItem={({ item }) => {
              const active = item.label === selectedLabel
              return (
                <Pressable
                  accessibilityRole="button"
                  onPress={() => {
                    onSelect(item)
                    onClose()
                  }}
                  style={({ pressed }) => [styles.row, pressed ? styles.pressed : null]}
                >
                  <Text style={[styles.rowLabel, active ? styles.rowActive : null]} numberOfLines={1}>
                    {item.label}
                  </Text>
                  {active ? <Text style={styles.check}>✓</Text> : null}
                </Pressable>
              )
            }}
            ListEmptyComponent={<Text style={styles.empty}>Ingen modeller tilgængelige</Text>}
          />
        </Pressable>
      </Pressable>
    </Modal>
  )
}

const makestyles = (tokens: Theme) => StyleSheet.create({
  scrim: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'flex-end' },
  sheet: {
    backgroundColor: tokens.color.bg1,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    paddingHorizontal: tokens.spacing.lg,
    paddingTop: tokens.spacing.sm,
    paddingBottom: tokens.spacing.xl,
    maxHeight: '70%'
  },
  grabber: {
    alignSelf: 'center',
    width: 40,
    height: 4,
    borderRadius: 2,
    backgroundColor: tokens.color.bg3,
    marginBottom: tokens.spacing.md
  },
  title: { color: tokens.color.fg3, fontSize: 12, fontWeight: '700', textTransform: 'uppercase', marginBottom: tokens.spacing.sm },
  subTitle: { color: tokens.color.fg3, fontSize: 11, fontWeight: '700', textTransform: 'uppercase', marginTop: tokens.spacing.sm, marginBottom: 6 },
  segmentRow: { flexDirection: 'row', gap: tokens.spacing.sm, marginBottom: tokens.spacing.xs },
  segment: {
    flex: 1,
    minHeight: 38,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: tokens.radius.md,
    backgroundColor: tokens.color.bg2
  },
  segmentOn: { backgroundColor: tokens.color.accent },
  segmentText: { color: tokens.color.fg2, fontWeight: '700' },
  segmentTextOn: { color: tokens.color.bg0 },
  list: { flexGrow: 0 },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: tokens.spacing.md,
    borderBottomColor: tokens.color.line,
    borderBottomWidth: 1
  },
  pressed: { opacity: 0.7 },
  rowLabel: { color: tokens.color.fg1, fontSize: 16, flexShrink: 1 },
  rowActive: { color: tokens.color.accentText, fontWeight: '700' },
  check: { color: tokens.color.accentText, fontSize: 16, fontWeight: '700' },
  empty: { color: tokens.color.fg3, paddingVertical: tokens.spacing.lg, textAlign: 'center' }
})
