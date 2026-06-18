import { FlatList, Modal, Pressable, StyleSheet, Text, View } from 'react-native'
import { tokens } from '../theme/tokens'

export interface ModelChoice {
  model: string // konkret id (owner) eller 'standard'|'pro' (member)
  providerChoice: string // provider (owner) — tom for member
  label: string
}

/**
 * Bottom-sheet model-vælger. Rolle-bevidst indhold leveres af kalderen:
 * owner får hele paletten, member får kun Standard/Pro (= ollama flash/pro).
 */
export function ModelPicker({
  open,
  choices,
  selectedLabel,
  onSelect,
  onClose
}: {
  open: boolean
  choices: ModelChoice[]
  selectedLabel?: string
  onSelect: (c: ModelChoice) => void
  onClose: () => void
}) {
  return (
    <Modal transparent visible={open} animationType="slide" onRequestClose={onClose}>
      <Pressable style={styles.scrim} onPress={onClose}>
        <Pressable style={styles.sheet} onPress={(e) => e.stopPropagation()}>
          <View style={styles.grabber} />
          <Text style={styles.title}>Model</Text>
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

const styles = StyleSheet.create({
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
  rowActive: { color: tokens.color.accent, fontWeight: '700' },
  check: { color: tokens.color.accent, fontSize: 16, fontWeight: '700' },
  empty: { color: tokens.color.fg3, paddingVertical: tokens.spacing.lg, textAlign: 'center' }
})
