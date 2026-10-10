import type { StreamEvent, ContentBlock } from './sseProtocol'

const LIVE_TOOL_OUTPUT_MAX_CHARS = 65_536

export type StreamStatus =
  | 'idle' | 'working' | 'interrupted' | 'hung' | 'error' | 'done' | 'reconnecting'

export interface StreamState {
  status: StreamStatus
  activeRunId: string | null
  model: string // den model det aktive/seneste run faktisk bruger (footer)
  provider: string
  lane: string
  blocks: ContentBlock[]
  provisionalText: string
  provisionalBlockIndex: number | null
  provisionalMissingBlockIndex: number | null
  workingStep: string | null // nyeste live progress-tekst (fx "Kalder analyze_image")
  finalAnswerStarted: boolean // serveren har bekræftet slutsvar før første synlige delta
  recoveryNotice?: { reason: string; message: string; continuing: boolean }
  usage: { input: number; output: number; cacheHit: number; cacheMiss: number
           // Maalt paa SERVEREN (core/services/svar_tempo), ikke hentet hos
           // udbyderen: saa betyder tallet det samme uanset om turen gik
           // gennem DeepSeek eller Ollama Cloud. `null` = ikke maalt.
           ttftMs: number | null; tokPerSek: number | null }
  /**
   * Runde-etiketter slået op på TOOL-ID — «Rettede fejl i login».
   *
   * Nøglen er kaldets id og ikke rundenummeret: en etiket der kom sent, eller
   * en tråd der blev genopbygget i en anden rækkefølge, ville ellers sætte sig
   * over de forkerte kald. 1:1 med mobilen.
   */
  rundeEtiketter?: Record<string, string>
  /** Tænke-resuméer slået op på kald-id — visningen «thinking» (19/9-2026). */
  tankeResumeer?: Record<string, string>
  /**
   * Skills runtimen lagde i prompten for dette run. Holdes UDEN FOR `blocks`:
   * de er indekseret af serverens content-block-index, og en blok lagt på
   * plads 0 ville blive overskrevet af det første tekst-stykke. Se `liveBlokke`.
   */
  skillFlade?: Extract<ContentBlock, { type: 'skill_surface' }>
}

export function initialStreamState(): StreamState {
  return { status: 'idle', activeRunId: null, model: '', provider: '', lane: '', blocks: [], provisionalText: '', provisionalBlockIndex: null, provisionalMissingBlockIndex: null, workingStep: null, finalAnswerStarted: false, usage: { input: 0, output: 0, cacheHit: 0, cacheMiss: 0, ttftMs: null, tokPerSek: null } }
}

/** Estimer output-tokens fra akkumuleret tekst/tænkning i blocks. Bruges
 * mens streaming kører, fordi Anthropic kun sender det faktiske tal i
 * `message_delta` (typisk én gang til sidst). Heuristik: ~4 chars/token. */
function estimateOutputTokens(blocks: ContentBlock[]): number {
  let chars = 0
  for (const b of blocks) {
    if (!b) continue
    if (b.type === 'text') chars += b.text.length
    else if (b.type === 'thinking') chars += b.thinking.length
    else if (b.type === 'tool_use' && b.partialJson) chars += b.partialJson.length
  }
  return Math.round(chars / 4)
}

/**
 * Ren reducer: (state, v2event) → state. Ingen netværk, ingen side-effekter.
 * Akkumulerer content-blocks pr. index og styrer status-overgange.
 * Status hung/interrupted/error sættes UDENFOR reduceren (fra streamClient-
 * handlers i StreamContext), ikke fra events.
 */
/**
 * Læg en runde-etiket ind, slået op på de kald den opsummerer. 1:1 med mobilen.
 *
 * Ét sted, fordi etiketten kommer ad TO veje: direkte (SSE-v1) og pakket ind
 * som `system_event` (SSE-v2). To kopier ville før eller siden komme til at
 * opføre sig forskelligt.
 */
