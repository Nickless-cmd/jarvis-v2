import { forwardRef, useImperativeHandle, useRef } from 'react'
import { FlatList, StyleSheet, View } from 'react-native'
import type { ContentBlock } from '../lib/sseProtocol'
import { denseBlocks } from '../lib/blockHelpers'
import type { ChatMessage } from '../lib/types'
import { tokens } from '../theme/tokens'
import { nextUserRow } from '../lib/messageNav'
import { MessageBubble } from './MessageBubble'
import { InlineToolGroup } from './InlineToolGroup'
import { ThinkingLabel } from './ThinkingLabel'
import { describeTool, describeToolResult } from '../lib/toolSummary'
import { countFromResult, type ToolItem } from '../lib/toolGroup'
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
  /** Vis «Tænker» nederst i tråden mens Jarvis arbejder (ChatGPT-mønsteret). */
  thinking?: boolean
  onResend?: (text: string) => void
  /** Kaldes ved scroll-aktivitet (bruges til at vise Save Rail mens man scroller). */
  onScrollActivity?: () => void
}

type Row =
  | { kind: 'msg'; key: string; message: ChatMessage }
  | { kind: 'tool'; key: string; content: string }
  | { kind: 'live-tool'; key: string; name: string; body: string; running: boolean }
  /** Én RUNDE værktøjsarbejde, foldet sammen til én linje. */
  | { kind: 'tool-group'; key: string; items: ToolItem[] }

/**
 * Fold sammenhængende værktøjsrækker sammen til én pr. runde.
 *
 * Codex-appen viser fortælling → ÉN linje → fortælling. Uden det her stablede
 * vi fire «Kører verify_file_contains…» oven på hinanden — samme information
 * fire gange, og tråden mistede sin ro. En tekstbesked afslutter runden.
 */
function groupToolRounds(rows: Row[]): Row[] {
  const out: Row[] = []
  let buf: Row[] = []
  const flush = () => {
    if (buf.length === 0) return
    const items: ToolItem[] = buf.map((r) =>
      r.kind === 'live-tool'
        ? { label: describeTool(r.name, r.body, r.running), running: r.running, tool: r.name }
        : {
            label: describeToolResult((r as { content: string }).content),
            running: false,
            tool: /\[([a-z_0-9]+)\]\s*:/i.exec((r as { content: string }).content)?.[1] ?? '',
            count: countFromResult((r as { content: string }).content)
          }
    )
    out.push({ kind: 'tool-group', key: `group-${buf[0]!.key}`, items })
    buf = []
  }
  for (const r of rows) {
    if (r.kind === 'tool' || r.kind === 'live-tool') buf.push(r)
    else {
      flush()
      out.push(r)
    }
  }
  flush()
  return out
}

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
  // denseBlocks: `blocks` kan være sparsomt (foldede tool_result-content-blokke
  // efterlader `undefined`-huller mellem indices). `for..of` over det rå array
  // ville ramme et hul og crashe på `b.type` → hele React-træet unmounter → sort
  // skærm. `b &&` er defense-in-depth.
  for (const b of denseBlocks(blocks)) {
    if (!b) continue
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
  { messages, blocks, onResend, onScrollActivity, thinking },
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

  const rows: Row[] = groupToolRounds([...persisted, ...buildStreamingRows(blocks)])

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
      // Inverteret liste: ListHeaderComponent tegnes NEDERST på skærmen —
      // altså lige efter den nyeste besked, præcis hvor ChatGPT viser
      // «Thinking». Det er derfor labelen ligger her og ikke over komponisten.
      ListHeaderComponent={thinking ? <ThinkingLabelRow /> : null}
      data={ordered}
      keyExtractor={(item) => item.key}
      onContentSizeChange={(_w, h) => { contentLenRef.current = h }}
      onScroll={onScrollActivity ? () => onScrollActivity() : undefined}
      scrollEventThrottle={120}
      onViewableItemsChanged={onViewable}
      onScrollToIndexFailed={(info) => {
        flatRef.current?.scrollToOffset({ offset: info.averageItemLength * info.index, animated: true })
      }}
      renderItem={({ item }) => {
        // Værktøjsarbejde er ÉN linje inde i samtalen — ikke et kort.
        // Målt i Codex-tråden: «</> Ændrede 16 filer ›». Det fulde output
        // ligger bag linjen, ikke foran den.
        if (item.kind === 'tool-group') return <InlineToolGroup items={item.items} />
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

function ThinkingLabelRow() {
  return (
    <View style={styles.thinkingRow}>
      <ThinkingLabel />
    </View>
  )
}

const styles = StyleSheet.create({
  thinkingRow: { paddingHorizontal: tokens.spacing.lg },
  content: {
    paddingVertical: tokens.spacing.sm
  }
})
