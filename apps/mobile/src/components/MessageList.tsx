import { forwardRef, useEffect, useImperativeHandle, useMemo, useRef, useState } from 'react'
import { useRaekkeFn, useSenesteFn } from '../lib/stabileHandlinger'
import { FlatList, Pressable, StyleSheet, Text, View } from 'react-native'
import { saetStickyPrompt } from '../lib/stickyPrompt'
import type { ContentBlock } from '../lib/sseProtocol'
import { denseBlocks } from '../lib/blockHelpers'
import type { ChatMessage } from '../lib/types'
import type { PersistedBlock } from '../lib/persistedBlocks'
import { tokens } from '../theme/tokens'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'
import { nextUserRow } from '../lib/messageNav'
import { MessageBubble } from './MessageBubble'
import { InlineToolGroup } from './InlineToolGroup'
import { formatTid } from './InlineToolGroup'
import { TurnHeader } from './TurnHeader'
import { aendringAf, diffFraResultat, toolDiff } from '../lib/toolDiff'
import { describeTool, describeToolResult } from '../lib/toolSummary'
import { countFromResult, summarizeRound, type ToolItem } from '../lib/toolGroup'
import { SKILL_VAERKTOEJER, type SkillKald } from '../lib/skillLinje'
import { SkillFladeLinje, SkillLinje, type SkillFladeMatch } from './SkillLinje'
import { TankeResumeLinje } from './TankeResumeLinje'
import type { Visning } from '../lib/visning'
import { attachmentBlocks, gemteEtiketter, hasOrdering, parseBlocks, thinkingBlock, gemteResumeer } from '../lib/persistedBlocks'
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
  /** Sand mens en tur kører, også før første indholdsblok er ankommet. */
  working?: boolean
  /**
   * Ekstra plads i bunden mens tastaturet er fremme.
   *
   * Komponisten svæver og stiger med tastaturet — uden dette blev tråden
   * stående, og de nyeste linjer forsvandt bag den. Nu følger indholdet med op.
   */
  bottomInset?: number
  /**
   * Runde-etiketter slået op på tool-id — «Rettede fejl i login».
   *
   * Kommer fra streamens `tool_round_label`. Udeladt = ingen overskrifter;
   * tråden ser ud som før.
   */
  rundeEtiketter?: Record<string, string>
  /** Den levende turs `skill_surface` (streamReducerens `skillFlade`). */
  skillFlade?: { matches: SkillFladeMatch[] }
  /** Id på den første besked man ikke har set — tegnes med en skillelinje over. */
  nyeFra?: string | null
  /** Spol tilbage til en af dine beskeder (Claude Desktop §8). */
  onRewind?: (messageId: string) => void
  /** Samtalens visning (Claude Desktop §1): normal, thinking eller verbose. */
  visning?: Visning
  /** Live tænke-resuméer fra streamen (visningen «thinking»). */
  tankeResumeer?: Record<string, string>
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

type Row = (
  | { kind: 'msg'; key: string; message: ChatMessage; hideActions?: boolean
      // Turens blokke følger med den SIDSTE tekstboble, så «Kilder» kan bygges
      // af det han faktisk slog op. Uden dem faldt kilderne væk i samme sekund
      // streamen stoppede.
      kildeBlokke?: PersistedBlock[] | null }
  /** «Tænkte i 14 s ›» — foldet spor af turens overvejelse.
   *  `live`: tænkningen streames lige nu → «Tænker…» med åndedrag.
   *  `messageId`: beskedens id — nøglen til at hente den FULDE strøm, hvis
   *  den avancerede bruger har slået det til i indstillingerne. */
  | { kind: 'thinking'; key: string; seconds?: number; text?: string; live?: boolean; messageId?: string }
  /** Billeder/filer sendt MED en brugerbesked, tegnet over boblen. */
  | { kind: 'attachments'; key: string; items: PersistedBlock[]; side: 'left' | 'right' }
  | { kind: 'tool'; key: string; content: string }
  | { kind: 'live-tool'; key: string; id?: string; name: string; body: string; running: boolean; etiket?: string; diff?: { tilfoejet: number; fjernet: number } | null }
  /** Én RUNDE værktøjsarbejde, foldet sammen til én linje. */
  | { kind: 'tool-group'; key: string; items: ToolItem[] }
  /** Et skill-kald (skill_gate/skill_invoke) — sin EGEN linje, ikke i runden. */
  | { kind: 'skill'; key: string; kald: SkillKald }
  /** Skills runtimen lagde i prompten (`skill_surface`) — uden et kald. */
  | { kind: 'skill-flade'; key: string; matches: SkillFladeMatch[] }
  /**
   * Kompakteringens markør — intern bogholderi, ikke en samtale-besked.
   * Tegnes som én diskret linje. Serveren trimmer dens indhold; uden denne gren
   * faldt rollen i default og blev tegnet som en almindelig boble med hele den
   * serialiserede transcript (målt 111k tegn).
   */
  | { kind: 'compact-marker'; key: string; content: string }
  | { kind: 'turn-header'; key: string; label: string; live: boolean; open: boolean }
  /** «Nye beskeder» — over den første besked man ikke har set (Claude Desktop §10). */
  | { kind: 'nye-beskeder'; key: string }
) & { turnId?: string; work?: boolean }

