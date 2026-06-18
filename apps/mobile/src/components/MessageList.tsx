import { FlatList, StyleSheet } from 'react-native'
import type { ContentBlock } from '../lib/sseProtocol'
import type { ChatMessage } from '../lib/types'
import { tokens } from '../theme/tokens'
import { MessageBubble } from './MessageBubble'
import { ToolResultCard } from './ToolResultCard'

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

export function MessageList({
  messages,
  blocks,
  onResend
}: {
  messages: ChatMessage[]
  blocks: ContentBlock[]
  onResend?: (text: string) => void
}) {
  const persisted: Row[] = messages.map((m) =>
    m.role === 'tool'
      ? { kind: 'tool', key: m.id, content: m.content }
      : { kind: 'msg', key: m.id, message: m }
  )

  const rows: Row[] = [...persisted, ...buildStreamingRows(blocks)]

  // Inverteret liste: nyeste række sidder altid i bunden og er synlig fra start.
  const ordered = [...rows].reverse()

  return (
    <FlatList
      inverted
      data={ordered}
      keyExtractor={(item) => item.key}
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
}

const styles = StyleSheet.create({
  content: {
    paddingVertical: tokens.spacing.sm
  }
})
