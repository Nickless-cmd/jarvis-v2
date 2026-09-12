import type { ContentBlock, StreamEvent } from './sseProtocol'

export type StreamStatus = 'idle' | 'working' | 'interrupted' | 'hung' | 'error' | 'done'

export interface ResearchUiState {
  runId: string
  tier: string
  phase: string
  completedTasks: number
  totalTasks: number
  sources: number
  warning: string
  quality: string
}

export interface StreamState {
  status: StreamStatus
  activeRunId: string | null
  model: string
  provider: string
  lane: string
  blocks: ContentBlock[]
  workingStep: string | null

  research: ResearchUiState | null
  usage: { input: number; output: number; cacheHit: number; cacheMiss: number }
}

export function initialStreamState(): StreamState {
  return {
    status: 'idle',
    activeRunId: null,
    model: '',
    provider: '',
    lane: '',
    blocks: [],
    workingStep: null,
    research: null,
    usage: { input: 0, output: 0, cacheHit: 0, cacheMiss: 0 }
  }
}

function estimateOutputTokens(blocks: ContentBlock[]): number {
  let chars = 0
  for (const b of blocks) {
    if (b?.type === 'text') chars += b.text.length
    if (b?.type === 'thinking') chars += b.thinking.length
    if (b?.type === 'tool_use' && b.partialJson) chars += b.partialJson.length
  }
  return Math.round(chars / 4)
}