/**
 * Fold sammenhængende værktøjsrækker sammen til én pr. runde.
 *
 * Codex-appen viser fortælling → ÉN linje → fortælling. Uden det her stablede
 * vi fire «Kører verify_file_contains…» oven på hinanden — samme information
 * fire gange, og tråden mistede sin ro. En tekstbesked afslutter runden.
 */
/** `skill_surface`-matches, kun dem der har navn og tal. */
function skillFladeMatches(v: unknown): SkillFladeMatch[] {
  return Array.isArray(v)
    ? v.flatMap((m) => {
      const mm = m as { name?: unknown; score?: unknown; primary?: unknown }
      return typeof mm?.name === 'string' && typeof mm.score === 'number'
        ? [{ name: mm.name, score: mm.score, primary: !!mm.primary }]
        : []
    })
    : []
}

/**
 * Skillelinjen over den FØRSTE række der hører til den første nye besked.
 * En besked kan blive til flere rækker (afsnit, runder, tanker), og en
 * runde-række bærer nøglen `group-<første kalds nøgle>`. Står den nye besked
 * øverst (intet ældre), er der ingen linje — alt er jo nyt.
 */
export function medNyeLinje<R extends { key: string }>(rows: R[], nyeFra: string | null | undefined): Array<R | { kind: 'nye-beskeder'; key: string }> {
  if (!nyeFra) return rows
  const i = rows.findIndex((r) => {
    const k = r.key.startsWith('group-') ? r.key.slice(6)
      : r.key.startsWith('turn-') ? r.key.slice(5) : r.key
    return k === nyeFra || k.startsWith(`${nyeFra}-`)
  })
  return i > 0 ? [...rows.slice(0, i), { kind: 'nye-beskeder', key: `nye-${nyeFra}` }, ...rows.slice(i)] : rows
}

/**
 * Hvilken af dine beskeder skal stå fast i toppen? (Inverteret liste: højere
 * index = ældre.) Er INGEN af dine beskeder i syne, er det den nærmeste
 * ovenover — den svaret handler om. Er én i syne, står intet fast.
 */
export function stickyIndex(userFlags: boolean[], synlige: [number, number] | null): number | null {
  if (!synlige) return null
  const [lav, hoej] = synlige
  if (userFlags.slice(lav, hoej + 1).some(Boolean)) return null
  const i = userFlags.findIndex((u, j) => u && j > hoej)
  return i >= 0 ? i : null
}

/** Et id serveren kender — ikke en lokal/optimistisk besked. */
function erServerId(id: string): boolean {
  return !/^(local-|u-|opt-|tmp-|outbox-)/.test(id)
}

