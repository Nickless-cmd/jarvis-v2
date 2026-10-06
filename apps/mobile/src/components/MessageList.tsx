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
import { InlineToolGroup, type TankeRaekke } from './InlineToolGroup'
import { formatTid } from '../lib/arbejdslinje'
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
import { Arbejdslinje } from './Arbejdslinje'
import { ImageGenerationCard } from './ImageGenerationCard'
import { VideoGenerationCard } from './VideoGenerationCard'
import { ImageAnalysisCard } from './ImageAnalysisCard'
import { billedArbejdeFor } from '../lib/billedArbejde'

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
   * Headerens samlede højde — `insets.top + headerHeight` fra App.tsx.
   *
   * Lægges til `TOP_CLEARANCE`, så trådens øverste kant ligger UNDER den
   * svævende header i stedet for 2 dp inde i den. Bjørn 28/9-2026: den
   * øverste boble blev klippet fladt foroven, men kun når streamen stod
   * stille — i hvile lander tråden på sin faste plads.
   */
  topInset?: number
  /**
   * Runde-etiketter slået op på tool-id — «Rettede fejl i login».
   *
   * Kommer fra streamens `tool_round_label`. Udeladt = ingen overskrifter;
   * tråden ser ud som før.
   */
  rundeEtiketter?: Record<string, string>
  /**
   * Arbejdslinjens sætning i Jarvis' stemme — eller null.
   *
   * Bygget af `arbejdslinjeTekst(state.workingStep, state.workingAction)`.
   * Udeladt eller null = ingen linje; tråden ser ud som før.
   */
  arbejdslinje?: string | null
  /**
   * Token-tallet til arbejdslinjen — `usage.input + cacheHit + cacheMiss +
   * output`, altså HELE konteksten turen bærer og ikke kun svaret.
   *
   * Samme fire led som desk summerer (`ChatView.tsx:138`), så de to klienter
   * viser samme tal for samme tur. Udeladt eller 0 = tallet vises ikke.
   */
  arbejdslinjeTokens?: number
  /**
   * Har serveren bekræftet at arbejdsfasen er slut (`final_answer_start`)?
   *
   * Bærer runde-linjens shimmer gennem hullet mellem to runder: uden den
   * slukker den i samme sekund sidste værktøjskald er færdigt, mens Jarvis
   * stadig tænker på den næste. Udeladt = nej (shimmeren slukker som før).
   */
  finalAnswerStarted?: boolean
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
      kildeBlokke?: PersistedBlock[] | null
      /**
       * Jarvis' egne filer og billeder — de hører til BESKEDEN (GPT-formen,
       * 27/9-2026).
       *
       * De bæres her frem for i deres egen række, fordi en selvstændig række
       * lander EFTER boblens handlingsrække: billedet endte under kopiér/
       * oplæs-ikonerne og så ud som om det kom efter svaret i stedet for at
       * være en del af det. Bjørn så det på telefonen.
       */
      vedhaeftninger?: PersistedBlock[] }
  /** «Tænkte i 14 s ›» — foldet spor af turens overvejelse.
   *  `live`: tænkningen streames lige nu → «Tænker…» med åndedrag.
   *  `messageId`: beskedens id — nøglen til at hente den FULDE strøm, hvis
   *  den avancerede bruger har slået det til i indstillingerne. */
  | { kind: 'thinking'; key: string; seconds?: number; text?: string; live?: boolean; messageId?: string }
  /** Billeder/filer sendt MED en brugerbesked, tegnet over boblen. */
  | { kind: 'attachments'; key: string; items: PersistedBlock[]; side: 'left' | 'right' }
  | { kind: 'tool'; key: string; content: string }
  | { kind: 'live-tool'; key: string; id?: string; name: string; body: string; running: boolean; etiket?: string; diff?: { tilfoejet: number; fjernet: number } | null; result?: string }
  | { kind: 'image-generation'; key: string }
  | { kind: 'video-generation'; key: string }
  | { kind: 'image-analysis'; key: string; kilde: string; sti: string }
  /** Én RUNDE værktøjsarbejde, foldet sammen til én linje. */
  | { kind: 'tool-group'; key: string; items: ToolItem[]; tanker?: TankeRaekke[]; sidsteRunde?: boolean }
  /** Arbejdslinjen — hvad Jarvis laver LIGE NU, nederst i beskeden.
   *  Findes kun mens der streames; rækken tilføjes ikke efter. */
  | { kind: 'arbejdslinje'; key: string; tekst: string; tokens: number }
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
  // Elementerne i runden der bygges nu: kald OG tanker, i den rækkefølge de
  // skete. Desk gør præcis dette (`opdelArbejdsrunder`, `raekkeModel.ts:71`):
  // elementer samles, og KUN et mellemsvar afslutter runden — en tanke gør
  // ikke. En runde uden kald bliver enkeltrækker.
  //
  // Bjørn 30/9-2026: «Tænkte linjen står stadig under tool result linjen».
  // Den gjorde netop det, fordi denne funktion LUKKEDE runden i det øjeblik
  // den så en tanke. Blokkene kommer i rækkefølgen `thinking, text, tool_use`
  // (målt i besked 153522), så tanken blev skubbet ud som sin EGEN række efter
  // den foregående rundes linje i stedet for at ligge inde i den.
  let elementer: Row[] = []
  let tur: string | undefined
  const afslut = () => {
    if (elementer.length === 0) return
    const kald: Row[] = []
    const tankeRækker: Row[] = []
    const tanker: TankeRaekke[] = []
    for (const r of elementer) {
      if (r.kind === 'thinking') {
        tankeRækker.push(r)
        // Hvor mange kald der kom FØR den. Folden tegner elementerne i den
        // rækkefølge de skete — som desk — i stedet for alle tanker øverst.
        tanker.push({ key: r.key, seconds: r.seconds, text: r.text, live: r.live,
          messageId: r.messageId, foerKald: kald.length })
      } else {
        kald.push(r)
      }
    }
    elementer = []
    tur = undefined
    // Ingen linje at folde bag: tankerne står selv, hvor de stod.
    if (kald.length === 0) { out.push(...tankeRækker); return }
    const items: ToolItem[] = kald.map((r) =>
      r.kind === 'live-tool'
        ? { label: r.etiket || describeTool(r.name, r.body, r.running), running: r.running, tool: r.name, id: r.id, diff: r.diff ?? null, aendring: aendringAf(r.name, r.body), result: r.result ?? null, input: r.body }
        : {
            label: describeToolResult((r as { content: string }).content),
            running: false,
            tool: /\[([a-z_0-9]+)\]\s*:/i.exec((r as { content: string }).content)?.[1] ?? '',
            count: countFromResult((r as { content: string }).content),
            // Den persisterede række ER resultatet (`[tool_result:…] [bash]: …`).
            result: (r as { content: string }).content
          }
    )
    out.push({ kind: 'tool-group', key: `group-${kald[0]!.key}`, items,
      tanker: tanker.length ? tanker : undefined,
      turnId: kald[0]!.turnId, work: kald[0]!.work })
  }
  for (const r of rows) {
    if (r.kind === 'tool' || r.kind === 'live-tool' || r.kind === 'thinking') {
      // En ny TUR starter altid en ny runde.
      if (elementer.length && r.turnId !== tur) afslut()
      elementer.push(r)
      tur = r.turnId
    } else {
      afslut()
      out.push(r)
    }
  }
  afslut()
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
      // Tænketiden bor nu INDE i gruppen for de tanker der hørte til en runde;
      // kun de tanker uden et kald efter sig står stadig som egne rækker.
      // Uden begge led ville hovedets «· 1m 3s» tabe netop de sekunder det
      // skal vise — og det ville gøre det uden en fejl at se på.
      const sekunder = dele.reduce((n, r) =>
        n + (r.kind === 'thinking'
          ? r.seconds ?? 0
          : r.kind === 'tool-group'
            ? (r.tanker ?? []).reduce((m, t) => m + (t.seconds ?? 0), 0)
            : 0), 0)
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
    else if (b.type === 'image') {
      // Jarvis' EGET billede midt i streamen. Det bærer `src` direkte (en
      // data-URL fra streamen), så det kan tegnes med det samme.
      //
      // Uden denne gren faldt billedet ud af den LEVENDE visning og dukkede
      // først op ved genindlæsning — altså netop mens man venter på det, og
      // det er dét Bjørn pegede på med ChatGPT-appen som facit (27/9-2026).
      flush()
      // REFERENCEN skal med, ikke kun `src`. Er billedet for stort til en
      // data-URL, sender serveren `attachment_id` alene — attachment'en er
      // allerede registreret, så `blokUrl` finder den. Uden felterne her
      // ville `tegnBillede` få hverken `src` eller adresse og tegne INTET,
      // præcis for de største billeder.
      rows.push({
        kind: 'attachments',
        key: `stream-vedh-${rows.length}`,
        items: [{
          type: 'image',
          src: b.src,
          attachment_id: b.attachment_id,
          url: b.url,
          filename: b.filename ?? b.alt,
          mime_type: b.mime_type,
          kilde: b.kilde,
          tool_use_id: b.tool_use_id,
        }],
        side: 'left',
      })
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
    else if (b.type === 'tool_use' && billedArbejdeFor(b)) {
      // Generering ELLER analyse. Ét opslag (lib/billedArbejde), så et nyt
      // billedværktøj ikke kan blive husket her og glemt i desk.
      const arbejde = billedArbejdeFor(b)!
      flush()
      rows.push(arbejde.slags === 'analyse'
        ? { kind: 'image-analysis', key: `stream-analyse-${b.id || i}`, kilde: arbejde.kilde, sti: arbejde.sti }
        : arbejde.slags === 'video'
          ? { kind: 'video-generation', key: `stream-video-${b.id || i}` }
          : { kind: 'image-generation', key: `stream-image-${b.id || i}` })
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
        // Kaldets svar. `result` sættes på blokken når tool_result-rammen
        // lander (se reducerens foldning), og bæres med her — ellers kunne
        // folden vise HVAD der blev kaldt, men ikke hvad det svarede.
        result: typeof b.result === 'string' ? b.result : undefined,
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
  // En senere blok betyder at Jarvis er gået videre. Et gammelt tool_use kan
  // mangle slutstatus i en sparsom stream; ventefladen må ikke blive stående.
  for (let index = rows.length - 2; index >= 0; index--) {
    const k = rows[index]?.kind
    if (k === 'image-generation' || k === 'image-analysis' || k === 'video-generation') rows.splice(index, 1)
  }
  // KUN den sidste række kan være i gang. Alt før den er overhalet af noget
  // der kom bagefter; det er selve beviset for at den er færdig.
  const sidste = rows[rows.length - 1]
  if (sidste?.kind === 'thinking') sidste.live = true
  // (Flaget `sidsteRunde` sættes IKKE her. Denne funktion bygger `live-tool`-
  // rækker; `tool-group` opstår først i `groupToolRounds`. Lå det her, ramte
  // det en rækketype der ikke findes i arrayet — og shimmeren var død i hele
  // appen. Se det levende sted nedenfor, ved `nyeLive`.)
  const sidsteArbejde = rows.reduce((index, r, j) =>
    r.kind === 'msg' || r.kind === 'attachments' ? index : j, -1)
  const sidsteTekst = rows.reduce((index, r, j) => r.kind === 'msg' ? j : index, -1)
  rows.forEach((r, j) => {
    r.turnId = 'stream'
    // Leverancer skal stå ved svaret, også mens arbejdshovedet er foldet.
    r.work = r.kind !== 'msg' && r.kind !== 'attachments'
      || (r.kind === 'msg' && sidsteArbejde >= 0 && (j !== sidsteTekst || j < sidsteArbejde))
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
  { messages, blocks, working = false, arbejdslinje, arbejdslinjeTokens = 0, finalAnswerStarted = false, onResend, onScrollOffset, bottomInset = 0, topInset = 0, pins, onTogglePin, onSaveMemory, rundeEtiketter, skillFlade, nyeFra, visning = 'normal', tankeResumeer, onRewind },
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
  const aabnetTurRef = useRef<string | null>(null)
  //: Scroll-offsettet i content-rummet. Inverteret liste: 0 = bunden.
  //: Bruges til at holde skaermen bomstille naar et tur-hoved foldes.
  const scrollTopRef = useRef(0)
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
        // UDGIVNE FILER. De bæres nu PÅ beskedens sidste afsnit frem for i
        // deres egen række (GPT-formen, 27/9-2026). I en egen række faldt de
        // neden for boblens kopiér/oplæs-ikoner og så ud som om de kom efter
        // svaret — se `MessageBubble.vedhaeftninger`.
        //
        // Den oprindelige kommentar her forklarede hvorfor de blev lagt FØR
        // grenene: både ordre-grenen og tænke-grenen `continue`r, så en
        // håndtering placeret efter dem blev aldrig nået. Det gælder stadig —
        // filerne lægges derfor af her og bæres med ind i hver gren.
        const afiler = attachmentBlocks(blocks)
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
                kildeBlokke: bi === lastTextIdx ? blocks : null,
                // Filen hører til turens SIDSTE afsnit — samme sted som
                // kilderne og som handlingsrækken sidder.
                vedhaeftninger: bi === lastTextIdx && afiler.length ? afiler : undefined
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
                // Samme som live-rækken: svaret skal med, ellers er folden
                // tom for indhold når tråden genindlæses fra disken.
                result: typeof b.result === 'string' ? b.result : undefined,
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
          // En tur UDEN tekstblokke (fx ren værktøjskørsel der ender med et
          // billede) har ingen besked at hænge filen på. Så står den alene —
          // det er bedre end at tabe den.
          if (afiler.length && !expanded.some((r) => r.kind === 'msg')) {
            expanded.push({ kind: 'attachments', key: `${m.id}-pub`, items: afiler, side: 'left' })
          }
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
            turnId: String(m.id), vedhaeftninger: afiler.length ? afiler : undefined })
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
        // Hverken rækkefølge eller tænkning: et rent svar — med eller uden
        // fil. Filerne bæres på rækken, så de ikke skal have deres egen.
        persisted.unshift({ kind: 'msg', key: m.id, message: m,
          turnId: String(m.id), vedhaeftninger: afiler.length ? afiler : undefined })
        continue
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
      // Assistent-ture har deres egen gren ovenfor og `continue`r altid, så
      // `turnId` sættes ikke her: de roller der når hertil (bruger, system,
      // godkendelse) har aldrig haft et turn-id.
      persisted.unshift({ kind: 'msg', key: m.id, message: m })
    }
    return persisted
  }, [messages])

  // Stabile funktioner pr. række: MessageBubble er memo, og en ny inline-
  // funktion ved hver render ville få ALLE synlige bobler til at rendere om
  // ved hver stream-delta (samme fund som desk, 19/9-2026).
  const genSend = useSenesteFn((...a: Parameters<NonNullable<typeof onResend>>) => onResend?.(...a))
  const toggleFor = useRaekkeFn((id) => {
    const aaben = turnOverrides[id] ?? (id === 'stream' ? working : visning === 'verbose')
    // Skaermen maa IKKE rykke sig naar et tur-hoved foldes (Bjoern 6/10-2026).
    //
    // Listen er inverteret, saa indsatte arbejdsraekker ligger paa HOEJERE
    // content-y end headeren. Uden kompensation skubber de headeren OP i
    // viewporten. Vi noterer turen her og lader `onContentSizeChange` skyde
    // offsettet praecis lige saa meget som indholdet voksede — saa staar
    // headeren stille og arbejdet folder NED under den.
    //
    // Samme vej begge retninger: ved fold-ind bliver delta negativ, og
    // kompensationen loefter skaermen tilsvarende op. Derfor saettes ref'en
    // ogsaa naar turen LUKKES — den gamle udgave ryddede den og lod
    // fold-ind skubbe headeren den anden vej.
    aabnetTurRef.current = id
    setTurnOverrides((current) => ({ ...current, [id]: !aaben }))
  })
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
  // Historikken ændrer sig ikke ved et nyt tekst-delta. Dens grupper og
  // turn-headere var ellers bygget om for hver lille bid af livestrømmen.
  const gemteGrupper = useMemo(() => groupToolRounds(persisted), [persisted])
  const gemteHoveder = useMemo(() => medTurHoveder(gemteGrupper,
    (id) => turnOverrides[id] ?? visning === 'verbose'), [gemteGrupper, turnOverrides, visning])
  // Tekst-delta skelner ikke syntese fra slutsvar. Fold først ved bekræftet stop.
  const erAaben = (id: string) => turnOverrides[id] ?? (id === 'stream' ? working : visning === 'verbose')
  const nyeLive = medTurHoveder(groupToolRounds([...flade, ...levende]), erAaben)
  // Kun turens SIDSTE arbejdsrunde kan stadig være i gang — og kun den bærer
  // shimmeren videre gennem hullet til næste runde (se `InlineToolGroup`).
  //
  // Flaget sættes HER, ikke i `buildStreamingRows`: den funktion bygger
  // `live-tool`-rækker, og `tool-group` opstår først i `groupToolRounds`
  // ovenfor. Sat der ramte det en rækketype der ikke findes i arrayet, så
  // `sidste` var altid `undefined` og shimmeren kørte ALDRIG (målt 4/10-2026).
  {
    const sidsteRunde = nyeLive.reduce((idx, r, j) => (r.kind === 'tool-group' ? j : idx), -1)
    if (sidsteRunde >= 0) {
      const r = nyeLive[sidsteRunde]
      if (r?.kind === 'tool-group') r.sidsteRunde = true
    }
  }
  // En ny delta ændrer som regel kun den sidste række. Genbrug de øvrige
  // referencer, så memoiserede rækker beholder deres tekst, ikoner og state.
  const gamleLive = useRef(new Map<string, Row>())
  const naesteLive = new Map<string, Row>()
  const liveHoveder = nyeLive.map((row) => {
    const gammel = gamleLive.current.get(row.key)
    let stabil = row
    if (gammel?.kind === row.kind && gammel.work === row.work) {
      if (row.kind === 'msg' && gammel.kind === 'msg'
        && gammel.message.content === row.message.content
        && gammel.hideActions === row.hideActions
        && gammel.kildeBlokke === row.kildeBlokke) stabil = gammel
      if (row.kind === 'tool-group' && gammel.kind === 'tool-group'
        && gammel.sidsteRunde === row.sidsteRunde
        && JSON.stringify(gammel.items) === JSON.stringify(row.items)) stabil = gammel
      if (row.kind === 'thinking' && gammel.kind === 'thinking'
        && gammel.text === row.text && gammel.seconds === row.seconds
        && gammel.live === row.live) stabil = gammel
      if (row.kind === 'turn-header' && gammel.kind === 'turn-header'
        && gammel.label === row.label && gammel.open === row.open
        && gammel.live === row.live) stabil = gammel
    }
    naesteLive.set(row.key, stabil)
    return stabil
  })
  gamleLive.current = naesteLive
  const medHoveder = [...gemteHoveder, ...liveHoveder]

  // En tur starter før første SSE-indholdsblok. Behold samme header-nøgle,
  // så rækken ikke hopper når den første tanke eller det første værktøj lander.
  if (working && !medHoveder.some((r) => r.kind === 'turn-header' && r.turnId === 'stream')) {
    const firstLive = medHoveder.findIndex((r) => r.turnId === 'stream')
    medHoveder.splice(firstLive < 0 ? medHoveder.length : firstLive, 0, {
      kind: 'turn-header', key: 'turn-stream', turnId: 'stream',
      label: 'Working…', live: working, open: erAaben('stream'),
    })
  }
  // Skillelinjen over den FØRSTE række der hører til den første nye besked.
  // En besked kan blive til flere rækker (afsnit, runder, tanker), og en
  // runde-række bærer nøglen `group-<første kalds nøgle>`.
  const rows: Row[] = medNyeLinje(medHoveder, nyeFra)
  // Arbejdslinjen lægges SIDST — den inverterede liste tegner index 0 i
  // bunden, så den havner under alt andet i beskeden og forsvinder med
  // streamen. Bjørn 29/9-2026: «fra streaming starter til den slutter og
  // så forsvinder igen i bunden af din besked».
  if (working && arbejdslinje) {
    rows.push({ kind: 'arbejdslinje', key: 'arbejdslinje', tekst: arbejdslinje, tokens: arbejdslinjeTokens })
  }

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
      testID="traad"
      inverted
      // Ingen linje over komponisten (Bjørn 21/9-2026: «tænke fragmenter bør
      // vises I tænke linjen i chatview og linjen over composer væk»). Den bar
      // tænke-fragmenterne og forsvandt når streamen sluttede. Fragmenterne
      // staar nu PAA traadens egen taenke-linje (ThinkingSummary), praecis hvor
      // desk har dem — og der er derfor intet der flyder ovenover traaden.
      data={ordered}
      keyExtractor={(item) => item.key}
      onContentSizeChange={(_w, h) => {
        const foer = contentLenRef.current
        contentLenRef.current = h
        if (!aabnetTurRef.current) return
        aabnetTurRef.current = null
        // Foerste maaling nogensinde (foer = 0) har intet at kompensere imod.
        if (!foer) return
        const delta = h - foer
        if (!delta) return
        // `animated: false` — med animation glider skaermen, og kravet er at
        // den staar bomstille mens indholdet folder ud under hovedet.
        flatRef.current?.scrollToOffset({ offset: scrollTopRef.current + delta, animated: false })
      }}
      onScroll={(e) => {
        scrollTopRef.current = e.nativeEvent.contentOffset.y
        onScrollOffset?.(e.nativeEvent.contentOffset.y)
      }}
      scrollEventThrottle={120}
      onViewableItemsChanged={onViewable}
      onScrollToIndexFailed={(info) => {
        flatRef.current?.scrollToOffset({ offset: info.averageItemLength * info.index, animated: true })
      }}
      renderItem={({ item }) => {
        if (item.kind === 'turn-header') {
          return <TurnHeader
            label={item.label} live={item.live} open={item.open}
            onToggle={toggleFor(item.turnId!)}
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
          const gruppe = <InlineToolGroup
            items={item.items} etiket={etik} aabenFraStart={visning === 'verbose'} tanker={item.tanker}
            streaming={working} sidste={item.sidsteRunde} svarBegyndt={finalAnswerStarted}
          />
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
        if (item.kind === 'arbejdslinje') return <Arbejdslinje tekst={item.tekst} tokens={item.tokens} />
        if (item.kind === 'attachments') {
          return <MessageAttachments items={item.items} side={item.side} />
        }
        if (item.kind === 'image-generation') return <ImageGenerationCard />
        if (item.kind === 'video-generation') return <VideoGenerationCard />
        if (item.kind === 'image-analysis') return <ImageAnalysisCard kilde={item.kilde} sti={item.sti} />
        if (item.kind === 'compact-marker') return <CompactMarkerRow content={item.content} />
        return (
          <MessageBubble
            message={item.message}
            kildeBlokke={item.kildeBlokke}
            vedhaeftninger={item.vedhaeftninger}
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
      contentContainerStyle={[styles.content, { paddingTop: BOTTOM_CLEARANCE + bottomInset, paddingBottom: TOP_CLEARANCE + topInset }]}
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
/** Luft under den svævende header UD OVER headerens egen højde. Selve
 *  headerhøjden lægges til dynamisk via `topInset` — se `content`. */
const TOP_CLEARANCE = 12

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
    // BEGGE sættes dynamisk i contentContainerStyle — se den.
    //
    // Den øverste var FAST (TOP_CLEARANCE = 72) indtil 28/9-2026, og det var
    // en fejl: 72 dp er målt fra skærmens top, men header'en fylder
    // `insets.top + BADGE_H + polstring` — ca. 74 dp på Bjørns enhed. Tråden
    // begyndte derfor 2 dp inde UNDER header'ens underkant, og den øverste
    // boble blev klippet fladt foroven. Bjørn 28/9-2026: «Der sker et eller
    // andet ved header … men kun når streamen står stille» — i hvile lander
    // tråden på sin faste plads; mens der streames skubbes den op.
    //
    // Tallet kommer nu fra App.tsx, som allerede måler headerHeight til
    // WorkScreen. Ét tal, ét sted.
  }
})