export function streamReducer(state: StreamState, event: StreamEvent): StreamState {
  switch (event.type) {
    case 'message_start':
      return {
        ...state,
        status: 'working',
        activeRunId: event.message.id,
        model: event.message.model,
        provider: event.message.provider,
        lane: event.message.lane,
        blocks: [],
        workingStep: null,
        research: null,
        usage: { ...state.usage, input: event.message.usage.input_tokens, output: 0 }
      }

    case 'content_block_start': {
      const blocks = state.blocks.slice()
      const cb = event.content_block
      if (cb.type === 'text') blocks[event.index] = { type: 'text', text: cb.text }
      else if (cb.type === 'thinking') blocks[event.index] = { type: 'thinking', thinking: cb.thinking }
      else if (cb.type === 'tool_use') {
        blocks[event.index] = {
          type: 'tool_use',
          id: cb.id,
          name: cb.name,
          input: cb.input,
          partialJson: '',
          status: 'running'
        }
        // Den rigtige blok er her nu — den foreløbige for SAMME værktøj skal
        // væk, ellers stod det to steder. Matches på navn: `working_step` har
        // intet id, og at tråde et nyt gennem hele rørledningen ville koste
        // mere end det gav. Landede serverens blok på det samme index, er
        // pladsen allerede overskrevet og løkken finder ingenting.
        for (let i = 0; i < blocks.length; i++) {
          const b = blocks[i]
          if (i !== event.index && b && b.type === 'tool_use' && b.foreloebig && b.name === cb.name) {
            delete blocks[i]
          }
        }
      } else if (cb.type === 'tool_result') {
        // Fold resultatet ind på sin matchende tool_use-blok (via tool_use_id) i
        // stedet for at fylde `blocks[event.index]`. Dette er MED VILJE — hvis vi
        // skrev på event.index (typisk højere end tool_use'ens index) ville en
        // efterfølgende tekst-blok på et endnu højere index efterlade et
        // `undefined`-hul mellem dem → crash på `b.type`. Ved at folde lader vi
        // tool_result-index'et stå tomt KUN hvis der aldrig kommer en højere blok;
        // og alle konsumenter densificerer nu via denseBlocks. b && : arrayet KAN
        // allerede være sparsomt.
        const idx = blocks.findIndex((b) => b && b.type === 'tool_use' && b.id === cb.tool_use_id)
        if (idx >= 0) {
          const b = blocks[idx]
          if (b && b.type === 'tool_use') {
            blocks[idx] = {
              ...b,
              status: cb.is_error || cb.status === 'error' ? 'error' : 'done',
              result: cb.content ?? b.result
            }
          }
        }
      }
      return { ...state, blocks }
    }

    case 'content_block_delta': {
      const existing = state.blocks[event.index]
      if (!existing) return state
      const blocks = state.blocks.slice()
      const d = event.delta
      if (d.type === 'text_delta' && existing.type === 'text') {
        blocks[event.index] = { ...existing, text: existing.text + d.text }
      }
      if (d.type === 'thinking_delta' && existing.type === 'thinking') {
        blocks[event.index] = { ...existing, thinking: existing.thinking + d.thinking }
      }
      if (d.type === 'input_json_delta' && existing.type === 'tool_use') {
        blocks[event.index] = {
          ...existing,
          partialJson: (existing.partialJson ?? '') + d.partial_json
        }
      }
      return { ...state, blocks, usage: { ...state.usage, output: estimateOutputTokens(blocks) } }
    }

    case 'system_event':
      if (event.kind === 'research_started') {
        return {
          ...state,
          research: {
            runId: String(event.payload.research_run_id ?? ''),
            tier: String(event.payload.tier ?? 'inline'),
            phase: 'planning',
            completedTasks: 0,
            totalTasks: 0,
            sources: 0,
            warning: '',
            quality: '',
          }
        }
      }
      if (event.kind === 'research_plan' && state.research) {
        const tasks = Array.isArray(event.payload.tasks) ? event.payload.tasks.length : 0
        return { ...state, research: { ...state.research, phase: 'planning', totalTasks: tasks } }
      }
      if (event.kind === 'research_progress' && state.research) {
        return {
          ...state,
          research: {
            ...state.research,
            phase: String(event.payload.phase ?? state.research.phase),
            completedTasks: Number(event.payload.completed_tasks ?? state.research.completedTasks),
            totalTasks: Number(event.payload.total_tasks ?? state.research.totalTasks),
            sources: Number(event.payload.sources ?? state.research.sources),
          }
        }
      }
      if (event.kind === 'research_source' && state.research) {
        return { ...state, research: { ...state.research, sources: state.research.sources + 1 } }
      }
      if (event.kind === 'research_warning' && state.research) {
        const warning = String(event.payload.error ?? event.payload.warning ?? 'Research er delvist begrænset')
        return { ...state, research: { ...state.research, warning } }
      }
      if (event.kind === 'research_completed' && state.research) {
        return {
          ...state,
          research: {
            ...state.research,
            phase: 'completed',
            sources: Number(event.payload.sources ?? state.research.sources),
            quality: String(event.payload.quality ?? ''),
          }
        }
      }
      if (event.kind === 'run') {
        const runId = typeof event.payload.run_id === 'string' ? event.payload.run_id : ''
        return runId ? { ...state, activeRunId: runId } : state
      }
      if (event.kind === 'working_step') {
        const detail =
          typeof event.payload.detail === 'string' ? event.payload.detail : state.workingStep
        const navn = typeof event.payload.action === 'string' ? event.payload.action : ''
        const status = String(event.payload.status ?? '')
        // Kun «running» og kun ÆGTE værktøjskald. «blocked» betyder at en hook
        // stoppede kaldet FØR det kørte. Og `working_step` bærer også livstegn
        // — `action: "thinking"` for «Thinking via …» og «Tænker videre ·
        // runde N» — som aldrig får et tool_use der kan rydde dem.
        //
        // `er_vaerktoej` er serverens eget flag; navnet er fallback, så
        // rettelsen virker mod den server der kører NU.
        const erVaerktoej = event.payload.er_vaerktoej === true
          || (event.payload.er_vaerktoej === undefined && navn !== 'thinking')
        if (!navn || status !== 'running' || !erVaerktoej) {
          return { ...state, workingStep: detail }
        }
        const skridt = Number(event.payload.step ?? 0)
        // Allerede annonceret (genoptag efter reconnect) → lad blokken stå.
        if (state.blocks.some((b) => b && b.type === 'tool_use' && b.foreloebig?.skridt === skridt)) {
          return { ...state, workingStep: detail }
        }
        // EN RIGTIG BLOK I TRÅDEN — ikke et kort ved siden af. Det er de samme
        // rækker MessageList allerede tegner for færdige værktøjer; de skal
        // bare findes fra annonceringen og ikke først når resultatet kommer.
        //
        // Lagt i ENDEN: serveren adresserer sine blokke på index, og et
        // vilkårligt index ville enten overskrive en tekstblok eller efterlade
        // et hul. Kommer serverens rigtige blok på samme index, erstatter den
        // denne af sig selv.
        const medPlads = state.blocks.slice()
        medPlads[medPlads.length] = {
          type: 'tool_use',
          id: `foreloebig:${skridt}`,
          name: navn,
          input: {},
          partialJson: '',
          status: 'running',
          foreloebig: {
            startet: Date.now(),
            skridt,
            etiket: typeof detail === 'string' ? detail : navn,
          },
        }
        return { ...state, workingStep: detail, blocks: medPlads }
      }
      return state

    case 'message_delta':
      return {
        ...state,
        usage: {
          input: event.usage.input_tokens || state.usage.input,
          output: event.usage.output_tokens,
          cacheHit: event.usage.cache_hit_tokens,
          cacheMiss: event.usage.cache_miss_tokens
        }
      }

    case 'message_stop': {
      // Et værktøj hvis rigtige blok aldrig kom (afbrudt run, tabt
      // forbindelse) ville ellers stå og snurre under et svar der er slut.
      const uden = state.blocks.slice()
      for (let i = 0; i < uden.length; i++) {
        const b = uden[i]
        if (b && b.type === 'tool_use' && b.foreloebig) delete uden[i]
      }
      return { ...state, status: 'done', blocks: uden }
    }

    case 'round_restart_discard_partial':
      // §4.1 CLIENT CONTRACT: en runde fejlede mid-stream og re-køres. Drop den
      // ikke-finaliserede on-screen partial (blocks) for dette run, så den
      // friske re-run-stream ikke render'es OVENPÅ den fejlede partial (dublet).
      // Advisory: serverens persisterede svar er allerede trunkeret, så selv en
      // klient der ignorerede dette ville forblive korrekt i historikken — kun
      // den live visning ville kortvarigt vise dubleret tekst. `retry`-eventet
      // (ren "Reconnecting n/m"-signalering) falder gennem default = no-op,
      // præcis som desk's reducer.
      return { ...state, status: 'working', blocks: [] }

    default:
      return state
  }
}
