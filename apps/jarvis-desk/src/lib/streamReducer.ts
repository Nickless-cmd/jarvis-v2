import type { StreamEvent, ContentBlock } from './sseProtocol'

export type StreamStatus =
  | 'idle' | 'working' | 'interrupted' | 'hung' | 'error' | 'done' | 'reconnecting'

export interface StreamState {
  status: StreamStatus
  activeRunId: string | null
  model: string // den model det aktive/seneste run faktisk bruger (footer)
  provider: string
  lane: string
  blocks: ContentBlock[]
  workingStep: string | null // nyeste live progress-tekst (fx "Kalder analyze_image")
  recoveryNotice?: { reason: string; message: string; continuing: boolean }
  usage: { input: number; output: number; cacheHit: number; cacheMiss: number }
  /**
   * Runde-etiketter slået op på TOOL-ID — «Rettede fejl i login».
   *
   * Nøglen er kaldets id og ikke rundenummeret: en etiket der kom sent, eller
   * en tråd der blev genopbygget i en anden rækkefølge, ville ellers sætte sig
   * over de forkerte kald. 1:1 med mobilen.
   */
  rundeEtiketter?: Record<string, string>
  /**
   * Skills runtimen lagde i prompten for dette run. Holdes UDEN FOR `blocks`:
   * de er indekseret af serverens content-block-index, og en blok lagt på
   * plads 0 ville blive overskrevet af det første tekst-stykke. Se `liveBlokke`.
   */
  skillFlade?: Extract<ContentBlock, { type: 'skill_surface' }>
}

export function initialStreamState(): StreamState {
  return { status: 'idle', activeRunId: null, model: '', provider: '', lane: '', blocks: [], workingStep: null, usage: { input: 0, output: 0, cacheHit: 0, cacheMiss: 0 } }
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
  ids: string[] | undefined
): StreamState {
  const tekst = (etiket ?? '').trim()
  const liste = ids ?? []
  if (!tekst || liste.length === 0) return state
  const kort = { ...(state.rundeEtiketter ?? {}) }
  for (const id of liste) kort[id] = tekst
  return { ...state, rundeEtiketter: kort }
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
export function liveBlokke(state: Pick<StreamState, 'blocks' | 'skillFlade'>): ContentBlock[] {
  return state.skillFlade ? [state.skillFlade, ...state.blocks] : state.blocks
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
      const _sameRun = state.activeRunId === event.message.id
      return {
        ...state,
        status: 'working',
        activeRunId: event.message.id,
        model: event.message.model || state.model,
        provider: event.message.provider || state.provider,
        lane: event.message.lane || state.lane,
        blocks: _sameRun ? state.blocks : [],
        workingStep: _sameRun ? state.workingStep : null,
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
      else if (cb.type === 'tool_result') {
        const idx = blocks.findIndex((b) => b && b.type === 'tool_use' && b.id === cb.tool_use_id)
        if (idx >= 0) {
          const b = blocks[idx]
          if (b && b.type === 'tool_use') {
            blocks[idx] = { ...b, status: cb.is_error || cb.status === 'error' ? 'error' : 'done', result: cb.content ?? b.result }
          }
        }
        return { ...state, blocks }
      }
      return { ...state, blocks }
    }

    case 'content_block_delta': {
      const existing = state.blocks[event.index]
      if (!existing) return state // delta uden forudgående start → ignorér (edge-case)
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
      // SSE-v2 oversætter den gamle strøm og pakker UKENDTE event-navne som
      // `system_event` med `kind = event_name`. Etiketten kom derfor aldrig
      // frem til `case 'tool_round_label'` ovenfor — målt i produktion 14/9.
      if (event.kind === 'skill_surface') {
        return medSkillFlade(state, (event.payload ?? {}) as { matches?: unknown; primary?: unknown })
      }
      if (event.kind === 'tool_round_label') {
        const p = (event.payload ?? {}) as { etiket?: string; tool_use_ids?: string[] }
        return medEtiket(state, p.etiket, p.tool_use_ids)
      }
      // run-event bærer det rigtige run_id (message_start har det tomt).
      if (event.kind === 'run') {
        const rp = event.payload as { run_id?: string }
        return rp.run_id ? { ...state, activeRunId: rp.run_id } : state
      }
      if (event.kind === 'run_recovery') {
        const p = event.payload as { reason?: string; message?: string; continuing?: boolean }
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
        if (b && b.type === 'tool_use') blocks[idx] = { ...b, status: mapped ?? b.status, result: tr.result ?? b.result }
        return { ...state, blocks }
      }
      if (event.kind !== 'working_step') return state // ukendt kind → ignorér gracefully
      const p = event.payload as { tool_id?: string; status?: string; result?: string; detail?: string; action?: string }
      // Surface seneste progress-tekst (også steps uden tool_id, fx "thinking").
      const step = p.detail ?? p.action ?? state.workingStep
      if (!p.tool_id) return { ...state, workingStep: step }
      // b && : sparsomt-hul-guard (samme rod som tool_result ovenfor).
      const idx = state.blocks.findIndex((b) => b && b.type === 'tool_use' && b.id === p.tool_id)
      if (idx < 0) return { ...state, workingStep: step }
      const blocks = state.blocks.slice()
      const b = blocks[idx]
      if (b && b.type === 'tool_use') blocks[idx] = { ...b, status: (p.status as 'running' | 'done' | 'error') ?? b.status, result: p.result ?? b.result }
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
        },
      }

    case 'message_stop': {
      // Svaret er slut: intet kører længere. Et kald hvis resultat aldrig kom,
      // stod ellers og pulserede under et færdigt svar.
      const blocks = lukTanker(state.blocks, Date.now()).map((b) =>
        b && b.type === 'tool_use' && (b.status ?? 'running') === 'running' ? { ...b, status: 'done' as const } : b)
      return { ...state, status: 'done', blocks }
    }

    case 'tool_round_label':
      // Den DIREKTE form (SSE-v1). Den indpakkede kommer som `system_event` —
      // se `medEtiket`.
      return medEtiket(state, event.etiket, event.tool_use_ids)

    case 'skill_surface':
      return medSkillFlade(state, event)

    case 'ping':
      return state

    default:
      return state
  }
}
