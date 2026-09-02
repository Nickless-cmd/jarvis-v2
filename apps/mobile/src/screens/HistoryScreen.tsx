import { FlatList, Pressable, StyleSheet, Text, View } from 'react-native'
import type { ApiConfig, ChatSession } from '../lib/types'
import { useSessions } from '../state/SessionContext'
import { tokens } from '../theme/tokens'

export function HistoryScreen({ config }: { config: ApiConfig }) {
  const { sessions, activeId, select } = useSessions()

  const renderItem = ({ item }: { item: ChatSession }) => (
    <Pressable
      accessibilityRole="button"
      onPress={() => void select(config, item.id)}
      style={[styles.row, item.id === activeId ? styles.activeRow : null]}
    >
      <Text style={styles.title}>{item.title || 'Ny samtale'}</Text>
      <Text style={styles.meta}>{item.message_count ?? 0} beskeder</Text>
    </Pressable>
  )

  return (
    <View style={styles.root}>
      <Text style={styles.heading}>Historik</Text>
      <FlatList
        data={sessions}
        keyExtractor={(item) => item.id}
        renderItem={renderItem}
        ListEmptyComponent={<Text style={styles.empty}>Ingen samtaler endnu</Text>}
      />
    </View>
  )
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: tokens.color.bg0,
    padding: tokens.spacing.md
  },
  heading: {
    color: tokens.color.fg1,
    fontSize: 22,
    fontWeight: '700',
    marginBottom: tokens.spacing.md
  },
  row: {
    padding: tokens.spacing.md,
    borderBottomColor: tokens.color.line,
    borderBottomWidth: 1
  },
  activeRow: {
    backgroundColor: tokens.color.bg1
  },
  title: {
    color: tokens.color.fg1,
    fontWeight: '700'
  },
  meta: {
    color: tokens.color.fg3,
    marginTop: tokens.spacing.xs
  },
  empty: {
    color: tokens.color.fg3,
    paddingVertical: tokens.spacing.xl,
    textAlign: 'center'
  }
})
