import { forwardRef, useImperativeHandle, useRef } from 'react'
import { FlatList, StyleSheet, Text, View } from 'react-native'
import type { ContentBlock } from '../lib/sseProtocol'
import { denseBlocks } from '../lib/blockHelpers'
import type { ChatMessage } from '../lib/types'
import type { PersistedBlock } from '../lib/persistedBlocks'
import { tokens } from '../theme/tokens'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'
import { nextUserRow } from '../lib/messageNav'
import { MessageBubble } from './MessageBubble'
import { InlineToolGroup } from './InlineToolGroup'
import { ThinkingLabel } from './ThinkingLabel'
import { toolDiff } from '../lib/toolDiff'
import { describeTool, describeToolResult } from '../lib/toolSummary'
import { countFromResult, type ToolItem } from '../lib/toolGroup'
import { attachmentBlocks, hasOrdering, parseBlocks, thinkingBlock } from '../lib/persistedBlocks'
import { threadBlocks } from '../lib/persistedBlocks'
import { ThinkingSummary } from './ThinkingSummary'
import { MessageAttachments } from './MessageAttachments'
import { ToolResultCard } from './ToolResultCard'

export interface MessageListHandle {
  jumpTop: () => void       // ældste besked
  jumpBottom: () => void    // nyeste besked
  jumpOlderUser: () => void // forrige bruger-besked (op i historik)
  jumpNewerUser: () => void // næste bruger-besked (ned mod nyeste)
  scrubTo: (fraction: number) => void // 0=nyeste, 1=ældste
  /** Spring til en besked ved dens id. Til søgning: man finder et træf i en
   *  liste og vil se det i sin sammenhæng, ikke bare læse uddraget. */
  jumpToMessage: (messageId: string) => void
}

interface MessageListProps {
  messages: ChatMessage[]
  blocks: ContentBlock[]
  /** Vis «Tænker» nederst i tråden mens Jarvis arbejder (ChatGPT-mønsteret). */
  thinking?: boolean
  /**
   * Ekstra plads i bunden mens tastaturet er fremme.
   *
   * Komponisten svæver og stiger med tastaturet — uden dette blev tråden
   * stående, og de nyeste linjer forsvandt bag den. Nu følger indholdet med op.
   */
  bottomInset?: number
  onResend?: (text: string) => void
  /** Id'er på fastgjorte beskeder. Styrer ikonet i besked-menuen. */
  pins?: string[]
  /** Slå fast/løs på en besked. Udeladt → punktet vises ikke. */
  onTogglePin?: (messageId: string) => void
  /** Gem et af hans svar i hukommelsen. Udeladt → punktet vises ikke. */
  onSaveMemory?: (message: ChatMessage) => void
  /**
   * Kaldes med afstanden fra bunden af traaden.
   *
   * Listen er INVERTERET, saa offset 0 = nyeste besked nederst. En voksende
   * offset betyder at man har rullet OP i historikken. Vi sender tallet videre
   * i stedet for bare «der skete scroll», fordi rul-til-bunden-knappen skal
   * kende positionen — ikke aktiviteten.
   */
  onScrollOffset?: (fromBottom: number) => void
}

type Row =
  | { kind: 'msg'; key: string; message: ChatMessage; hideActions?: boolean
      // Turens blokke følger med den SIDSTE tekstboble, så «Kilder» kan bygges
      // af det han faktisk slog op. Uden dem faldt kilderne væk i samme sekund
      // streamen stoppede.
      kildeBlokke?: PersistedBlock[] | null }
  /** «Tænkte i 14 s ›» — foldet spor af turens overvejelse. */
  | { kind: 'thinking'; key: string; seconds?: number; text?: string }
  /** Billeder/filer sendt MED en brugerbesked, tegnet over boblen. */
  | { kind: 'attachments'; key: string; items: PersistedBlock[] }
  | { kind: 'tool'; key: string; content: string }
  | { kind: 'live-tool'; key: string; name: string; body: string; running: boolean; etiket?: string; diff?: { tilfoejet: number; fjernet: number } | null }
  /** Én RUNDE værktøjsarbejde, foldet sammen til én linje. */
  | { kind: 'tool-group'; key: string; items: ToolItem[] }
  /**
   * Kompakteringens markør — intern bogholderi, ikke en samtale-besked.
   * Tegnes som én diskret linje. Serveren trimmer dens indhold; uden denne gren
   * faldt rollen i default og blev tegnet som en almindelig boble med hele den
   * serialiserede transcript (målt 111k tegn).
   */
  | { kind: 'compact-marker'; key: string; content: string }

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
        ? { label: r.etiket || describeTool(r.name, r.body, r.running), running: r.running, tool: r.name, diff: r.diff ?? null }
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
        running: b.status !== 'done' && b.status !== 'error',
        // Linjetallene for DETTE kald. De ligger allerede i argumenterne;
        // serveren skulle ikke spoerges om noget klienten har.
        diff: toolDiff(b.name, b.input),
        // Serverens egen etiket, brugt ORDRET. En foreløbig række har ingen
        // argumenter endnu — `describeTool` ville sige «Kører bash…» og tabe
        // netop dét der gør ventetiden forståelig. Etiketten findes allerede
        // i `working_step`; den skulle bare ikke smides væk.
        etiket: b.foreloebig?.etiket
      })
    }
  }
  flush()
  return rows
}