function groupToolRounds(rows: Row[]): Row[] {
  const out: Row[] = []
  let buf: Row[] = []
  const flush = () => {
    if (buf.length === 0) return
    const items: ToolItem[] = buf.map((r) =>
      r.kind === 'live-tool'
        ? { label: r.etiket || describeTool(r.name, r.body, r.running), running: r.running, tool: r.name, id: r.id, diff: r.diff ?? null, aendring: aendringAf(r.name, r.body) }
        : {
            label: describeToolResult((r as { content: string }).content),
            running: false,
            tool: /\[([a-z_0-9]+)\]\s*:/i.exec((r as { content: string }).content)?.[1] ?? '',
            count: countFromResult((r as { content: string }).content)
          }
    )
    out.push({ kind: 'tool-group', key: `group-${buf[0]!.key}`, items,
      turnId: buf[0]!.turnId, work: buf[0]!.work })
    buf = []
  }
  for (const r of rows) {
    if (r.kind === 'tool' || r.kind === 'live-tool') {
      if (buf.length && r.turnId !== buf[0]!.turnId) flush()
      buf.push(r)
    }
    else {
      flush()
      out.push(r)
    }
  }
  flush()
  return out
}

/** Hold turens arbejde bag én linje, men lad svaret blive i FlatList som sin
 * egen række. Så kan søgning, sticky prompt og rul-til-bunden stadig finde det. */
function medTurHoveder(rows: Row[], aaben: (id: string) => boolean): Row[] {
  const arbejde = new Map<string, Row[]>()
  for (const row of rows) {
    if (row.turnId && row.work) {
      const gruppe = arbejde.get(row.turnId) ?? []
      gruppe.push(row)
      arbejde.set(row.turnId, gruppe)
    }
  }
  const setHoved = new Set<string>()
  const ud: Row[] = []
  for (const row of rows) {
    if (!row.turnId || !row.work) { ud.push(row); continue }
    if (!setHoved.has(row.turnId)) {
      setHoved.add(row.turnId)
      const dele = arbejde.get(row.turnId) ?? []
      const vaerktoejer = dele.flatMap((r) => r.kind === 'tool-group' ? r.items : [])
      const sekunder = dele.reduce((n, r) => n + (r.kind === 'thinking' ? r.seconds ?? 0 : 0), 0)
      const fortalt = summarizeRound(vaerktoejer).replace(/…$/, '') ||
        (sekunder > 0 ? `Tænkte i ${formatTid(sekunder)}` : 'Arbejdede')
      const label = vaerktoejer.length && sekunder > 0 ? `${fortalt} · ${formatTid(sekunder)}` : fortalt
      ud.push({ kind: 'turn-header', key: `turn-${row.turnId}`, turnId: row.turnId,
        label, live: row.turnId === 'stream', open: aaben(row.turnId) })
    }
    if (aaben(row.turnId)) ud.push(row)
  }
  return ud
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
  let thinkingBuf = ''
  // Taenketiden for den raekke der bygges nu. Bufferen kan samle flere
  // tanke-blokke, saa start er den foerste og slut den seneste.
  let tankeStart: number | undefined
  let tankeSlut: number | undefined
  let i = 0
  const flushText = () => {
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
  }
  // `live` sættes IKKE her. En tankerække der bliver skyllet ud, bliver det
  // fordi noget ANDET kom bagefter — tekst eller et værktøj — og så er den
  // tanke afsluttet. Kun den sidste række i turen kan stadig være i gang, og
  // den afgøres til sidst.
  //
  // Før stod `live: true` på dem alle, så hver eneste tankerække pulsede
  // resten af streamen. Bjørn: «intet fanger dem og markerer dem færdig».
  const flushThinking = () => {
    if (thinkingBuf.trim()) {
      rows.push({
        kind: 'thinking',
        key: `stream-thinking-${i}`,
        text: thinkingBuf,
        seconds: taenketid(tankeStart, tankeSlut)
      })
      thinkingBuf = ''
      tankeStart = undefined
      tankeSlut = undefined
    }
  }
  const flush = () => {
    flushThinking()
    flushText()
    i += 1
  }
  // denseBlocks: `blocks` kan være sparsomt (foldede tool_result-content-blokke
  // efterlader `undefined`-huller mellem indices). `for..of` over det rå array
  // ville ramme et hul og crashe på `b.type` → hele React-træet unmounter → sort
  // skærm. `b &&` er defense-in-depth.
  //
  // 12/9-2026: thinking får sin EGEN række, ikke smeltet ind i textBuf.
  // Før blev rå CoT lagt direkte i svarets tekstboble — en ny bruger så
  // intern monolog flyde ind i det svar han skulle læse. Nu står tænkningen
  // som én foldbar linje (Brain-ikon + «Tænker…»), præcis som værktøjerne.
  for (const b of denseBlocks(blocks)) {
    if (!b) continue
    if (b.type === 'text') {
      flushThinking()
      textBuf += b.text
    }
    else if (b.type === 'thinking') {
      flushText()
      thinkingBuf += b.thinking
      if (b.startet != null) tankeStart = Math.min(tankeStart ?? b.startet, b.startet)
      if (b.sidst != null) tankeSlut = Math.max(tankeSlut ?? b.sidst, b.sidst)
    }
    else if (b.type === 'tool_use' && SKILL_VAERKTOEJER.has(b.name)) {
      // Skill-kald står på deres EGEN linje (som desk): i runden ville
      // «hvilken skill, og blev den indlæst» forsvinde i «Brugte et værktøj».
      flush()
      rows.push({
        kind: 'skill', key: `stream-skill-${b.id || i}`,
        kald: { name: b.name, input: b.input, result: b.result, status: b.status ?? 'running' },
      })
    }
    else if (b.type === 'tool_use') {
      flush()
      rows.push({
        kind: 'live-tool',
        key: `stream-tool-${b.id || i}`,
        // Kaldets id baeres med, saa rundens etiket kan slaas op paa DEN.
        id: b.id,
        name: b.name,
        body: toolBody(b),
        running: b.status !== 'done' && b.status !== 'error',
        // Linjetallene for DETTE kald. Serverens MAALTE tal foerst: den har
        // filen i haanden lige foer den skriver, og kan derfor sige hvor meget
        // en overskrivning FJERNEDE — noget klienten umuligt kan vide af
        // argumenterne alene. Gaettet bliver som faldback, fordi et kald der
        // stadig koerer ikke HAR et resultat endnu, og linjen skal kunne
        // tegnes mens svaret kommer ind.
        // `b.partialJson` FOERST: under streaming lander argumenterne dér som
        // en streng, ikke i `b.input` — og det er praecis de runder hvor en fil
        // bliver redigeret, saa «+12 −4» manglede netop hvor det betoed noget.
        // `toolBody` lige nedenfor har hele tiden gjort det samme.
        diff: diffFraResultat(b.result) ?? toolDiff(b.name, b.partialJson || b.input),
        // Serverens egen etiket, brugt ORDRET. En foreløbig række har ingen
        // argumenter endnu — `describeTool` ville sige «Kører bash…» og tabe
        // netop dét der gør ventetiden forståelig. Etiketten findes allerede
        // i `working_step`; den skulle bare ikke smides væk.
        etiket: b.foreloebig?.etiket
      })
    }
  }
  flush()
  // KUN den sidste række kan være i gang. Alt før den er overhalet af noget
  // der kom bagefter; det er selve beviset for at den er færdig.
  const sidste = rows[rows.length - 1]
  if (sidste?.kind === 'thinking') sidste.live = true
  const sidsteArbejde = rows.reduce((index, r, j) => r.kind === 'msg' ? index : j, -1)
  const sidsteTekst = rows.reduce((index, r, j) => r.kind === 'msg' ? j : index, -1)
  rows.forEach((r, j) => {
    r.turnId = 'stream'
    r.work = r.kind !== 'msg' || (sidsteArbejde >= 0 && (j !== sidsteTekst || j < sidsteArbejde))
  })
  return rows
}

