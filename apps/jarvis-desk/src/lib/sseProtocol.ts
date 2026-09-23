/**
 * Anthropic-style v2 SSE event-typer for /chat/stream/v2.
 *
 * Udtrukket fra streamClient.ts så både stream-konsumenten OG rich-rendering
 * kan dele typerne uden cirkulær import. streamClient re-eksporterer dem for
 * bagudkompatibilitet.
 */

// ─── Wire-form events (1:1 fra serverens v2-protokol) ────────────────────

export interface MessageStartEvent {
  type: 'message_start'
  message: {
    id: string
    model: string
    provider: string
    lane: string
    session_id: string | null
    usage: { input_tokens: number; output_tokens: number }
  }
}

export interface ContentBlockStartEvent {
  type: 'content_block_start'
  index: number
  content_block:
    | { type: 'text'; text: string }
    | { type: 'thinking'; thinking: string }
    | { type: 'tool_use'; id: string; name: string; input: Record<string, unknown> }
    | { type: 'tool_result'; tool_use_id: string; status: string; content: string; is_error?: boolean }
}

export interface ContentBlockDeltaEvent {
  type: 'content_block_delta'
  index: number
  delta:
    | { type: 'text_delta'; text: string }
    | { type: 'thinking_delta'; thinking: string }
    | { type: 'input_json_delta'; partial_json: string }
}

export interface ContentBlockStopEvent {
  type: 'content_block_stop'
  index: number
}

export interface MessageDeltaEvent {
  type: 'message_delta'
  delta: { stop_reason: string }
  usage: {
    input_tokens: number
    output_tokens: number
    cache_hit_tokens: number
    cache_miss_tokens: number
  }
}

export interface MessageStopEvent {
  type: 'message_stop'
}

export interface PingEvent {
  type: 'ping'
}

export interface SystemEvent {
  type: 'system_event'
  kind: string
  payload: Record<string, unknown>
}

/**
 * Én kort etiket for en afsluttet værktøjs-runde — «Rettede fejl i login».
 *
 * Skrevet af en lille LOKAL model på serveren og leveret ved NÆSTE rundes
 * start: etiketten regnes i en tråd, og en generator kan kun yield'e fra sit
 * eget flow. `tool_use_ids` binder den til DE kald den opsummerer — ikke til en
 * plads i strømmen.
 */
export interface ToolRoundLabelEvent {
  type: 'tool_round_label'
  run_id: string
  round: number
  etiket: string
  tool_use_ids: string[]
  /** Tænke-resuméet — kun når samtalen står i visningen «thinking». */
  tanke_resume?: string
}

/**
 * Skills runtimen lagde i prompten, FØR modellen skrev et ord
 * (skill_relevance_surface.skill_flade_event). Den hyppigste skill-gate —
 * efterlod før intet spor. Kommer direkte (v1) eller som
 * `system_event(kind='skill_surface')` (v2).
 */
export interface SkillSurfaceEvent {
  type: 'skill_surface'
  run_id?: string
  matches: SkillMatchInfo[]
  primary: boolean
}

export interface SkillMatchInfo { name: string; score: number; primary: boolean }

export type StreamEvent =
  | ToolRoundLabelEvent
  | SkillSurfaceEvent
  | MessageStartEvent
  | ContentBlockStartEvent
  | ContentBlockDeltaEvent
  | ContentBlockStopEvent
  | MessageDeltaEvent
  | MessageStopEvent
  | PingEvent
  | SystemEvent

// ─── Rendret form (ikke wire-form). Bruges af reducer + rich-rendering. ───

