import { useMemo, useState } from 'react'
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native'
import { ChevronDown, ChevronUp, Search, X } from 'lucide-react-native'
import { soegIBeskeder, flytTraef, type SoegeTraef } from '../lib/chatSearch'
import type { ChatMessage } from '../lib/types'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'

/** Søgning INDE i den åbne samtale.
 *
 *  Sidepanelet søger på tværs af samtaler — det her leder i den man står i.
 *  Den eneste vej tilbage til «hvad var det nu han sagde» har været at
 *  scrolle.
 *
 *  Feltet viser «3 af 12» og springer mellem træffene, frem for at filtrere
 *  listen. En filtreret samtale mister sin sammenhæng: man vil se svaret DÉR
 *  hvor det står, med det der kom før og efter.
 */

export interface ChatSearchBarProps {
  visible: boolean
  messages: ChatMessage[]
  onJump: (messageId: string) => void
  onClose: () => void
}

export function ChatSearchBar({ visible, messages, onJump, onClose }: ChatSearchBarProps) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  const [query, setQuery] = useState('')
  const [aktiv, setAktiv] = useState(0)

  const traef: SoegeTraef[] = useMemo(() => soegIBeskeder(messages, query), [messages, query])

  if (!visible) return null

  const spring = (retning: 1 | -1) => {
    if (!traef.length) return
    const n = flytTraef(traef.length, aktiv, retning)
    setAktiv(n)
    const t = traef[n]
    if (t) onJump(t.id)
  }

  const harQuery = query.trim().length >= 2

  return (
    <View style={styles.wrap} testID="chat-search">
      <View style={styles.field}>
        <Search size={15} color={tokens.color.fg3} strokeWidth={1.8} />
        <TextInput
          testID="chat-search-input"
          value={query}
          onChangeText={(v) => { setQuery(v); setAktiv(0) }}
          placeholder="Søg i denne samtale"
          placeholderTextColor={tokens.color.fg3}
          style={styles.input}
          autoFocus
          returnKeyType="search"
          onSubmitEditing={() => spring(1)}
        />
        {harQuery ? (
          <Text testID="chat-search-count" style={styles.count}>
            {traef.length ? `${aktiv + 1} af ${traef.length}` : 'ingen'}
          </Text>
        ) : null}
        <Pressable
          testID="chat-search-prev"
          accessibilityRole="button"
          accessibilityLabel="Forrige træf"
          disabled={!traef.length}
          onPress={() => spring(-1)}
          hitSlop={8}
          style={styles.iconBtn}
        >
          <ChevronUp size={17} color={traef.length ? tokens.color.fg2 : tokens.color.fg3} strokeWidth={1.8} />
        </Pressable>
        <Pressable
          testID="chat-search-next"
          accessibilityRole="button"
          accessibilityLabel="Næste træf"
          disabled={!traef.length}
          onPress={() => spring(1)}
          hitSlop={8}
          style={styles.iconBtn}
        >
          <ChevronDown size={17} color={traef.length ? tokens.color.fg2 : tokens.color.fg3} strokeWidth={1.8} />
        </Pressable>
        <Pressable
          testID="chat-search-close"
          accessibilityRole="button"
          accessibilityLabel="Luk søgning"
          onPress={() => { setQuery(''); setAktiv(0); onClose() }}
          hitSlop={8}
          style={styles.iconBtn}
        >
          <X size={17} color={tokens.color.fg2} strokeWidth={1.8} />
        </Pressable>
      </View>
      {harQuery && traef.length ? (
        <Text testID="chat-search-snippet" style={styles.snippet} numberOfLines={1}>
          {traef[aktiv]?.uddrag}
        </Text>
      ) : null}
    </View>
  )
}

const makestyles = (t: Theme) => StyleSheet.create({
  wrap: {
    backgroundColor: t.color.bg1, borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: t.color.line, paddingHorizontal: 12, paddingVertical: 8,
  },
  field: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  input: { flex: 1, color: t.color.fg1, fontSize: 15, paddingVertical: 4 },
  count: { color: t.color.fg3, fontSize: 12.5, fontVariant: ['tabular-nums'] },
  iconBtn: { padding: 2 },
  snippet: { color: t.color.fg3, fontSize: 12.5, marginTop: 5 },
})