/**
 * Sekunder mellem to maalinger — eller undefined hvis der ikke blev maalt.
 *
 * Samme skel som i `blocksToPersisted`: «Taenkte i 0 s» ville vaere en paastand
 * vi ikke har daekning for, og uden tal falder etiketten tilbage til «Taenkte».
 */
function taenketid(start?: number, slut?: number): number | undefined {
  if (start == null || slut == null) return undefined
  const s = (slut - start) / 1000
  return s > 0 ? s : undefined
}

export const MessageList = forwardRef<MessageListHandle, MessageListProps>(function MessageList(
  { messages, blocks, working = false, onResend, onScrollOffset, bottomInset = 0, pins, onTogglePin, onSaveMemory, rundeEtiketter, skillFlade, nyeFra, visning = 'normal', tankeResumeer, onRewind },
  ref
) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  const flatRef = useRef<FlatList>(null)
  const [turnOverrides, setTurnOverrides] = useState<Record<string, boolean>>({})
  const wasWorking = useRef(working)
  useEffect(() => {
    if (working && !wasWorking.current) {
      setTurnOverrides((current) => {
        if (!('stream' in current)) return current
        const next = { ...current }
        delete next.stream
        return next
      })
    }
    wasWorking.current = working
  }, [working])
  const visibleRef = useRef(0)   // ordered-index øverst i viewport (inverted)
  const contentLenRef = useRef(0)
  // Stabil callback — RN kaster hvis onViewableItemsChanged ændrer identitet on-the-fly.
  // Hele det synlige spænd — sticky prompt skal vide om DIN besked er i syne.
  const [synlige, setSynlige] = useState<[number, number] | null>(null)
  const onViewable = useRef(({ viewableItems }: { viewableItems: Array<{ index: number | null }> }) => {
    const first = viewableItems[0]
    if (first && first.index != null) visibleRef.current = first.index
    const idx = viewableItems.map((v) => v.index).filter((i): i is number => i != null)
    setSynlige(idx.length ? [Math.min(...idx), Math.max(...idx)] : null)
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
  // Memoiseret på beskederne (19/9-2026): løkken parsede ALLE beskeders
  // blokke forfra ved hver stream-delta, selv om de gemte beskeder ikke
  // ændrer sig mens et svar streames.
  const persisted = useMemo(() => {
    const persisted: Row[] = []
    let skipToolRows = false
    let legacyTurnId: string | undefined
    for (let i = messages.length - 1; i >= 0; i--) {
      const m = messages[i]!
      if (m.role === 'assistant') {
        legacyTurnId = String(m.id)
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
          // `side: 'left'`: assistenten skriver fra venstre. Uden den landede et
          // billede Jarvis havde lavet i brugerens side og så ud som om brugeren
          // havde sendt det — målt 13/9-2026 på telefonen.
          persisted.unshift({ kind: 'attachments', key: `${m.id}-pub`, items: afiler, side: 'left' })
        }
        if (hasOrdering(blocks)) {
          const expanded: Row[] = []
          const thread = threadBlocks(blocks!)
          const lastTextIdx = thread.reduce(
            (acc, b, i) => (b.type === 'text' && (b.text ?? '').trim() ? i : acc),
            -1
          )
          const lastWorkIdx = thread.reduce((acc, b, i) =>
            b.type === 'tool_use' || b.type === 'skill_surface' ? i : acc, -1)
          thread.forEach((b, bi) => {
            if (b.type === 'text' && (b.text ?? '').trim()) {
              expanded.push({
                kind: 'msg',
                key: `${m.id}-b${bi}`,
                turnId: String(m.id), work: bi !== lastTextIdx || bi < lastWorkIdx,
                message: { ...m, id: `${m.id}-b${bi}`, content: (b.text ?? '').trim() },
                // Kun turens sidste afsnit bærer kopiér/oplæs — ellers gentages
                // rækken efter hvert afsnit og tråden bliver støjende. Samme
                // sted hører kilderne hjemme: én gang pr. tur, i bunden.
                hideActions: bi !== lastTextIdx,
                kildeBlokke: bi === lastTextIdx ? blocks : null
              })
            } else if (b.type === 'tool_use' && SKILL_VAERKTOEJER.has(String(b.name ?? ''))) {
              // Resultatet ligger i den tilhørende `tool_result`-blok, ikke i kaldet.
              const res = thread.find((r) => r.type === 'tool_result' && r.tool_use_id === b.id)
              expanded.push({
                kind: 'skill', key: `${m.id}-sk${bi}`,
                turnId: String(m.id), work: true,
                kald: {
                  name: String(b.name), input: b.input,
                  result: typeof res?.content === 'string' ? res.content : undefined,
                  status: res?.status === 'error' ? 'error' : 'done',
                },
              })
            } else if (b.type === 'skill_surface' && Array.isArray((b as { matches?: unknown }).matches)) {
              const matches = skillFladeMatches((b as { matches?: unknown }).matches)
              if (matches.length) expanded.push({ kind: 'skill-flade', key: `${m.id}-sf${bi}`, matches,
                turnId: String(m.id), work: true })
            } else if (b.type === 'tool_use') {
              expanded.push({
                kind: 'live-tool',
                key: `${m.id}-t${bi}`,
                turnId: String(m.id), work: true,
                // `id` og `diff` skal MED, ellers doer baade linjetallene og
                // runde-etiketten i det oejeblik turen er faerdig: uden id'et
                // kan etiketten ikke slaas op, og uden diff'en er der intet at
                // summere. Blokkene HAR begge dele — `types.ts` siger det selv:
                // «Har beskeden blokke, er de sandheden.»
                id: b.id,
                name: String(b.name ?? ''),
                body: JSON.stringify(b.input ?? {}),
                diff: diffFraResultat(b.result) ?? toolDiff(String(b.name ?? ''), b.input),
                running: false
              })
            } else if (b.type === 'thinking' && (b.text ?? '').trim()) {
              // PAA SIN PLADS, ikke hejst op over turen. En tanke hoerer til dér
              // hvor den blev taenkt — mellem de to vaerktoejer den forbinder.
              expanded.push({
                kind: 'thinking', key: `${m.id}-tk${bi}`,
                turnId: String(m.id), work: true,
                seconds: b.seconds, text: b.text, messageId: m.id
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
          persisted.unshift({ kind: 'msg', key: m.id, message: m, kildeBlokke: blocks,
            turnId: String(m.id) })
          // ALLE turens tanker, i raekkefoelge. `unshift` saetter forrest, saa
          // listen vendes for at bevare den.
          const tanker = (blocks ?? []).filter(
            (b) => b.type === 'thinking' && (b.text ?? '').trim())
          for (let ti = tanker.length - 1; ti >= 0; ti--) {
            persisted.unshift({
              kind: 'thinking', key: `${m.id}-tk${ti}`,
              turnId: String(m.id), work: true,
              seconds: tanker[ti]!.seconds, text: tanker[ti]!.text,
              messageId: m.id
            })
          }
          continue
        }
      }
      if (m.role === 'user') {
        skipToolRows = false
        legacyTurnId = undefined
        const ublocks = attachmentBlocks(parseBlocks(m))
        if (ublocks.length) {
          persisted.unshift({ kind: 'msg', key: m.id, message: m, kildeBlokke: blocks })
          // Billederne ligger OVER boblen, som i referencen — ikke inde i den.
          persisted.unshift({ kind: 'attachments', key: `${m.id}-att`, items: ublocks, side: 'right' })
          continue
        }
      }
      if (m.role === 'tool') {
        if (skipToolRows) continue
        persisted.unshift({ kind: 'tool', key: m.id, content: m.content,
          turnId: legacyTurnId, work: !!legacyTurnId })
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
      persisted.unshift({ kind: 'msg', key: m.id, message: m,
        turnId: m.role === 'assistant' ? String(m.id) : undefined })
    }
    return persisted
  }, [messages])

  // Stabile funktioner pr. række: MessageBubble er memo, og en ny inline-
  // funktion ved hver render ville få ALLE synlige bobler til at rendere om
  // ved hver stream-delta (samme fund som desk, 19/9-2026).
  const genSend = useSenesteFn((...a: Parameters<NonNullable<typeof onResend>>) => onResend?.(...a))
  const rewindFor = useRaekkeFn((id) => onRewind?.(id))
  const pinFor = useRaekkeFn((id) => onTogglePin?.(id))
  // Rækkens EGEN besked — et afsnit af en tur har id'et `<id>-b<n>` og findes
  // ikke i `messages`. Kortet opdateres ved hver render (se nedenfor).
  const beskedForRaekke = useRef(new Map<string, ChatMessage>())
  const gemFor = useRaekkeFn((id) => {
    const m = beskedForRaekke.current.get(id)
    if (m) onSaveMemory?.(m)
  })

  // Den levende turs skill-flade står øverst i turen, før strømmen — som desk.
  const levende = buildStreamingRows(blocks)
  const flade = skillFlade?.matches?.length && levende.length
    ? [{ kind: 'skill-flade' as const, key: 'stream-skill-flade', matches: skillFlade.matches,
        turnId: 'stream', work: true }]
    : []
  const grupperet: Row[] = groupToolRounds([...persisted, ...flade, ...levende])
  const medHoveder = medTurHoveder(grupperet, (id) => turnOverrides[id] ?? visning === 'verbose')
  // En tur starter før første SSE-indholdsblok. Behold samme header-nøgle,
  // så rækken ikke hopper når den første tanke eller det første værktøj lander.
  if (working && !medHoveder.some((r) => r.kind === 'turn-header' && r.turnId === 'stream')) {
    const firstLive = medHoveder.findIndex((r) => r.turnId === 'stream')
    medHoveder.splice(firstLive < 0 ? medHoveder.length : firstLive, 0, {
      kind: 'turn-header', key: 'turn-stream', turnId: 'stream',
      label: 'Working…', live: true, open: turnOverrides.stream ?? visning === 'verbose',
    })
  }
  // Skillelinjen over den FØRSTE række der hører til den første nye besked.
  // En besked kan blive til flere rækker (afsnit, runder, tanker), og en
  // runde-række bærer nøglen `group-<første kalds nøgle>`.
  const rows: Row[] = medNyeLinje(medHoveder, nyeFra)

  // Inverteret liste: nyeste række sidder altid i bunden og er synlig fra start.
  const ordered = [...rows].reverse()
  beskedForRaekke.current = new Map(
    ordered.flatMap((r) => (r.kind === 'msg' ? [[String(r.message.id), r.message] as const] : []))
  )
  // Rundernes sætninger: de GEMTE (tool_use_summary i beskederne) plus de LIVE
  // (streamens tool_round_label). Live vinder, hvis de er uenige — den er den
  // nyeste. Før fandtes kun den live, og sætningen forsvandt når turen var gemt.
  const etiketter = useMemo(
    () => ({ ...gemteEtiketter(messages), ...(rundeEtiketter ?? {}) }),
    [messages, rundeEtiketter],
  )
  const resumeer = useMemo(
    () => (visning === 'thinking' ? { ...gemteResumeer(messages), ...(tankeResumeer ?? {}) } : {}),
    [messages, tankeResumeer, visning],
  )
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
      const i = ordered.findIndex((r) =>
        (r.kind === 'msg' && String(r.turnId ?? r.message.id) === String(messageId)) ||
        (r.kind === 'turn-header' && r.turnId === String(messageId)))
      if (i < 0) return
      // viewPosition 0.3: træffet lander lidt under toppen, så man kan se
      // linjerne FØR det — en besked uden sin optakt er svær at genkende.
      flatRef.current?.scrollToIndex({ index: i, animated: true, viewPosition: 0.3 })
    },
  }), [userFlags, ordered])

  // Sticky prompt (Claude Desktop §10): er INGEN af dine beskeder i syne, står
  // den nærmeste ovenover fast i toppen — det er den svaret handler om. Et tryk
  // ruller tilbage til den. (Inverteret liste: højere index = ældre.)
  let sticky: { i: number; tekst: string } | null = null
  const si = stickyIndex(userFlags, synlige)
  const sr = si != null ? ordered[si] : undefined
  if (si != null && sr && sr.kind === 'msg') sticky = { i: si, tekst: String(sr.message.content ?? '').replace(/\s+/g, ' ').trim() }

  // Ikonet i topbjælken (lib/stickyPrompt) — ikke længere en strimmel her.
  const stickyI = sticky && sticky.tekst ? sticky.i : null
  const stickyTekst = sticky?.tekst ?? ''
  useEffect(() => {
    saetStickyPrompt(stickyI != null ? {
      tekst: stickyTekst,
      hop: () => flatRef.current?.scrollToIndex({ index: stickyI, animated: true, viewPosition: 0 }),
    } : null)
  }, [stickyI, stickyTekst])
  useEffect(() => () => saetStickyPrompt(null), [])

  return (
    <View style={styles.listeWrap}>
    <FlatList
      ref={flatRef}
      inverted
      // Ingen linje over komponisten (Bjørn 21/9-2026: «tænke fragmenter bør
      // vises I tænke linjen i chatview og linjen over composer væk»). Den bar
      // tænke-fragmenterne og forsvandt når streamen sluttede. Fragmenterne
      // staar nu PAA traadens egen taenke-linje (ThinkingSummary), praecis hvor
      // desk har dem — og der er derfor intet der flyder ovenover traaden.
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
        if (item.kind === 'turn-header') {
          return <TurnHeader
            label={item.label} live={item.live} open={item.open}
            onToggle={() => setTurnOverrides((current) => ({ ...current,
              [item.turnId!]: !item.open }))}
          />
        }
        // Værktøjsarbejde er ÉN linje inde i samtalen — ikke et kort.
        // Målt i Codex-tråden: «</> Ændrede 16 filer ›». Det fulde output
        // ligger bag linjen, ikke foran den.
        if (item.kind === 'tool-group') {
          // Etiketten daekker HELE runden, saa det foerste kald der har en, er
          // rundens. Opslaget gaar paa kaldets id og ikke paa raekkefoelgen:
          // en sen etiket ville ellers saette sig over de forkerte kald.
          const etik = item.items
            .map((i: ToolItem) => (i.id ? etiketter[i.id] : undefined))
            .find(Boolean)
          // «Tænkning»: resuméet af tænkningen står OVER gruppen (Claude Desktop §2).
          const resume = visning === 'thinking'
            ? item.items.map((i: ToolItem) => (i.id ? resumeer[i.id] : undefined)).find(Boolean)
            : undefined
          const gruppe = <InlineToolGroup items={item.items} etiket={etik} aabenFraStart={visning === 'verbose'} />
          return resume ? <View><TankeResumeLinje tekst={resume} />{gruppe}</View> : gruppe
        }
        if (item.kind === 'thinking') {
          return (
            <ThinkingSummary
              seconds={item.seconds}
              text={item.text}
              live={item.live}
              messageId={item.messageId}
              aabenFraStart={visning === 'verbose'}
            />
          )
        }
        if (item.kind === 'nye-beskeder') return <NyeBeskederRow />
        if (item.kind === 'skill') return <SkillLinje kald={item.kald} />
        if (item.kind === 'skill-flade') return <SkillFladeLinje matches={item.matches} />
        if (item.kind === 'attachments') {
          return <MessageAttachments items={item.items} side={item.side} />
        }
        if (item.kind === 'compact-marker') return <CompactMarkerRow content={item.content} />
        return (
          <MessageBubble
            message={item.message}
            kildeBlokke={item.kildeBlokke}
            onResend={item.message.role === 'user' && onResend ? genSend : undefined}
            // Kun en besked serveren kender (ikke en lokal/optimistisk), og kun
            // hele beskeder — et afsnit af en tur har id'et `<id>-b<n>`.
            onRewind={item.message.role === 'user' && onRewind && erServerId(String(item.message.id))
              ? rewindFor(String(item.message.id)) : undefined}
            pinned={pins?.includes(String(item.message.id))}
            onTogglePin={onTogglePin ? pinFor(String(item.message.id)) : undefined}
            onSaveMemory={
              // Kun hans egne svar. En hukommelse af Bjørns egen besked er
              // bare et ekko — det er svaret der er værd at gemme.
              onSaveMemory && item.message.role === 'assistant'
                ? gemFor(String(item.message.id))
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
    </View>
  )
})

/** «Nye beskeder» — tynd accentlinje med ordet i midten, som desk. */
function NyeBeskederRow() {
  const styles = useStyles(makestyles)
  return (
    <View style={styles.nyeRow} accessibilityRole="text" accessibilityLabel="Nye beskeder" testID="nye-beskeder">
      <View style={styles.nyeStreg} />
      <Text style={styles.nyeTekst}>Nye beskeder</Text>
      <View style={styles.nyeStreg} />
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
  listeWrap: { flex: 1 },
  // Under den svævende header (TOP_CLEARANCE), højrestillet som dine bobler.
  nyeRow: { flexDirection: 'row', alignItems: 'center', gap: 10, marginHorizontal: tokens.spacing.lg, marginVertical: 10 },
  nyeStreg: { flex: 1, height: StyleSheet.hairlineWidth, backgroundColor: tokens.color.accent, opacity: 0.6 },
  nyeTekst: { color: tokens.color.accent, fontSize: 12, fontWeight: '600', letterSpacing: 0.3 },
  content: {
    // paddingTop sættes dynamisk (BOTTOM_CLEARANCE + tastaturhøjde) — se
    // contentContainerStyle. Kun den øverste er konstant.
    paddingBottom: TOP_CLEARANCE
  }
})
