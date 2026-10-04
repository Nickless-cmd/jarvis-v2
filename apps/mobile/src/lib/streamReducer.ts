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
  /** Løbende tekst, som serveren endnu ikke har klassificeret som syntese/slutsvar. */
  provisionalText: string
  /** Den bekræftede blok holdes skjult, indtil den kan afløse forhåndsvisningen. */
  provisionalBlockIndex: number | null
  /** Bekræftet tekst-delta uden startblok efter et relay-gap. */
  provisionalMissingBlockIndex: number | null
  workingStep: string | null
  /**
   * Værktøjets RÅ navn fra `working_step` (fx `read_file`).
   *
   * `workingStep` bærer serverens færdige label — «Læser fil: X» — og den
   * alene kunne kun give maskinens stemme. Navnet her gør det muligt at
   * bygge sætningen i Jarvis' egen (se `lib/arbejdslinje.ts`).
   */
  workingAction: string | null

  /**
   * Serveren har bekræftet at ARBEJDSFASEN er slut — `final_answer_start`.
   *
   * Det er ikke «der er kommet tekst efter værktøjet»: rundeopsummeringen
   * (`tool_use_summary`) lander lige når værktøjet er færdigt, og talte den
   * som «svaret er begyndt», døde runde-linjens shimmer i præcis det vindue
   * hvor modellen tænker på næste runde. Bjørn 3/10-2026 (desk): «shimmer
   * skal fortsætte til første tænke i næste runde, ellers opstår der et par
   * sekunders stilhed hvor du tænker».
   */
  finalAnswerStarted: boolean

  research: ResearchUiState | null
  usage: { input: number; output: number; cacheHit: number; cacheMiss: number }

  /**
   * Runde-etiketter slået op på TOOL-ID — «Rettede fejl i login».
   *
   * Nøglen er kaldets id og ikke rundenummeret, fordi etiketten skal hæfte sig
   * på de kald den opsummerer. En etiket der kom sent, eller en tråd der blev
   * genopbygget i en anden rækkefølge, ville ellers sætte sig over de forkerte.
   */
  rundeEtiketter?: Record<string, string>

  /** Tænke-resuméer slået op på kald-id — visningen «thinking» (19/9-2026). */
  tankeResumeer?: Record<string, string>

  /**
   * Skills runtimen lagde i prompten for DENNE kørsel — `skill_surface`.
   * Tegnes øverst i den levende tur som en skill-linje (desk'ens
   * `skillFlade`, portet 19/9-2026). Nulstilles når en ny kørsel starter.
   */
  skillFlade?: { matches: { name: string; score: number; primary: boolean }[]; primary: boolean }
}

/** Læg skill-fladen ind, uanset om den kom direkte eller pakket — som desk. */
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
  return { ...state, skillFlade: { matches, primary: !!p.primary || matches.some((m) => m.primary) } }
}

export function initialStreamState(): StreamState {
  return {
    status: 'idle',
    activeRunId: null,
    model: '',
    provider: '',
    lane: '',
    blocks: [],
    provisionalText: '',
    provisionalBlockIndex: null,
    provisionalMissingBlockIndex: null,
    workingStep: null,
    workingAction: null,
    finalAnswerStarted: false,
    research: null,
    usage: { input: 0, output: 0, cacheHit: 0, cacheMiss: 0 }
  }
}