function medEtiket(
  state: StreamState,
  etiket: string | undefined,
  ids: string[] | undefined,
  tankeResume?: string,
): StreamState {
  const tekst = (etiket ?? '').trim()
  const resume = (tankeResume ?? '').trim()
  const liste = ids ?? []
  if (liste.length === 0 || (!tekst && !resume)) return state
  let ud = state
  if (tekst) {
    const kort = { ...(state.rundeEtiketter ?? {}) }
    for (const id of liste) kort[id] = tekst
    ud = { ...ud, rundeEtiketter: kort }
  }
  // Tænke-resuméet rider med i samme event (visningen «thinking»); det kan
  // stå alene, når Jarvis selv skrev linjen og der ingen etiket blev lavet.
  if (resume) {
    const kort = { ...(state.tankeResumeer ?? {}) }
    for (const id of liste) kort[id] = resume
    ud = { ...ud, tankeResumeer: kort }
  }
  return ud
}

/** Læg skill-fladen ind, uanset om den kom direkte eller pakket (se medEtiket). */
function medSkillFlade(state: StreamState, p: { matches?: unknown; primary?: unknown }): StreamState {
  const matches = Array.isArray(p.matches)
    ? (p.matches as unknown[]).flatMap((m) => {
      const mm = m as { name?: unknown; score?: unknown; primary?: unknown }
      return typeof mm?.name === 'string' && typeof mm.score === 'number'
        ? [{ name: mm.name, score: mm.score, primary: !!mm.primary }]
        : []
    })
    : []
  if (matches.length === 0) return state
  return { ...state, skillFlade: { type: 'skill_surface', matches, primary: !!p.primary || matches.some((m) => m.primary) } }
}

/** De blokke en LIVE besked tegnes af: skill-fladen først, så strømmen. */
const liveBlokkeCache = new WeakMap<ContentBlock[], {
  skillFlade: Extract<ContentBlock, { type: 'skill_surface' }>
  result: ContentBlock[]
}>()

export function liveBlokke(state: Pick<StreamState, 'blocks' | 'skillFlade'> & Partial<Pick<StreamState, 'provisionalText' | 'provisionalBlockIndex'>>): ContentBlock[] {
  if (state.provisionalText) {
    const blocks = state.provisionalBlockIndex == null
      ? state.blocks.filter((b): b is ContentBlock => !!b)
      : state.blocks.filter((b, index): b is ContentBlock => !!b && index !== state.provisionalBlockIndex)
    return [
      ...(state.skillFlade ? [state.skillFlade] : []),
      ...blocks,
      { type: 'text', text: state.provisionalText },
    ]
  }
  if (!state.skillFlade) return state.blocks
  const cached = liveBlokkeCache.get(state.blocks)
  if (cached?.skillFlade === state.skillFlade) return cached.result
  const result = [state.skillFlade, ...state.blocks]
  liveBlokkeCache.set(state.blocks, { skillFlade: state.skillFlade, result })
  return result
}

/** Serverens udfald → linjens status. Alt der ikke kører mere, er færdigt:
 *  en ukendt status («blocked», «timeout» …) lod før kaldet stå og pulsere. */
const FEJL_STATUS = new Set(['error', 'failed', 'blocked', 'denied', 'rejected', 'timeout', 'cancelled', 'canceled'])
export function udfaldsStatus(status: string | undefined): 'running' | 'done' | 'error' | undefined {
  if (!status) return undefined
  if (status === 'running' || status === 'pending' || status === 'started') return 'running'
  return FEJL_STATUS.has(status) ? 'error' : 'done'
}

/** Luk åbne tanker: en tanke er slut når noget nyt begynder. `undtagen` er
 *  blokken der starter — et replay af den samme tanke må ikke lukke sig selv. */
function lukTanker(blocks: ContentBlock[], nu: number, undtagen = -1): ContentBlock[] {
  let ændret = false
  const ud = blocks.map((b, i) => {
    if (i !== undtagen && b && b.type === 'thinking' && b.seconds == null && b.startet != null) {
      ændret = true
      return { ...b, seconds: Math.max(0, (nu - b.startet) / 1000) }
    }
    return b
  })
  return ændret ? ud : blocks
}