export const MessageList = forwardRef<MessageListHandle, MessageListProps>(function MessageList(
  { messages, blocks, onResend, onScrollOffset, thinking, bottomInset = 0, pins, onTogglePin, onSaveMemory },
  ref
) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  const flatRef = useRef<FlatList>(null)
  const visibleRef = useRef(0)   // ordered-index øverst i viewport (inverted)
  const contentLenRef = useRef(0)
  // Stabil callback — RN kaster hvis onViewableItemsChanged ændrer identitet on-the-fly.
  const onViewable = useRef(({ viewableItems }: { viewableItems: Array<{ index: number | null }> }) => {
    const first = viewableItems[0]
    if (first && first.index != null) visibleRef.current = first.index
  }).current

  /**
   * Har en gemt assistent-tur strukturerede blokke MED rækkefølge, bruges de
   * frem for den flade `content`. Ellers ville skærmen stadig vise den gamle
   * klump — værktøjer først, alle synteser smeltet sammen — selv om serveren
   * nu gemmer den rigtige orden.
   *
   * De løse `tool`-beskeder i samme tur er de SAMME resultater; de springes
   * over, så de ikke tælles to gange.
   */
  const persisted: Row[] = []
  let skipToolRows = false
  for (let i = messages.length - 1; i >= 0; i--) {
    const m = messages[i]!
    if (m.role === 'assistant') {
      const blocks = parseBlocks(m)
      const think = thinkingBlock(blocks)
      // UDGIVNE FILER, lagt fra sig FOER grenene nedenfor. Foerste forsoeg lagde
      // dem i en egen gren til sidst — men baade ordre-grenen og taenke-grenen
      // `continue`r foer den, altsaa paa de fleste ture, og filen forsvandt.
      //
      // `unshift` saetter forrest, og listen bygges bagfra: den SIDST
      // unshiftede staar oeverst. Filerne laegges derfor foerst, saa turens
      // tekst ender OVER dem. En fil er et resultat og hoerer under det den
      // handler om — modsat brugerens billeder, der ligger over boblen fordi
      // billedet dér ofte ER beskeden.
      const afiler = attachmentBlocks(blocks)
      if (afiler.length) {
        persisted.unshift({ kind: 'attachments', key: `${m.id}-pub`, items: afiler })
      }
      if (hasOrdering(blocks)) {
        const expanded: Row[] = []
        if (think) {
          expanded.push({
            kind: 'thinking', key: `${m.id}-think`,
            seconds: think.seconds, text: think.text
          })
        }
        const thread = threadBlocks(blocks!)
        const lastTextIdx = thread.reduce(
          (acc, b, i) => (b.type === 'text' && (b.text ?? '').trim() ? i : acc),
          -1
        )
        thread.forEach((b, bi) => {
          if (b.type === 'text' && (b.text ?? '').trim()) {
            expanded.push({
              kind: 'msg',
              key: `${m.id}-b${bi}`,
              message: { ...m, id: `${m.id}-b${bi}`, content: (b.text ?? '').trim() },
              // Kun turens sidste afsnit bærer kopiér/oplæs — ellers gentages
              // rækken efter hvert afsnit og tråden bliver støjende. Samme
              // sted hører kilderne hjemme: én gang pr. tur, i bunden.
              hideActions: bi !== lastTextIdx,
              kildeBlokke: bi === lastTextIdx ? blocks : null
            })
          } else if (b.type === 'tool_use') {
            expanded.push({
              kind: 'live-tool',
              key: `${m.id}-t${bi}`,
              name: String(b.name ?? ''),
              body: JSON.stringify(b.input ?? {}),
              running: false
            })
          }
        })
        persisted.unshift(...expanded)
        skipToolRows = true
        continue
      }
      skipToolRows = false
      // En tur uden værktøjer har ingen «rækkefølge» at udfolde, men han kan
      // sagtens have tænkt. Uden dette forsvandt linjen på netop de turer hvor
      // tænkningen ofte er mest interessant: de rene svar.
      if (think) {
        persisted.unshift({ kind: 'msg', key: m.id, message: m, kildeBlokke: blocks })
        persisted.unshift({
          kind: 'thinking', key: `${m.id}-think`,
          seconds: think.seconds, text: think.text
        })
        continue
      }
    }
    if (m.role === 'user') {
      skipToolRows = false
      const ublocks = attachmentBlocks(parseBlocks(m))
      if (ublocks.length) {
        persisted.unshift({ kind: 'msg', key: m.id, message: m, kildeBlokke: blocks })
        // Billederne ligger OVER boblen, som i referencen — ikke inde i den.
        persisted.unshift({ kind: 'attachments', key: `${m.id}-att`, items: ublocks })
        continue
      }
    }
    if (m.role === 'tool') {
      if (skipToolRows) continue
      persisted.unshift({ kind: 'tool', key: m.id, content: m.content })
      continue
    }
    if (m.role === 'compact_marker') {
      // Intern bogholderi, ikke en samtale-besked. Uden denne gren faldt rollen
      // i default nedenfor og blev tegnet som en almindelig boble — med hele den
      // serialiserede transcript som indhold (målt 111k tegn: `[Bjørn] …`,
      // `[tool:tool] …`, «Use read_tool_result with result_id=…»).
      skipToolRows = false
      persisted.unshift({ kind: 'compact-marker', key: m.id, content: m.content })
      continue
    }
    persisted.unshift({ kind: 'msg', key: m.id, message: m })
  }

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
    jumpToMessage: (messageId: string) => {
      const i = ordered.findIndex((r) => r.kind === 'msg' && String(r.message.id) === String(messageId))
      if (i < 0) return
      // viewPosition 0.3: træffet lander lidt under toppen, så man kan se
      // linjerne FØR det — en besked uden sin optakt er svær at genkende.
      flatRef.current?.scrollToIndex({ index: i, animated: true, viewPosition: 0.3 })
    },
  }), [userFlags, ordered])

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
      onScroll={onScrollOffset ? (e) => onScrollOffset(e.nativeEvent.contentOffset.y) : undefined}
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
        if (item.kind === 'thinking') {
          return <ThinkingSummary seconds={item.seconds} text={item.text} />
        }
        if (item.kind === 'attachments') return <MessageAttachments items={item.items} />
        if (item.kind === 'compact-marker') return <CompactMarkerRow content={item.content} />
        return (
          <MessageBubble
            message={item.message}
            kildeBlokke={item.kildeBlokke}
            onResend={item.message.role === 'user' ? onResend : undefined}
            pinned={pins?.includes(String(item.message.id))}
            onTogglePin={onTogglePin ? () => onTogglePin(String(item.message.id)) : undefined}
            onSaveMemory={
              // Kun hans egne svar. En hukommelse af Bjørns egen besked er
              // bare et ekko — det er svaret der er værd at gemme.
              onSaveMemory && item.message.role === 'assistant'
                ? () => onSaveMemory(item.message)
                : undefined
            }
            hideActions={item.hideActions}
          />
        )
      }}
      // INVERTERET: paddingTop lander visuelt NEDERST — det er dér tastaturet
      // og komponisten æder plads.
      contentContainerStyle={[styles.content, { paddingTop: BOTTOM_CLEARANCE + bottomInset }]}
      keyboardShouldPersistTaps="handled"
    />
  )
})

