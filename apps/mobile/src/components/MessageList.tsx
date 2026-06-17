import { useRef } from 'react'
import { FlatList, StyleSheet, type NativeScrollEvent, type NativeSyntheticEvent } from 'react-native'
import type { ContentBlock } from '../lib/sseProtocol'
import type { ChatMessage } from '../lib/types'
import { tokens } from '../theme/tokens'
import { MessageBubble } from './MessageBubble'

// Hvor tæt på bunden (px) man skal være for at "følge" nye beskeder.
const AT_BOTTOM_THRESHOLD = 80

export function MessageList({
  messages,
  blocks
}: {
  messages: ChatMessage[]
  blocks: ContentBlock[]
}) {
  const listRef = useRef<FlatList>(null)
  // Følg bunden som standard (opstart + under streaming). Sættes til false
  // når brugeren scroller op for at læse gammelt — så river vi ham ikke ned.
  const atBottom = useRef(true)
  const didInitialScroll = useRef(false)

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

  const onScroll = (e: NativeSyntheticEvent<NativeScrollEvent>) => {
    const { contentOffset, contentSize, layoutMeasurement } = e.nativeEvent
    const distanceFromBottom = contentSize.height - (contentOffset.y + layoutMeasurement.height)
    atBottom.current = distanceFromBottom <= AT_BOTTOM_THRESHOLD
  }

  const onContentSizeChange = () => {
    // Første layout: hop direkte til nyeste besked (ingen animation).
    if (!didInitialScroll.current) {
      didInitialScroll.current = true
      listRef.current?.scrollToEnd({ animated: false })
      return
    }
    // Senere vækst (nye beskeder / streaming): følg kun hvis brugeren er i bunden.
    if (atBottom.current) {
      listRef.current?.scrollToEnd({ animated: true })
    }
  }

  return (
    <FlatList
      ref={listRef}
      data={data}
      keyExtractor={(item) => item.id}
      renderItem={({ item }) => <MessageBubble message={item} />}
      contentContainerStyle={styles.content}
      keyboardShouldPersistTaps="handled"
      onScroll={onScroll}
      scrollEventThrottle={64}
      onContentSizeChange={onContentSizeChange}
    />
  )
}

const styles = StyleSheet.create({
  content: {
    paddingVertical: tokens.spacing.sm
  }
})
