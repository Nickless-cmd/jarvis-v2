import { FlatList, StyleSheet, View } from 'react-native'
import type { ContentBlock } from '../lib/sseProtocol'
import type { ChatMessage } from '../lib/types'
import { tokens } from '../theme/tokens'
import { MessageBubble } from './MessageBubble'

export function MessageList({
  messages,
  blocks
}: {
  messages: ChatMessage[]
  blocks: ContentBlock[]
}) {
  const assistantText = blocks
    .map((block) => {
      if (block.type === 'text') return block.text
      if (block.type === 'thinking') return block.thinking
      return ''
    })
    .join('')

  const data = assistantText
    ? [
        ...messages,
        {
          id: 'streaming',
          role: 'assistant' as const,
          content: assistantText,
          created_at: new Date().toISOString()
        }
      ]
    : messages

  return (
    <FlatList
      data={data}
      keyExtractor={(item) => item.id}
      renderItem={({ item }) => <MessageBubble message={item} />}
      contentContainerStyle={styles.content}
      keyboardShouldPersistTaps="handled"
    />
  )
}

const styles = StyleSheet.create({
  content: {
    paddingVertical: tokens.spacing.sm
  }
})