/** Vis uafklaret tekst live uden at vise den bekræftede kopi to gange. */
export function visibleStreamBlocks(state: StreamState): ContentBlock[] {
  if (!state.provisionalText) return state.blocks
  const blocks = state.provisionalBlockIndex == null
    ? state.blocks
    : state.blocks.filter((_, index) => index !== state.provisionalBlockIndex)
  return [...blocks, { type: 'text', text: state.provisionalText }]
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

/**
 * Læg en runde-etiket ind, slået op på de kald den opsummerer.
 *
 * Rører ALDRIG blokkene: ændrede den strømmen, kunne en sen overskrift flytte
 * rundt på det der allerede står på skærmen. Uden id-er er der intet at hæfte
 * den på, og en etiket der svæver ville sætte sig over det forkerte.
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
  // Tænke-resuméet (visningen «thinking») rider med i samme event — som desk.
  if (resume) {
    const kort = { ...(state.tankeResumeer ?? {}) }
    for (const id of liste) kort[id] = resume
    ud = { ...ud, tankeResumeer: kort }
  }
  return ud
}

export function streamReducer(state: StreamState, event: StreamEvent): StreamState {
  switch (event.type) {
    case 'message_start': {
      // ── BLINKET (Bjørn 1/10-2026) ────────────────────────────────────────
      // `message_start` bærer kun et run_id hvis et tidligere legacy-event har
      // båret det (visible_runs_sse_v2.py:705) — kommer den før, er id'et TOMT,
      // og `system_event(kind='run')` sætter derefter det rigtige. Her blev
      // `blocks` ryddet UBETINGET ved hvert message_start, så et replay eller en
      // genforbindelse slettede hele svaret og fyldte det ind igen på én gang.
      //
      // Desk havde en vagt mod netop det (samme run → behold blokke), men den
      // sammenlignede mod et tomt id og fejlede. Mobilen havde ingen vagt.
      // Begge rettet samme dag — de to klienter må ikke drive fra hinanden.
      const _indkommende = event.message.id || ''
      const _sammeRun = !_indkommende || _indkommende === state.activeRunId
      return {
        ...state,
        status: 'working',
        activeRunId: _indkommende || state.activeRunId,
        model: event.message.model,
        provider: event.message.provider,
        lane: event.message.lane,
        blocks: _sammeRun ? state.blocks : [],
        // Samme vagt som `blocks` — og som desk har haft siden 1/10.
        // Et tomt eller identisk run-id må IKKE rive den LIVE foreløbige
        // tekst væk. Uden vagten forsvandt den streamende syntese ved en
        // genforbindelse/replay, og `provisionalBlockIndex = null` gjorde
        // at blokken ikke længere blev filtreret — så kom teksten igen som
        // ÉT hug. Det er præcis dumpet `blocks`-vagten blev indført mod;
        // rettelsen 1/10 ramte kun `blocks` og glemte de tre felter her.
        provisionalText: _sammeRun ? state.provisionalText : '',
        provisionalBlockIndex: _sammeRun ? state.provisionalBlockIndex : null,
        provisionalMissingBlockIndex: _sammeRun ? state.provisionalMissingBlockIndex : null,
        // En NY kørsel har sin egen skill-flade; samme kørsel beholder sin.
        skillFlade: _sammeRun ? state.skillFlade : undefined,
        workingStep: null,
        workingAction: null,
        // En NY kørsel har ikke begyndt sit slutsvar endnu. Samme run beholder
        // flaget — en genforbindelse midt i svaret må ikke tænde shimmeren igen.
        finalAnswerStarted: _sammeRun ? state.finalAnswerStarted : false,
        research: null,
        usage: { ...state.usage, input: event.message.usage.input_tokens, output: 0 }
      }
    }

    case 'content_block_start': {
      const blocks = state.blocks.slice()
      const cb = event.content_block
      if (cb.type === 'text') blocks[event.index] = { type: 'text', text: cb.text }
      else if (cb.type === 'thinking') {
        // Taenketiden maales HER. Serveren sender den ikke, og ThinkingSummary
        // har kunnet vise «Taenkte i X s» hele tiden — feltet blev bare aldrig
        // fyldt af nogen. Endnu et tilfaelde af built-but-not-connected.
        blocks[event.index] = {
          type: 'thinking', thinking: cb.thinking, startet: Date.now(), sidst: Date.now(),
        }
      }
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
      } else if (cb.type === 'image') {
        // Billedet fandtes ikke i streamen før 27/9-2026: værktøjet lagde en
        // note fra sig, og blokken blev først bygget når svaret blev gemt.
        // Animationen vistes, fordi den er sin egen komponent — billedet havde
        // ingen blok at bo i før turen var slut.
        blocks[event.index] = {
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
      return {
        ...state, blocks,
        provisionalBlockIndex: cb.type === 'text' && state.provisionalText
          ? event.index : state.provisionalBlockIndex,
      }
    }

    case 'content_block_delta': {
      const existing = state.blocks[event.index]
      if (!existing) {
        return event.delta.type === 'text_delta' && state.provisionalText
          ? { ...state, provisionalMissingBlockIndex: event.index }
          : state
      }
      const blocks = state.blocks.slice()
      const d = event.delta
      if (d.type === 'text_delta' && existing.type === 'text') {
        blocks[event.index] = { ...existing, text: existing.text + d.text }
      }
      if (d.type === 'thinking_delta' && existing.type === 'thinking') {
        blocks[event.index] = {
          ...existing,
          thinking: existing.thinking + d.thinking,
          startet: existing.startet ?? Date.now(),
          sidst: Date.now(),
        }
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
      if (event.kind === 'provisional_text_delta') {
        const runId = String(event.payload.run_id ?? '')
        if (!runId || (state.status === 'working' && state.activeRunId && runId !== state.activeRunId)
          || (state.status === 'done' && state.activeRunId === runId)) return state
        const delta = String(event.payload.delta ?? '')
        if (!delta) return state
        // Ved sen tilkobling kan ring-bufferen have rullet message_start ud.
        // Deltaen bærer stadig run-id, så den kan vække live-visningen selv.
        const nytRun = state.activeRunId && state.activeRunId !== runId
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
        if (String(event.payload.run_id ?? '') !== state.activeRunId) return state
        const blocks = state.blocks.slice()
        if (state.provisionalMissingBlockIndex != null && state.provisionalText) {
          blocks[state.provisionalMissingBlockIndex] = { type: 'text', text: state.provisionalText }
        }
        return {
          ...state, blocks, provisionalText: '', provisionalBlockIndex: null,
          provisionalMissingBlockIndex: null,
        }
      }
      // Arbejdsfasen er slut. Signalet kommer fra serveren (`visible_runs_sse_v2
      // .py:450`) og er UAFHÆNGIGT af hvilke blokke der lander — derfor kan det
      // skelne «han tænker på næste runde» fra «han er begyndt at svare», hvor
      // rundeopsummeringen ikke kan. Desk bruger det til shimmeren
      // (`RaekkeTranskript.tsx:341`); mobilen havde hverken flaget eller grenen.
      //
      // Run-id'et tjekkes, så en FORSINKET `final_answer_start` fra en tidligere
      // kørsel ikke slukker shimmeren i den vi ser på nu.
      if (event.kind === 'final_answer_start') {
        const rid = String(event.payload.run_id ?? '')
        return rid && rid === state.activeRunId
          ? { ...state, finalAnswerStarted: true }
          : state
      }
      // SSE-v2 oversætter den gamle strøm og pakker UKENDTE event-navne som
      // `system_event` med `kind = event_name`. Etiketten kom derfor aldrig
      // frem til `case 'tool_round_label'` ovenfor — målt i produktion 14/9 på
      // en telefon der HAVDE den nye klient. Samme v1/v2-asymmetri som gjorde
      // at `retry` virkede i desk og ikke på mobilen.
      if (event.kind === 'tool_round_label') {
        const p = (event.payload ?? {}) as { etiket?: string; tool_use_ids?: string[]; tanke_resume?: string }
        return medEtiket(state, p.etiket, p.tool_use_ids, p.tanke_resume)
      }
      if (event.kind === 'skill_surface') {
        return medSkillFlade(state, (event.payload ?? {}) as { matches?: unknown; primary?: unknown })
      }
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
      if (event.kind === 'tool_result') {
        // SERVERENS EGEN FALDBACK, som klienten aldrig læste.
        //
        // `visible_runs_sse_v2` sender udfaldet TO gange: som denne
        // system_event (altid) og som en tool_result-content-blok (bag flaget
        // `structured_content_v2`). Kommentaren i serveren siger det lige ud —
        // «system_event bærer stadig udfaldet (aldrig break stream)» — men
        // reduceren foldede kun content-blokken. Var flaget slukket, eller kom
        // blokken ikke, stod rækken og kørte for evigt.
        //
        // Foldningen er idempotent: kommer begge, sætter den anden det samme.
        const id = String(event.payload.tool_use_id ?? '')
        const navn = String(event.payload.tool ?? '')
        const fejl = String(event.payload.status ?? '').toLowerCase()
        const blokke = state.blocks.slice()
        let rørt = false
        for (let i = 0; i < blokke.length; i++) {
          const b = blokke[i]
          if (!b || b.type !== 'tool_use') continue
          // Den RIGTIGE blok kendes på id'et. En FORELØBIG har intet id fra
          // serveren og kendes derfor på navnet — den skal væk uanset, ellers
          // bliver den stående og kører mens resultatet allerede er kommet.
          const rammer = b.id === id || (b.foreloebig && b.name === navn)
          if (!rammer) continue
          if (b.foreloebig) { delete blokke[i]; rørt = true; continue }
          blokke[i] = {
            ...b,
            status: fejl === 'error' || fejl === 'failed' || fejl === 'denied' ? 'error' : 'done',
            result: typeof event.payload.result === 'string' ? event.payload.result : b.result,
          }
          rørt = true
        }
        return rørt ? { ...state, blocks: blokke } : state
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
        if (navn === 'thinking' && !erVaerktoej) {
          // BEHOLD den sidste ægte linje — ryd den ikke.
          //
          // Før nulstillede vi her, og det fik arbejdslinjen til at BLINKE:
          // serveren sender et livstegn mellem hvert værktøjskald («Tænker
          // videre · runde N», visible_runs.py:2866, plus «Thinking via …»
          // ved start og ved grounding). Hvert af dem tømte `workingStep`,
          // så linjen forsvandt og kom igen for hver runde.
          //
          // Bjørn 30/9-2026: «Den vises og forsvinder random under streamen.
          // Meningen er den skal vises hele tiden under streamen og væk når
          // streamen ender.» Det var ikke random — det var hvert mellemrum.
          //
          // Den forrige turs linje hænger ikke ved af sig selv: `message_start`
          // nulstiller ved hver NY kørsel, og `working`-flaget slukker linjen
          // når streamen ender. Derfor er det nok at lade den stå her.
          return state
        }
        if (!navn || status !== 'running' || !erVaerktoej) {
          return { ...state, workingStep: detail, workingAction: navn || null }
        }
        const skridt = Number(event.payload.step ?? 0)
        // Allerede annonceret → lav den ikke igen. To slags «allerede»:
        //
        //  1. En foreløbig blok for SAMME skridt (genoptag efter reconnect).
        //  2. Serverens EGEN blok for samme værktøj, som stadig kører.
        //
        // (2) er driftens normaltilfælde og manglede: `_emit_tool_use_start`
        // lægger `content_block_start` + argumenterne på køen og sender FØRST
        // DEREFTER `system_event(working_step)` med det samme kald. Den
        // foreløbige blok blev altså født EFTER den rigtige, havnede sidst i
        // arrayet — og `buildStreamingRows` beholder den SIDSTE venteflade.
        // Resultat, målt 28/9-2026 på telefonen: `analyze_image`-animationen
        // stod uden navn og uden billede, fordi den blok der vandt var den
        // tomme. Den rigtige, med `image_path`, blev smidt væk.
        const alleredeAnnonceret = state.blocks.some((b) => b && b.type === 'tool_use'
          && (b.foreloebig
            ? b.foreloebig.skridt === skridt
            : b.name === navn && b.status === 'running'))
        if (alleredeAnnonceret) {
          return { ...state, workingStep: detail, workingAction: navn || null }
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
        return { ...state, workingStep: detail, workingAction: navn || null, blocks: medPlads }
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
      if (state.provisionalMissingBlockIndex != null && state.provisionalText) {
        uden[state.provisionalMissingBlockIndex] = { type: 'text', text: state.provisionalText }
      }
      for (let i = 0; i < uden.length; i++) {
        const b = uden[i]
        if (b && b.type === 'tool_use' && b.foreloebig) delete uden[i]
      }
      return { ...state, status: 'done', blocks: uden, provisionalText: '', provisionalBlockIndex: null, provisionalMissingBlockIndex: null }
    }

    case 'tool_round_label':
      // Den DIREKTE form (SSE-v1). Den indpakkede kommer som `system_event`
      // nedenfor — se `medEtiket`.
      return medEtiket(state, event.etiket, event.tool_use_ids, event.tanke_resume)

    case 'round_restart_discard_partial':
      // §4.1 CLIENT CONTRACT: en runde fejlede mid-stream og re-køres. Drop den
      // ikke-finaliserede on-screen partial (blocks) for dette run, så den
      // friske re-run-stream ikke render'es OVENPÅ den fejlede partial (dublet).
      // Advisory: serverens persisterede svar er allerede trunkeret, så selv en
      // klient der ignorerede dette ville forblive korrekt i historikken — kun
      // den live visning ville kortvarigt vise dubleret tekst. `retry`-eventet
      // (ren "Reconnecting n/m"-signalering) falder gennem default = no-op,
      // præcis som desk's reducer.
      return { ...state, status: 'working', blocks: [], provisionalText: '', provisionalBlockIndex: null, provisionalMissingBlockIndex: null }

    default:
      // Den DIREKTE form af `skill_surface` (SSE-v1) står ikke i typen; den
      // indpakkede kommer som `system_event` ovenfor.
      if ((event as { type?: string }).type === 'skill_surface') {
        return medSkillFlade(state, event as unknown as { matches?: unknown; primary?: unknown })
      }
      return state
  }
}
