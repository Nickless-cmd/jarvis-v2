import { forwardRef, useImperativeHandle, useRef } from 'react'
import { FlatList, StyleSheet } from 'react-native'
import type { ContentBlock } from '../lib/sseProtocol'
import type { ChatMessage } from '../lib/types'
import { tokens } from '../theme/tokens'
import { nextUserRow } from '../lib/messageNav'
import { MessageBubble } from './MessageBubble'
import { ToolResultCard } from './ToolResultCard'

export interface MessageListHandle {
  jumpTop: () => void       // ældste besked
  jumpBottom: () => void    // nyeste besked
  jumpOlderUser: () => void // forrige bruger-besked (op i historik)
  jumpNewerUser: () => void // næste bruger-besked (ned mod nyeste)
  scrubTo: (fraction: number) => void // 0=nyeste, 1=ældste
}

interface MessageListProps {
  messages: ChatMessage[]
  blocks: ContentBlock[]
  onResend?: (text: string) => void
}

type Row =
  | { kind: 'msg'; key: string; message: ChatMessage }
  | { kind: 'tool'; key: string; content: string }
  | { kind: 'live-tool'; key: string; name: string; body: string; running: boolean }

function toolBody(block: Extract<ContentBlock, { type: 'tool_use' }>): string {
  if (block.partialJson) return block.partialJson
  try {
    return Object.keys(block.input ?? {}).length ? JSON.stringify(block.input, null, 2) : ''
  } catch {
    return ''
  }
}

/**
 * Bygger streaming-rækker af de live blocks: tekst/thinking samles til
 * tekstbobler, og tool_use-blokke renderes som live tool-kort (fix: tidligere
 * blev tool-blokke filtreret væk under streaming → resultater dukkede først op
 * efter app-genstart fra persisterede beskeder).
 */
function buildStreamingRows(blocks: ContentBlock[]): Row[] {
  const rows: Row[] = []
  let textBuf = ''
  let i = 0
  const flush = () => {
    if (textBuf.trim()) {
      rows.push({
        kind: 'msg',
        key: `stream-text-${i}`,
        message: {
          id: `stream-text-${i}`,
          role: 'assistant',
          content: textBuf,
          created_at: new Date().toISOString()
        }
      })
      textBuf = ''
    }
    i += 1
  }
  for (const b of blocks) {
    if (b.type === 'text') textBuf += b.text
    else if (b.type === 'thinking') textBuf += b.thinking
    else if (b.type === 'tool_use') {
      flush()
      rows.push({
        kind: 'live-tool',
        key: `stream-tool-${b.id || i}`,
        name: b.name,
        body: toolBody(b),
        running: b.status !== 'done' && b.status !== 'error'
      })
    }
  }
  flush()
  return rows
}

export const MessageList = forwardRef<MessageListHandle, MessageListProps>(function MessageList(
  { messages, blocks, onResend },
  ref
) {
  const flatRef = useRef<FlatList>(null)
  const visibleRef = useRef(0)   // ordered-index øverst i viewport (inverted)
  const contentLenRef = useRef(0)
  // Stabil callback — RN kaster hvis onViewableItemsChanged ændrer identitet on-the-fly.
  const onViewable = useRef(({ viewableItems }: { viewableItems: Array<{ index: number | null }> }) => {
    const first = viewableItems[0]
    if (first && first.index != null) visibleRef.current = first.index
  }).current

  const persisted: Row[] = messages.map((m) =>
    m.role === 'tool'
      ? { kind: 'tool', key: m.id, content: m.content }
      : { kind: 'msg', key: m.id, message: m }
  )

  const rows: Row[] = [...persisted, ...buildStreamingRows(blocks)]

  // Inverteret liste: nyeste række sidder altid i bunden og er synlig fra start.
  const ordered = [...rows].reverse()
  // I inverted liste: HØJERE index = ÆLDRE besked, LAVERE index = NYERE.
  const userFlags = ordered.map((r) => r.kind === 'msg' && r.message.role === 'user')

  useImperativeHandle(ref, () => ({
    jumpTop: () => flatRef.current?.scrollToEnd({ animated: true }),
    jumpBottom: () => flatRef.current?.scrollToOffset({ offset: 0, animated: true }),
    jumpOlderUser: () => {
      const i = nextUserRow(userFlags, visibleRef.current, 1)
      if (i != null) flatRef.current?.scrollToIndex({ index: i, animated: true, viewPosition: 0 })
    },
    jumpNewerUser: () => {
      const i = nextUserRow(userFlags, visibleRef.current, -1)
      if (i != null) flatRef.current?.scrollToIndex({ index: i, animated: true, viewPosition: 0 })
    },
    scrubTo: (f: number) => flatRef.current?.scrollToOffset({ offset: f * contentLenRef.current, animated: false }),
  }), [userFlags])

  return (
    <FlatList
      ref={flatRef}
      inverted
      data={ordered}
      keyExtractor={(item) => item.key}
      onContentSizeChange={(_w, h) => { contentLenRef.current = h }}
      onViewableItemsChanged={onViewable}
      onScrollToIndexFailed={(info) => {
        flatRef.current?.scrollToOffset({ offset: info.averageItemLength * info.index, animated: true })
      }}
      renderItem={({ item }) => {
        if (item.kind === 'tool') return <ToolResultCard content={item.content} />
        if (item.kind === 'live-tool')
          return <ToolResultCard toolName={item.name} body={item.body} running={item.running} />
        return (
          <MessageBubble
            message={item.message}
            onResend={item.message.role === 'user' ? onResend : undefined}
          />
        )
      }}
      contentContainerStyle={styles.content}
      keyboardShouldPersistTaps="handled"
    />
  )
})

const styles = StyleSheet.create({
  content: {
    paddingVertical: tokens.spacing.sm
  }
})