function ThinkingLabelRow() {
  const styles = useStyles(makestyles)
  return (
    <View style={styles.thinkingRow}>
      <ThinkingLabel />
    </View>
  )
}

/**
 * Kompakteringens markør. Én diskret linje — ikke en boble.
 *
 * Markøren er intern bogholderi: den fortæller at ældre beskeder er blevet
 * foldet sammen til en summary. Den er værd at vise (ellers forstår man ikke
 * hvorfor historikken ændrede sig), men den er ikke en samtale-besked og skal
 * ikke se ud som en. Samme form som desktop-klienten (jarvisx MessageList).
 */
function CompactMarkerRow({ content }: { content: string }) {
  const styles = useStyles(makestyles)
  return (
    <View style={styles.compactMarkerRow} testID="compact-marker">
      <Text style={styles.compactMarkerText}>{content}</Text>
    </View>
  )
}

/**
 * INVERTERET liste: indholdet er vendt 180°, så contentContainer'ens
 * `paddingTop` lander VISUELT NEDERST og `paddingBottom` visuelt øverst.
 * Det er kontraintuitivt nok til at være værd at skrive ned.
 *
 * Tallene er plads til de to svævende bjælker. Bunden er 124 og ikke bare
 * komponistens egen højde: handlingsrækken (kopiér/læs op) hænger UNDER
 * turens sidste afsnit, og med for lidt luft gled netop de to ikoner ind bag
 * komponisten. Man skal måle til bunden af det SIDSTE element, ikke af teksten.
 */
const BOTTOM_CLEARANCE = 124
const TOP_CLEARANCE = 72

const makestyles = (tokens: Theme) => StyleSheet.create({
  thinkingRow: { paddingHorizontal: tokens.spacing.lg },
  // Kompakterings-markøren: diskret, tonet i warn — samme udtryk som desktop.
  compactMarkerRow: {
    marginHorizontal: tokens.spacing.lg,
    marginVertical: tokens.spacing.sm,
    paddingVertical: tokens.spacing.sm,
    paddingHorizontal: tokens.spacing.md,
    borderRadius: tokens.radius.sm,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: tokens.color.warn + '33',
    backgroundColor: tokens.color.warn + '0D'
  },
  compactMarkerText: {
    fontSize: 11,
    fontStyle: 'italic',
    lineHeight: 15,
    color: tokens.color.warn,
    opacity: 0.8
  },
  content: {
    // paddingTop sættes dynamisk (BOTTOM_CLEARANCE + tastaturhøjde) — se
    // contentContainerStyle. Kun den øverste er konstant.
    paddingBottom: TOP_CLEARANCE
  }
})