export function streamReducer(state: StreamState, event: StreamEvent): StreamState {
  switch (event.type) {
    case 'message_start': {
      // Nyt run → output-tokens nulstilles. Live-estimat bygges op via
      // content_block_delta indtil message_delta lander med det rigtige tal.
      // ── TOOL-BLOK-VANISH-FIX (Bjørn 4. jul) ──────────────────────────────
      // FØR: blocks nulstilledes ALTID → et 2. message_start for SAMME run
      // (reconnect / relay-replay fra offset 0 / server-autoritativ genudsendelse)
      // wipede tool-blokkene + første tekst brugeren allerede så → "tool-results
      // forsvinder, og svaret bang'er ind løsrevet bagefter". Nu: bevar blocks når
      // det er SAMME run (activeRunId uændret) — replay'ens content_block_start
      // SÆTTER hvert index på ny (linje ~65), så staten genopbygges rent uden
      // dobling. Kun et ÆGTE nyt run (nyt id) nulstiller.
      // ── BLINKET (Bjørn 1/10-2026) ────────────────────────────────────────
      // «nogen gange starter den op igen 5-7 sekunder og lukker ned igen uden
      // der sker noget, og så blinker chatview lige en gang og så lander hele
      // hans besked.»
      //
      // `message_start` bærer kun et run_id hvis et tidligere legacy-event har
      // båret det (visible_runs_sse_v2.py:705) — kommer den før, er id'et TOMT.
      // `system_event(kind='run')` sætter derefter det rigtige. Ved et replay
      // kom `message_start` igen med "" og ramte `_sameRun` mod det rigtige id:
      // falsk → blocks ryddet → blinket → og replay'et fyldte hele svaret ind
      // på én gang.
      //
      // Et tomt id bærer INGEN information. Det må hverken erklære et nyt run
      // eller overskrive det id vi allerede kender. Et ÆGTE nyt id nulstiller
      // stadig — det er hele pointen med vagten.
      const _indkommende = event.message.id || ''
      const _sameRun = !_indkommende || state.activeRunId === _indkommende
      return {
        ...state,
        status: 'working',
        activeRunId: _indkommende || state.activeRunId,
        model: event.message.model || state.model,
        provider: event.message.provider || state.provider,
        lane: event.message.lane || state.lane,
        blocks: _sameRun ? state.blocks : [],
        provisionalText: _sameRun ? state.provisionalText : '',
        provisionalBlockIndex: _sameRun ? state.provisionalBlockIndex : null,
        provisionalMissingBlockIndex: _sameRun ? state.provisionalMissingBlockIndex : null,
        workingStep: _sameRun ? state.workingStep : null,
        // Et NYT run rydder genoptagelses-varslet. Foer var `message_delta`
        // med stop_reason end_turn/completed den eneste vej ud — og en tvungen
        // slutrunde har per definition ikke det stop_reason: det er selve
        // udloeseren. Betingelsen der rejste banneret udelukkede altsaa vejen
        // der fjernede det, saa det blev staaende resten af sessionen (Bjoern
        // 30/9-2026: «saa forsvinder den badge ikk igen fra desk»).
        //
        // Varslet siger «Jarvis fortsaetter automatisk fra sit checkpoint».
        // Naar fortsaettelsen faktisk koerer, har det sagt sit — og fejler den
        // ogsaa, kommer der et nyt.
        recoveryNotice: _sameRun ? state.recoveryNotice : undefined,
        finalAnswerStarted: _sameRun ? state.finalAnswerStarted : false,
        skillFlade: _sameRun ? state.skillFlade : undefined,
        usage: {
          ...state.usage,
          input: event.message.usage.input_tokens,
          output: _sameRun ? state.usage.output : 0,
        },
      }
    }

    case 'content_block_start': {
      const nu = Date.now()
      const cb = event.content_block
      const blocks = (cb.type === 'tool_result' ? state.blocks : lukTanker(state.blocks, nu, event.index)).slice()
      const forrige = state.blocks[event.index]
      if (cb.type === 'text') blocks[event.index] = { type: 'text', text: cb.text ?? '' }
      else if (cb.type === 'thinking') blocks[event.index] = {
        type: 'thinking', thinking: cb.thinking ?? '',
        startet: forrige && forrige.type === 'thinking' && forrige.startet != null ? forrige.startet : nu,
      }
      else if (cb.type === 'tool_use') blocks[event.index] = {
        type: 'tool_use', id: cb.id, name: cb.name, input: cb.input ?? {}, partialJson: '', status: 'running',
        startet: forrige && forrige.type === 'tool_use' && forrige.startet != null ? forrige.startet : nu,
      }
      // Billedet fandtes ikke i streamen før 27/9-2026: værktøjet lagde en
      // note fra sig, og blokken blev først bygget når svaret blev gemt.
      // Renderen har haft grenen hele tiden (`BlocksRenderer`: `block.src ?
      // <ImageBlock/> : …`) — den fik bare aldrig noget. Nu gør den.
      else if (cb.type === 'image') blocks[event.index] = {
        type: 'image',
        src: cb.src,
        alt: cb.alt,
        attachment_id: cb.attachment_id,
        url: cb.url,
        filename: cb.filename,
        mime_type: cb.mime_type,
        kilde: cb.kilde,
        tool_use_id: cb.tool_use_id,
      }
      // UDGIVET fil eller video UNDER kørslen (7/10-2026).
      //
      // Renderen har hele tiden kunnet vise dem (`BlocksRenderer`,
      // `foldToolResults`), men grenen fandtes ikke her — og udsenderen
      // sendte dem heller ikke. En widget er `text/html` → typen `file`, så
      // fladen faldt til jorden i den levende strøm og dukkede først op når
      // tråden blev genindlæst fra `content_json`.
      else if (cb.type === 'file') blocks[event.index] = {
        // Tilstandstypen `file` bærer KUN referencen — `src`/`alt`/
        // `tool_use_id` findes ikke på den (kun på `image` og `video`).
        // Udsenderen sender dem heller ikke for en fil.
        type: 'file',
        filename: cb.filename,
        url: cb.url,
        attachment_id: cb.attachment_id,
        mime_type: cb.mime_type,
        size_bytes: cb.size_bytes,
        kilde: cb.kilde,
      }
      else if (cb.type === 'video') blocks[event.index] = {
        type: 'video',
        src: cb.src,
        alt: cb.alt,
        attachment_id: cb.attachment_id,
        url: cb.url,
        filename: cb.filename,
        mime_type: cb.mime_type,
        size_bytes: cb.size_bytes,
        kilde: cb.kilde,
        tool_use_id: cb.tool_use_id,
      }
      else if (cb.type === 'tool_result') {
        const idx = blocks.findIndex((b) => b && b.type === 'tool_use' && b.id === cb.tool_use_id)
        if (idx >= 0) {
          const b = blocks[idx]
          if (b && b.type === 'tool_use') {
            blocks[idx] = {
              ...b,
              status: cb.is_error || cb.status === 'error' ? 'error' : 'done',
              result: cb.content ?? b.result,
              liveOutput: undefined,
              liveOutputSeq: undefined,
              liveOutputTruncated: undefined,
            }
          }
        }
        return { ...state, blocks }
      }
      return {
        ...state, blocks,
        provisionalBlockIndex: cb.type === 'text' && state.provisionalText
          ? event.index : state.provisionalBlockIndex,
      }
    }

    case 'content_block_delta': {
      const existing = state.blocks[event.index]
      if (!existing) return event.delta.type === 'text_delta' && state.provisionalText
        ? { ...state, provisionalMissingBlockIndex: event.index }
        : state
      const blocks = state.blocks.slice()
      const d = event.delta
      if (d.type === 'text_delta' && existing.type === 'text') blocks[event.index] = { ...existing, text: existing.text + d.text }
      else if (d.type === 'thinking_delta' && existing.type === 'thinking') blocks[event.index] = { ...existing, thinking: existing.thinking + d.thinking }
      else if (d.type === 'input_json_delta' && existing.type === 'tool_use') blocks[event.index] = { ...existing, partialJson: (existing.partialJson ?? '') + d.partial_json }
      // Live-estimer output-tokens fra ny content. Erstattes af det rigtige
      // tal når message_delta lander til sidst.
      return { ...state, blocks, usage: { ...state.usage, output: estimateOutputTokens(blocks) } }
    }

    case 'content_block_stop':
      return state

    case 'system_event': {
      if (event.kind === 'tool_output_delta') {
        const p = event.payload as {
          run_id?: unknown
          tool_use_id?: unknown
          seq?: unknown
          chunk?: unknown
          truncated?: unknown
        }
        if (typeof p.run_id !== 'string' || p.run_id !== state.activeRunId
          || typeof p.tool_use_id !== 'string' || typeof p.seq !== 'number'
          || !Number.isFinite(p.seq) || typeof p.chunk !== 'string') return state
        const idx = state.blocks.findIndex((b) => b && b.type === 'tool_use' && b.id === p.tool_use_id)
        if (idx < 0) return state
        const current = state.blocks[idx]
        if (!current || current.type !== 'tool_use'
          || (current.status ?? 'running') !== 'running'
          || p.seq <= (current.liveOutputSeq ?? 0)) return state
        const combined = (current.liveOutput ?? '') + p.chunk
        const clientTruncated = combined.length > LIVE_TOOL_OUTPUT_MAX_CHARS
        const blocks = state.blocks.slice()
        blocks[idx] = {
          ...current,
          liveOutput: clientTruncated ? combined.slice(-LIVE_TOOL_OUTPUT_MAX_CHARS) : combined,
          liveOutputSeq: p.seq,
          liveOutputTruncated: current.liveOutputTruncated || p.truncated === true || clientTruncated,
        }
        return { ...state, blocks }
      }
      if (event.kind === 'provisional_text_delta') {
        const runId = String(event.payload?.run_id ?? '')
        if (!runId || (state.status === 'working' && state.activeRunId && runId !== state.activeRunId)
          || (state.status === 'done' && state.activeRunId === runId)) return state
        const delta = String(event.payload?.delta ?? '')
        if (!delta) return state
        // Ved sen tilkobling kan message_start være faldet ud af relay-bufferen.
        // Deltaens run-id er nok til at starte en ny live-visning.
        const nytRun = !!state.activeRunId && state.activeRunId !== runId
        return {
          ...state, status: 'working', activeRunId: runId,
          blocks: nytRun ? [] : state.blocks,
          provisionalText: (nytRun ? '' : state.provisionalText) + delta,
          provisionalBlockIndex: nytRun ? null : state.provisionalBlockIndex,
          provisionalMissingBlockIndex: nytRun ? null : state.provisionalMissingBlockIndex,
          finalAnswerStarted: nytRun ? false : state.finalAnswerStarted,
        }
      }
      if (event.kind === 'provisional_text_commit') {
        if (String(event.payload?.run_id ?? '') !== state.activeRunId) return state
        const blocks = state.blocks.slice()
        if (state.provisionalMissingBlockIndex != null && state.provisionalText) {
          blocks[state.provisionalMissingBlockIndex] = { type: 'text', text: state.provisionalText }
        }
        return { ...state, blocks, provisionalText: '', provisionalBlockIndex: null,
          provisionalMissingBlockIndex: null }
      }
      if (event.kind === 'final_answer_start') {
        const rid = String(event.payload?.run_id ?? '')
        return rid && rid === state.activeRunId
          ? { ...state, finalAnswerStarted: true }
          : state
      }
      // SSE-v2 oversætter den gamle strøm og pakker UKENDTE event-navne som
      // `system_event` med `kind = event_name`. Etiketten kom derfor aldrig
      // frem til `case 'tool_round_label'` ovenfor — målt i produktion 14/9.
      if (event.kind === 'skill_surface') {
        return medSkillFlade(state, (event.payload ?? {}) as { matches?: unknown; primary?: unknown })
      }
      if (event.kind === 'tool_round_label') {
        const p = (event.payload ?? {}) as { etiket?: string; tool_use_ids?: string[]; tanke_resume?: string }
        return medEtiket(state, p.etiket, p.tool_use_ids, p.tanke_resume)
      }
      // run-event bærer det rigtige run_id (message_start har det tomt).
      if (event.kind === 'run') {
        const rp = event.payload as { run_id?: string }
        return rp.run_id ? { ...state, activeRunId: rp.run_id } : state
      }
      if (event.kind === 'run_recovery') {
        const p = event.payload as { reason?: string; message?: string; continuing?: boolean; ryddet?: boolean }
        // Han trykkede det vaek. Banneret havde ingen knap overhovedet, saa et
        // varsel der overlevede sin egen ryddevej kunne ikke fjernes af nogen.
        if (p.ryddet) return { ...state, recoveryNotice: undefined }
        if (!p.message) return state
        return {
          ...state,
          recoveryNotice: {
            reason: p.reason || 'unknown',
            message: p.message,
            continuing: p.continuing !== false,
          },
        }
      }
      // Phase 2: tool_result formidler en tool_use-blocks udfald (status)
      // bundet til tool_use_id.
      if (event.kind === 'tool_result') {
        const tr = event.payload as { tool_use_id?: string; status?: string; result?: string }
        if (!tr.tool_use_id) return state
        // b && : state.blocks kan være SPARSOMT (foldede tool_result-content-blok-
        // indices efterlader undefined-huller) → `b.type` på et hul crashede hele
        // reduceren → sort skærm (Bjørn 10. jul, dual-emit content-blok+system_event).
        const idx = state.blocks.findIndex((b) => b && b.type === 'tool_use' && b.id === tr.tool_use_id)
        if (idx < 0) return state
        const mapped = udfaldsStatus(tr.status)
        const blocks = state.blocks.slice()
        const b = blocks[idx]
        if (b && b.type === 'tool_use') blocks[idx] = {
          ...b,
          status: mapped ?? b.status,
          result: tr.result ?? b.result,
          liveOutput: undefined,
          liveOutputSeq: undefined,
          liveOutputTruncated: undefined,
        }
        return { ...state, blocks }
      }
      if (event.kind !== 'working_step') return state // ukendt kind → ignorér gracefully
      const p = event.payload as { tool_id?: string; status?: string; result?: string; detail?: string; action?: string }
      // Thinking er allerede liveness-indikatorens egen tilstand. Livstegnet
      // rydder samtidig en gammel værktøjsetiket efter et afsluttet kald.
      if (p.action === 'thinking' && !p.tool_id) return { ...state, workingStep: null }
      // Surface seneste progress-tekst (også steps uden tool_id, fx "thinking").
      const step = p.detail ?? p.action ?? state.workingStep
      if (!p.tool_id) return { ...state, workingStep: step }
      // b && : sparsomt-hul-guard (samme rod som tool_result ovenfor).
      const idx = state.blocks.findIndex((b) => b && b.type === 'tool_use' && b.id === p.tool_id)
      if (idx < 0) return { ...state, workingStep: step }
      const blocks = state.blocks.slice()
      const b = blocks[idx]
      if (b && b.type === 'tool_use') {
        const nextStatus = (p.status as 'running' | 'done' | 'error') ?? b.status
        const terminal = nextStatus === 'done' || nextStatus === 'error'
        blocks[idx] = {
          ...b,
          status: nextStatus,
          result: p.result ?? b.result,
          liveOutput: terminal ? undefined : b.liveOutput,
          liveOutputSeq: terminal ? undefined : b.liveOutputSeq,
          liveOutputTruncated: terminal ? undefined : b.liveOutputTruncated,
        }
      }
      return { ...state, blocks, workingStep: step }
    }

    case 'message_delta':
      return {
        ...state,
        recoveryNotice: ['end_turn', 'completed'].includes(event.delta.stop_reason)
          ? undefined
          : state.recoveryNotice,
        usage: {
          ...state.usage,
          // input kommer i message_delta (v2 message_start bærer ikke usage) —
          // bruges af context-ringen (#9). Behold tidligere ved 0.
          input: event.usage.input_tokens || state.usage.input,
          output: event.usage.output_tokens,
          cacheHit: event.usage.cache_hit_tokens ?? state.usage.cacheHit,
          cacheMiss: event.usage.cache_miss_tokens ?? state.usage.cacheMiss,
          // `??`, ikke `||`: en maalt 0 er et svar, og `||` ville kaste den
          // vaek sammen med `null`. Serveren udelader feltet naar det ikke
          // kunne maales, saa `undefined` betyder «behold hvad vi havde».
          ttftMs: event.usage.ttft_ms ?? state.usage.ttftMs,
          tokPerSek: event.usage.tok_per_sek ?? state.usage.tokPerSek,
        },
      }

    case 'message_stop': {
      // Svaret er slut: intet kører længere. Et kald hvis resultat aldrig kom,
      // stod ellers og pulserede under et færdigt svar.
      const blocks = lukTanker(state.blocks, Date.now()).map((b) =>
        b && b.type === 'tool_use' && (b.status ?? 'running') === 'running' ? { ...b, status: 'done' as const } : b)
      if (state.provisionalMissingBlockIndex != null && state.provisionalText) {
        blocks[state.provisionalMissingBlockIndex] = { type: 'text', text: state.provisionalText }
      }
      return { ...state, status: 'done', blocks, provisionalText: '',
        provisionalBlockIndex: null, provisionalMissingBlockIndex: null }
    }

    case 'tool_round_label':
      // Den DIREKTE form (SSE-v1). Den indpakkede kommer som `system_event` —
      // se `medEtiket`.
      return medEtiket(state, event.etiket, event.tool_use_ids, event.tanke_resume)

    case 'skill_surface':
      return medSkillFlade(state, event)

    case 'ping':
      return state

    default:
      return state
  }
}
