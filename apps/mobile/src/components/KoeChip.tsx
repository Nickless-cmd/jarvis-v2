import { useState } from 'react'
import { Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native'
import { ArrowDown, ArrowUp, Check, Pencil, Send, X } from 'lucide-react-native'
import type { FollowupItem } from '../lib/useFollowupQueue'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'

/** Ventende follow-ups for denne samtale. Handlingerne rører aldrig selve runnet,
 * bortset fra «Send nu», der bruger serverens mid-flight steer. */
export function KoeChip({ items, busy, canSteer, error, onEdit, onRemove, onMove, onSendNow }: {
  items: FollowupItem[]
  busy: boolean
  canSteer: boolean
  error?: string
  onEdit: (id: number, text: string) => void
  onRemove: (id: number) => void
  onMove: (id: number, direction: -1 | 1) => void
  onSendNow: (id: number) => void
}) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [draft, setDraft] = useState('')
  if (!items.length && !error) return null
  return (
    <View style={styles.shell} testID="koe-chip">
      <Text style={styles.heading}>I kø · {items.length}</Text>
      <ScrollView style={styles.list} keyboardShouldPersistTaps="always">
        {items.map((item, index) => (
          <View key={item.id} style={styles.row} testID={`koe-item-${item.id}`}>
            {editingId === item.id ? (
              <TextInput
                style={styles.input} value={draft} onChangeText={setDraft}
                multiline autoFocus accessibilityLabel="Rediger follow-up-tekst"
              />
            ) : (
              <Text style={styles.text} numberOfLines={2}>{item.text || 'Vedhæftning'}{item.attachmentIds?.length ? ` · ${item.attachmentIds.length} fil(er)` : ''}</Text>
            )}
            <View style={styles.actions}>
              {editingId === item.id ? (
                <>
                  <Pressable accessibilityRole="button" accessibilityLabel="Gem ændring" disabled={!draft.trim() && !item.attachmentIds?.length}
                    onPress={() => { onEdit(item.id, draft); setEditingId(null) }} hitSlop={8}>
                    <Check size={18} color={tokens.color.accent} />
                  </Pressable>
                  <Pressable accessibilityRole="button" accessibilityLabel="Fortryd redigering" onPress={() => setEditingId(null)} hitSlop={8}>
                    <X size={18} color={tokens.color.fg3} />
                  </Pressable>
                </>
              ) : (
                <>
                  <Pressable accessibilityRole="button" accessibilityLabel="Rediger follow-up" onPress={() => { setEditingId(item.id); setDraft(item.text) }} hitSlop={8}>
                    <Pencil size={17} color={tokens.color.fg2} />
                  </Pressable>
                  <Pressable accessibilityRole="button" accessibilityLabel="Flyt op" disabled={index === 0} onPress={() => onMove(item.id, -1)} hitSlop={8}>
                    <ArrowUp size={17} color={index === 0 ? tokens.color.fg3 : tokens.color.fg2} />
                  </Pressable>
                  <Pressable accessibilityRole="button" accessibilityLabel="Flyt ned" disabled={index === items.length - 1} onPress={() => onMove(item.id, 1)} hitSlop={8}>
                    <ArrowDown size={17} color={index === items.length - 1 ? tokens.color.fg3 : tokens.color.fg2} />
                  </Pressable>
                  <Pressable accessibilityRole="button" accessibilityLabel={busy ? 'Send nu til aktivt run' : 'Send nu'}
                    disabled={busy && (!canSteer || !!item.attachmentIds?.length)} onPress={() => onSendNow(item.id)} hitSlop={8}>
                    <Send size={17} color={!busy || canSteer && !item.attachmentIds?.length ? tokens.color.accent : tokens.color.fg3} />
                  </Pressable>
                  <Pressable accessibilityRole="button" accessibilityLabel="Fjern fra kø" onPress={() => onRemove(item.id)} hitSlop={8}>
                    <X size={18} color={tokens.color.fg3} />
                  </Pressable>
                </>
              )}
            </View>
          </View>
        ))}
      </ScrollView>
      {error ? <Text style={styles.error}>{error}</Text> : null}
    </View>
  )
}

const makestyles = (tokens: Theme) => StyleSheet.create({
  shell: {
    marginHorizontal: tokens.spacing.lg, marginBottom: tokens.spacing.xs,
    paddingHorizontal: tokens.spacing.md, paddingVertical: 8,
    borderRadius: 12, borderWidth: StyleSheet.hairlineWidth, borderColor: tokens.color.line,
    backgroundColor: tokens.color.bg2,
  },
  heading: { color: tokens.color.accent, fontSize: 13, fontWeight: '600', marginBottom: 4 },
  list: { maxHeight: 180 },
  row: { borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: tokens.color.line, paddingVertical: 6 },
  text: { color: tokens.color.fg2, fontSize: 13 },
  actions: { flexDirection: 'row', justifyContent: 'flex-end', alignItems: 'center', gap: 18, marginTop: 6 },
  input: { color: tokens.color.fg1, borderWidth: StyleSheet.hairlineWidth, borderColor: tokens.color.line, borderRadius: 6, padding: 6, minHeight: 38 },
  error: { color: tokens.color.error, fontSize: 12, marginTop: 4 },
})