export type ContentBlock =
  | { type: 'text'; text: string }
  /**
   * `seconds`: målt varighed. Gemte beskeder har serverens tal; live sætter
   * reduceren den, når næste blok starter. `startet`: klientens ur da blokken
   * startede — på BLOKKEN og ikke i komponenten, fordi komponenten monteres om
   * når runderne grupperes eller svaret bliver færdigt, og så startede uret
   * forfra og «Tænkte i xx s» forsvandt (Bjørn 17/9-2026).
   */
  | { type: 'thinking'; thinking: string; seconds?: number; startet?: number }
  | { type: 'skill_surface'; matches: SkillMatchInfo[]; primary: boolean }
  | {
      // Rundens sætning, gemt i beskeden — Claude Desktops egen form
      // (19/9-2026). Hæfter sig på sine kald via ids, ikke på en plads.
      type: 'tool_use_summary'
      summary: string
      preceding_tool_use_ids: string[]
      /** Tænke-resuméet for gruppen (visningen «thinking», 19/9-2026). */
      thinking_summary?: string
    }
  | {
      type: 'tool_use'
      id: string
      name: string
      input: Record<string, unknown>
      partialJson?: string
      status?: 'running' | 'done' | 'error'
      result?: string
      /** Serveren sendte kun begyndelsen af et langt resultat; resten hentes
       *  med GET /chat/messages/{id}/tool-result/{tool_use_id}. */
      resultAfkortet?: boolean
      /** Hele resultatets længde i tegn — så linjen kan sige det ærligt. */
      resultTegnIAlt?: number
      /** Klientens ur da kaldet startede — til live-tiden på runde-linjen. */
      startet?: number
      /**
       * Noget ved kaldet stemmer ikke, og det skal SES (18/9-2026):
       *  - `uden-kald`: et resultat hvis kald ikke findes i beskeden. Det
       *    blev før droppet stille.
       *  - `uden-resultat`: en færdig besked hvor kaldet aldrig fik et
       *    resultat. Det blev før vist som lykkedes.
       * Et manglende resultat er et UKENDT udfald — hverken fejl eller succes.
       */
      anomali?: 'uden-kald' | 'uden-resultat'
    }
  | {
      // Billede. LIVE bærer det en `src` (data-URL fra streamen). PERSISTERET
      // bærer det en REFERENCE — `attachment_id` eller `url` — og hentes med
      // token ved visning. Uden reference-felterne her faldt et gemt billede
      // ud af `foldToolResults` og forsvandt fra tråden efter reload, selv om
      // det lå i beskeden hele tiden.
      type: 'image'
      src?: string
      alt?: string
      attachment_id?: string
      url?: string
      filename?: string
      mime_type?: string
    }
  | {
      // UDGIVET fil (`publish_file`) eller en vedhæftning. Bærer ALTID kun en
      // reference, aldrig data: `url` for Jarvis' egen udgivelse over
      // `/files/{navn}`, `attachment_id` for uploads over `/attachments/...`.
      //
      // Målt 15/9-2026: blokken blev gemt i beskeden med `url` og
      // `kilde: "published"`, men `foldToolResults` kendte ikke typen og
      // droppede den — så filen nåede aldrig skærmen.
      type: 'file'
      filename: string
      url?: string
      attachment_id?: string
      mime_type?: string
      size_bytes?: number
      /** `published` = Jarvis lagde den ud selv. */
      kilde?: string
    }
  | {
      // Fladt persisteret progress-element (spec 2026-07-09 §5). Bærer den
      // narration live-working_step viste ("Analyserede billede…") så forløbet
      // overlever reload. parent_tool_use_id er altid null i v1 (fladt).
      //
      // `tool` + `hint` kom til 23/9-2026 (Bjørn: «Kører kommando skal helt
      // væk og erstattes af ikone»): klienten tegner værktøjets IKON og emnet
      // ved siden af hinanden i stedet for at vise serverens label-tekst
      // («Kører kommando: git status») råt. `message` bliver som den var —
      // flade tekst-kanaler (Discord, liveness-linjen) læser stadig den.
      // Begge er valgfrie: en gemt besked fra før 23/9 har dem ikke, og så
      // falder visningen tilbage til `message`.
      type: 'progress'
      tool_use_id: string
      parent_tool_use_id: string | null
      message: string
      /** Værktøjets navn (fx `bash`) — klienten slår ikonet op på det. */
      tool?: string
      /** Emnet alene (fx `git status`) — uden label foran. */
      hint?: string
      status: 'running' | 'done' | 'error'
    }

/** Lightweight type-guard: et objekt med en string `type` er et StreamEvent. */
export function isStreamEvent(value: unknown): value is StreamEvent {
  if (typeof value !== 'object' || value === null) return false
  const t = (value as { type?: unknown }).type
  return typeof t === 'string'
}

/** Groft estimat af output-tokens fra streamede blokke (≈ tegn/4). Bruges til
 *  en LIVE token-tæller i liveness-linjen — de rigtige output_tokens kommer
 *  først i message_delta ved svar-slut. */
export function approxOutputTokens(blocks: ContentBlock[]): number {
  const chars = blocks.reduce(
    (n, b) => n + (!b ? 0 : b.type === 'text' ? b.text.length : b.type === 'thinking' ? b.thinking.length : 0),
    0,
  )
  return Math.round(chars / 4)
}
