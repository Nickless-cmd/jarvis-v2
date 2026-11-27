import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { ApiConfig } from '../../lib/api'
import { deriveChatFlow } from '../../lib/chatFlowModel'
import type { ContentBlock } from '../../lib/sseProtocol'
import type { StreamStatus } from '../../lib/streamReducer'
import { useChatPacedBlocks } from '../../lib/useChatPacedBlocks'
import { useFoldHukommelse } from '../../lib/foldHukommelse'
import { useTurSekunder } from '../../lib/turTid'
import { usePacingWorkLine } from '../../lib/usePacingWorkLine'
import '../../styles/chat-flow.css'
import { Arbejdsforloeb } from './RaekkeTranskript'
import { CODE_FOLD_MS, codeVisibleBlocks, codeAnswerStarted } from '../../lib/codeTurnPresentation'
import { BlocksRenderer } from './BlocksRenderer'
import { JarvisRing } from '../shell/JarvisRing'
import { SynteseLinje } from './LabelSkift'
import { TitelCrossfade, TurHoved } from './TurHoved'
import { FladeKontrolContext } from './NativeRichBlock'
import { FladeDeferredTurnContext } from '../../lib/fladeDeferredTurn'
import { udførDeferredTool } from '../../lib/fladeHandling'
import { RullendeTokens } from '../feedback/RullendeTal'

export interface ChatFlowPresentationProps {
  blocks: ContentBlock[]
  mode: 'living' | 'calm'
  density: 'compact' | 'full'
  streaming: boolean
  status: StreamStatus
  finalAnswerStarted: boolean
  /**
   * Der er kommet arbejde EFTER svar-låsen (et nyt run i samme tur). Hovedet
   * skal folde ud igen, så rundens tekst er synlig mens den kører — uden at
   * det låste svar rives op. Se `StreamState.arbejdeEfterSvar`.
   */
  arbejdeEfterSvar?: boolean
  runId?: string | null
  /** Turens starttid (ms epoch) — uret måler turen, ikke komponentens montering. */
  turStart?: number | null
  /**
   * TURENS LOGISKE IDENTITET — pacing-nøglen.
   *
   * Adskilt fra `turStart` 26/11-2026. `turStart` er TID og kan sættes på ny
   * af en frame der hører til samme tur; `turId` er IDENTITET og kan ikke.
   * Så længe nøglen var `tur-${turStart}`, nulstillede enhver sådan frame
   * pacens cursor — og folden kunne derfor aldrig blive irrelevant for pacen.
   *
   * `null` = persisteret tur uden stream-tilstand; så bruges `runId` som før.
   */
  turId?: string | null
  /** Turens sluttid (ms epoch) — uret fryser her og bliver stående efter turen. */
  turSlut?: number | null
  /** Turens varighed udledt af transskriptet. Bruges på persisterede ture, hvor
   *  stream-tilstanden (og dermed `turStart`/`turSlut`) ikke findes længere. */
  varighedSekunder?: number | null
  /** Levende output-token-estimat; erstattes af providerens slutmåling. */
  tokens?: number
  workingStep?: string | null
  rundeEtiketter?: Record<string, string>
  tankeResumeer?: Record<string, string>
  beskedId?: string
  sessionId?: string | null
  config?: ApiConfig
  onWorkExpanded?: () => void
  /** Hold slutsvarets visuelle pacing i live efter message_stop, indtil den
   *  persisterede besked kan overtage uden et dump. */
  paceFinalAnswer?: boolean
  /** Eksplicit nødudgang: vis hele den modtagne tekst NU og forbigå paceren.
   *  Bruges IKKE ved `done` — serverens stream-slut, pacerens slut og den
   *  sidste ordanimations slut er tre forskellige hændelser, og `done` alene
   *  må ikke give et visuelt dump (side-f9ab36ac9d). Rækken holdes live af
   *  `paceFinalAnswer` til `onAnswerPaced`. Kun til situationer hvor
   *  øjeblikkelig visning er påkrævet (fx afbrudt tur der skal vise alt). */
  flushFinalAnswer?: boolean
  onAnswerPaced?: () => void
}

/**
 * Render one logical answer as one Markdown document.
 *
 * The stream protocol may split a single word across text blocks when an
 * autonomous/follow run crosses a round boundary (for example `L` +
 * `ukket`). The pacing layer already treats all answer text as one continuous
 * target. Keeping the transport blocks separate here would nevertheless make
 * BlocksRenderer create one Markdown paragraph per block, inserting a visual
 * line break that was never present in the text.
 *
 * This is deliberately presentation-only: the original blocks still drive
 * pacing, phases and work/final classification unchanged.
 */
function samletSvarMarkdown(blocks: ContentBlock[]): ContentBlock[] {
  const samlet: ContentBlock[] = []
  for (const block of blocks) {
    const previous = samlet.at(-1)
    if (block.type === 'text' && previous?.type === 'text') {
      samlet[samlet.length - 1] = { ...previous, text: previous.text + block.text }
    } else {
      samlet.push(block)
    }
  }
  return samlet
}

export function ChatFlowPresentation({
  blocks,
  mode,
  density,
  streaming,
  status,
  finalAnswerStarted,
  arbejdeEfterSvar = false,
  runId,
  turStart,
  turId,
  turSlut,
  varighedSekunder,
  tokens = 0,
  workingStep,
  rundeEtiketter,
  tankeResumeer,
  beskedId,
  sessionId,
  config,
  onWorkExpanded,
  paceFinalAnswer = false,
  flushFinalAnswer = false,
  onAnswerPaced,
}: ChatFlowPresentationProps) {
  const deferredTurn = useMemo(() => (
    config && sessionId && beskedId
      ? {
          accountId: '', conversationId: sessionId, sourceMessageId: beskedId,
          run: (request: Parameters<typeof udførDeferredTool>[1]) => udførDeferredTool(config, request),
        }
      : null
  ), [config, sessionId, beskedId])
  // Pace fra FØRSTE levende teksttegn, ikke først efter final_answer_start.
  // No-tool-svar får ingen sådan grænse fra relæet og kunne derfor arve
  // providerens store bidder, mens autonome follow-runs så fine ud. Samme
  // cursor følger nu teksten gennem syntese → slutsvar → message_stop.
  const pacingFinal = finalAnswerStarted || (paceFinalAnswer && status === 'done')
  const paced = useChatPacedBlocks(blocks, {
    live: streaming || paceFinalAnswer,
    finalAnswerStarted: pacingFinal,
    paceAllText: streaming,
    flush: flushFinalAnswer,
    // Nøglen er TURENS IDENTITET, ikke runnet og ikke tidsstemplet
    // (28/10-2026, skærpet 26/11-2026). Cursoren ligger under
    // `${nøgle}:chat-text`; gav et follow-up-run en ny nøgle, faldt cursoren
    // til `''` og svaret blev pacet FORFRA — det Bjørn beskrev som «tom skærm,
    // og så starter slut besked med at pace uden for hoved».
    //
    // Før var nøglen `tur-${turStart}`. Det holdt så længe `turStart` var
    // uforanderlig, men den er TID og blev sat på ny af `follow_start`,
    // `client_turn_start`, en `origin`-frame og en run-frame med nyt id. Hver
    // af dem nulstillede pacen midt i turen. `turId` sættes én gang pr. tur
    // og bevares af alle de frames — så pacen fortsætter uanset hvad der sker
    // med hovedet, runderne eller tidsstemplet.
    //
    // Persisterede ture har ingen stream-tilstand og dermed intet `turId`;
    // der falder vi tilbage på `runId`, som er stabilt for en gemt besked.
    runId: turId ?? (turStart != null ? `tur-${turStart}` : runId),
  })
  const explicitProtocol = blocks.some((b) => b?.type === 'text' && b.code_answer_protocol === 1)
  const pacedBlocks = explicitProtocol ? codeVisibleBlocks(blocks, paced) : paced
  const targetSvar = blocks.flatMap((block) => block && block.type === 'text' ? [block.text] : []).join('')
  const vistSvar = pacedBlocks.flatMap((block) => block && block.type === 'text' ? [block.text] : []).join('')
  const svarFaerdigPacet = targetSvar.length > 0 && targetSvar === vistSvar
  const shownAnswerStarted = explicitProtocol ? codeAnswerStarted(pacedBlocks) : finalAnswerStarted
  const model = deriveChatFlow({
    blocks: pacedBlocks,
    workingStep,
    rundeEtiketter,
    tankeResumeer,
    finalAnswerStarted: shownAnswerStarted,
    status,
    arbejdeEfterSvar,
  })
  const targetModel = deriveChatFlow({
    blocks,
    workingStep,
    rundeEtiketter,
    tankeResumeer,
    finalAnswerStarted,
    status,
    arbejdeEfterSvar,
  })
  const confirmedRef = useRef<{ runKey: string; texts: string[] }>({ runKey: '', texts: [] })
  // Nøglen er TUREN, ikke runnet (26/11-2026). `runId` skifter ved hvert
  // follow-up-run, så de bekræftede tekster blev nulstillet midt i turen — og
  // så forsvandt en syntese der allerede stod på skærmen. `turId` er stabil
  // gennem alle rundens frames; persisterede ture falder tilbage på `runId`.
  const runKey = turId ?? runId ?? '__historical-message__'
  const priorConfirmed = confirmedRef.current.runKey === runKey ? confirmedRef.current.texts : []
  let confirmedTexts = priorConfirmed
  if (finalAnswerStarted) {
    confirmedTexts = [...priorConfirmed]
    for (const block of targetModel.finalBlocks) {
      if (block.type !== 'text' || !block.text) continue
      const related = confirmedTexts.findIndex((text) => text.startsWith(block.text) || block.text.startsWith(text))
      if (related < 0) confirmedTexts.push(block.text)
      else if (block.text.length > confirmedTexts[related]!.length) confirmedTexts[related] = block.text
    }
    confirmedRef.current = { runKey, texts: confirmedTexts }
  } else if (confirmedRef.current.runKey !== runKey) {
    confirmedRef.current = { runKey, texts: [] }
  }
  // «Runder» er værktøjskald og arbejdsrapporter — ikke tekst.
  //
  // Bjørn 14/11-2026: «hvis ingen runder er kørt i turen bør turhoved forsvinde
  // når beskeden starter, men det kræver vi tager højde for at en syntese ikk er
  // det samme som slut beskeden. og hvis der kaldes runder bør hoved forblive
  // synligt.»
  //
  // `hasObservableWork` kan ikke bruges til den sondring: den er OGSÅ sand når
  // der kun ligger synteser (`allSynthesis.length > 0`), så et rent syntese-svar
  // holdt hovedet i live gennem hele turen — også efter beskeden var begyndt.
  // Syntesen er en mellemtekst under arbejdet, ikke et værktøjskald, og den må
  // hverken tælle som runde eller forveksles med slutsvaret.
  //
  // `thinking` er udelukket af samme grund (Bjørn 14/11-2026: «hvis den første
  // blok er en tanke blok og så beskeden … ellers bliver det stående fordi du
  // tænker før du skriver i chat mode»). I chat mode tænker jeg FØR jeg skriver,
  // så næsten hver tur ville ellers bære en «runde» og holde hovedet stående
  // gennem hele beskeden — uden at et eneste værktøj var kaldt. Tænkeblokken er
  // min monolog, ikke arbejde: den kan foldes ud, men den er ikke en runde.
  const harRunder = model.workBlocks.some(
    (blok) => blok.type !== 'text' && blok.type !== 'thinking',
  )
  // Uden runder er der ingen fold at gemme syntesen i.
  //
  // MÅLT 14/11/2026 i Chromium: da hovedet blev fjernet, forsvandt syntesen
  // «Lad mig se på det.» HELT fra DOM'en — den lå kun i gruppen under hovedet,
  // og gruppen forsvinder sammen med det. Uden runder er syntesen ikke en
  // arbejdsdetalje; den er en del af svaret og hører i svar-lanen, foran det.
  //
  // MEN kun når den levende visning er forbi: mens turen kører og slutsvaret
  // ikke er begyndt, står syntesen i gruppen som `chat-flow-live-synthesis`.
  // Flyttede jeg den samtidig, ville den stå to steder.
  //
  // Tænkeblokken følger IKKE med (rettet 14/11-2026, Bjørn: «hvorfor viser den
  // tænke blokken?»). Første udgave flyttede den til svar-lanen sammen med
  // syntesen, fordi den forsvandt fra DOM'en da hovedet blev fjernet. Det var
  // forkert: tænkeblokken er min monolog, ikke en del af svaret. Uden runder er
  // der ingen fold at lægge den i, og så skal den ikke vises — ikke flyttes ind
  // i beskeden. Kun syntesen er mellemtekst der hører til brugeren.
  const syntesenVisesLevende = streaming && !finalAnswerStarted
  const udenArbejde = (harRunder || syntesenVisesLevende)
    ? []
    : model.workBlocks.filter((block) =>
        block.type === 'text' && block.text.trim().length > 0)
  // Flyttede blokke må ikke også stå i arbejdsvisningen — samme regel som
  // `retainedWork` bruger for de bekræftede tekster: ét sted, aldrig to.
  const flyttedeTekster = new Set(
    udenArbejde.flatMap((block) => (block.type === 'text' ? [block.text] : [])),
  )
  const erFlyttetTilSvar = (block: ContentBlock): boolean =>
    block.type === 'text' && flyttedeTekster.has(block.text)
  const retainedWork = (finalAnswerStarted && confirmedTexts.length > 0
    ? model.workBlocks.filter((block) => block.type !== 'text'
        || !confirmedTexts.some((text) => text === block.text || text.startsWith(block.text) || block.text.startsWith(text)))
    : model.workBlocks).filter((block) => !erFlyttetTilSvar(block))
  // Et blokerende spørgsmål er ikke en arbejdsdetalje der må gemmes bag
  // turhovedets fold. Det er en samtalebesked med et svarfelt og skal stå
  // inline, synligt og tastaturtilgængeligt mens resten af arbejdet fortsat
  // kan være kompakt.
  const inlineQuestions = retainedWork.filter((block) =>
    block.type === 'tool_use' && block.name === 'pause_and_ask')
  // ── RUNDER EFTER BESVARELSEN — EGEN CONTAINER, EGEN LIVSCYKLUS ─────────
  //
  // Bjørn 27/11-2026: «Turhovedet, besvarelsen og runderne uden for hovedet
  // skal have hver deres uafhængige visuelle livscyklus i én stabil
  // dokumentstruktur.»
  //
  // Før var dette en BINÆR gren: så snart ét runde-segment lå efter
  // besvarelsen, skiftede hele besvarelsens indre struktur fra
  // `BlocksRenderer`s rod til `.chat-flow-segmenter`. Besvarelsen blev dermed
  // remountet — og det er det blink brugeren ser. Animationerne dækkede over
  // det i stedet for at fjerne det.
  //
  // Nu bærer `plassering` (fra `chatFlowModel`) hele sondringen, og der er
  // ingen gren: besvarelsen er ALTID `BlocksRenderer` i `.chat-flow-answer`,
  // og hale-runderne er ALTID deres egne containere under den. En runde der
  // ankommer efter svaret tilføjes under besvarelsen — den flytter intet.
  //
  // `HALEBLOKKE_UDEN_RUNDE` bevares: `progress` samles sidst i `content_json`
  // ved persistens, og en umatchet `approval` lægges sidst af `indsaetVedKald`.
  // Ingen af dem er en ny runde, så et segment der KUN består af dem må ikke
  // blive en synlig container.
  const HALEBLOKKE_UDEN_RUNDE = new Set<ContentBlock['type']>(['progress', 'approval'])
  const efterSegmenter = model.segmenter.filter((segment) =>
    segment.slags === 'runde'
    && segment.plassering === 'efter'
    && segment.blokke.some((block) => !HALEBLOKKE_UDEN_RUNDE.has(block.type)))
  // Blokkene ejes nu af hale-containeren. Folden må ikke også vise dem —
  // dobbelt ejerskab er præcis det KONTRAKT 1b værner mod. Referencerne er
  // identiske (`segmenter` og `workBlocks` bygges fra samme liste), så et
  // sæt på objektidentitet rammer præcist.
  const efterBlokke = new Set<ContentBlock>(
    efterSegmenter.flatMap((segment) => segment.blokke))
  const foldWork = retainedWork.filter((block) =>
    (block.type !== 'tool_use' || block.name !== 'pause_and_ask')
    && ((!streaming && !arbejdeEfterSvar && svarFaerdigPacet)
      || !efterBlokke.has(block)))
  // Bjørn 20/10-2026: «det hurtige svar skal aldrig vises».
  //
  // `confirmedTexts` er den RÅ tekst fra serveren. Da den blev lagt foran
  // `model.finalBlocks`, stod hele svaret på skærmen i samme frame som turen
  // vendte tilbage til værktøjsarbejde — mens pacen stadig var på de første
  // tegn. Målt: 102 tegn vist mod 2 pacede.
  //
  // De bekræftede tekster findes OGSÅ i `model.workBlocks`, som er PACET.
  // Vi henter dem der i stedet: samme tekster, samme ur, og ingen upacet vej
  // ind i svar-lanen. `retainedWork` filtrerer præcis de samme blokke ud af
  // arbejdsvisningen, så teksten vises ét sted — aldrig to.
  const restoredText = finalAnswerStarted
    ? model.workBlocks.filter((block): block is Extract<ContentBlock, { type: 'text' }> =>
        block.type === 'text'
        && block.text.length > 0
        && confirmedTexts.some((text) => text === block.text
          || text.startsWith(block.text)
          || block.text.startsWith(text)))
    : []
  const answerBlocks = [...udenArbejde, ...restoredText, ...model.finalBlocks]
  const answer = samletSvarMarkdown(answerBlocks)

  // Bjørn 29/10-2026: «det bør kun tilføjes naturligt i enden af pacen altså
  // ikk før pacen er slut med en levende forlængning? fade eller sådan noget?»
  //
  // Widgetten er en leverance og hører i bunden (se `leveranceIBunden`), men
  // den skal ikke dukke op MIDT i pacen: den ankommer først når svaret er
  // rullet færdigt. Imens står en PLACEHOLDER med reserveret højde, så det er
  // widgetten der fader ind — ikke layoutet der hopper.
  //
  // `paceFinalAnswer` er gaten: en persisteret besked (uden pace) viser
  // widgetten med det samme, og en tur der ikke paces røres ikke.
  const venterPaaPace = paceFinalAnswer && !svarFaerdigPacet
  const erLeverance = (block: ContentBlock): boolean => block.type === 'file'
    && String(block.mime_type || '').toLowerCase().startsWith('text/html')
    && String(block.kilde || '') === 'generated'
    && !!String(block.attachment_id || '').trim()
  // Leverancen holdes ALTID ude af svar-lanen — ikke kun mens pacen ruller.
  //
  // Målt 29/10-2026 (Bjørn: «widget bliver vist 2 gange nu? men i bunden af
  // beskeden?»): filtreringen var gated på `venterPaaPace`, så i det øjeblik
  // pacen sluttede blev `synligeSvar === answer`, og widgetten stod BÅDE i
  // `.chat-flow-answer` og i leverance-blokken nedenfor. To instanser, begge
  // i bunden. Repro: 4 forekomster af filnavnet i hver. Leverance-blokken er
  // den eneste ejer, så svar-lanen må aldrig bære den.
  const synligeSvar = answer.filter((block) => !erLeverance(block))
  const ventendeLeverancer = venterPaaPace ? answer.filter(erLeverance) : []
  const onAnswerPacedRef = useRef(onAnswerPaced)
  onAnswerPacedRef.current = onAnswerPaced
  useEffect(() => {
    if (!paceFinalAnswer || !svarFaerdigPacet || streaming || arbejdeEfterSvar) return
    if (!efterSegmenter.length) { onAnswerPacedRef.current?.(); return }
    const timer = window.setTimeout(() => onAnswerPacedRef.current?.(), CODE_FOLD_MS + 50)
    return () => window.clearTimeout(timer)
  }, [paceFinalAnswer, svarFaerdigPacet, streaming, arbejdeEfterSvar, efterSegmenter.length])
  // «Aktiv» er arbejdsfasen: Jarvis kører og har ikke begyndt at svare endnu.
  // Uden for den er turen enten afsluttet eller svaret er begyndt — og så
  // klapper hovedet sammen og arbejdet lægger sig som detaljer.
  // «Aktiv» betyder «turen kører og rundelinjen er dens ansigt». Den må ikke
  // kræve `!finalAnswerStarted`: med «gem turhoved til det foldes» (14/11-2026)
  // findes hovedet ikke før turen er slut, så rundelinjen skal blive stående
  // gennem slutsvaret. Målt: uden denne gren faldt `arbejdeAabent` tilbage på
  // `aaben` = true, og arbejdsdetaljerne overtog pladsen mens turen kørte.
  const aktiv = streaming || arbejdeEfterSvar
  // KUN rundelinjen fader — synteselinjen bliver stående. Første udgave satte
  // attributten på den fælles wrapper `chat-flow-activity`, så både syntese og
  // runde forsvandt i samme fade og skærmen blev tom (Bjørn 22/10-2026: «det
  // var kun runde linjen.. ikk syntese linjen»). Rundelinjen bliver i DOM'en
  // mens pacen ruller, så Jarvis-markørens animation og layoutet ikke hopper,
  // og fader ind igen når pacen er forbi. Korte synteser når ikke tærsklen
  // (420 ms) og blinker derfor aldrig.
  const skjulAktivRunde = usePacingWorkLine(
    aktiv && targetSvar.length > 0 && !svarFaerdigPacet,
    runId ?? beskedId ?? null,
  )
  const activeLine = mode === 'calm'
    ? model.calmStatus
    : model.visibleSynthesis.at(-1)
  // Den levende syntese er den seneste tekstblok i arbejdet — men kun hvis
  // den HAR indhold. En ny tekstblok starter tom, og det tidligere
  // `…?.text.trim() || null` rev linjen ned i netop det øjeblik: den gamle
  // forsvandt, der blev et glip, og den næste kom streamende bagefter
  // (Bjørn 17/10-2026). Vi springer tomme blokke over, så den forrige tekst
  // står stille indtil den nye har noget at vise.
  //
  // `noegle` er blokkens indeks i arbejdet. Det skifter KUN når syntesen
  // erstattes — ikke mens teksten vokser — så visningen kan opdatere på
  // stedet i stedet for at krydsfade ved hvert tegn.
  const levendeSyntese = (() => {
    if (mode !== 'living') return null
    for (let i = model.workBlocks.length - 1; i >= 0; i--) {
      const blok = model.workBlocks[i]
      if (blok && blok.type === 'text' && blok.text.trim()) {
        return { tekst: blok.text.trim(), noegle: i }
      }
    }
    // Femte gate, målt 22/10-2026: `model.workBlocks` er PACET. Når slutsvaret
    // begynder, er de pacede arbejdsblokke tømt — så synteselinjen forsvandt
    // mens rundelinjen blev. Syntesen skal blive stående gennem
    // pacing-vinduet, så vi falder tilbage til de RÅ blokke. Kun teksten
    // bruges til visning; paceren rører ikke denne vej.
    //
    // KUN når slutsvaret er begyndt (side-f9ab36ac9d, fejl 2). Før da er de
    // pacede arbejdsblokke ikke «tømt» — cursoren står bare på nul, fordi
    // paceren endnu ikke har sat første tegn. Faldt vi dér tilbage til de rå
    // blokke, blev HELE den modtagne tekst tegnet i folden i første frame
    // (målt: 290 tegn) og faldt så til 2 i næste: et dump i folden efterfulgt
    // af en nulstilling. Rå tekst må aldrig komme uden om paceren.
    if (explicitProtocol || !finalAnswerStarted) return null
    for (let i = targetModel.workBlocks.length - 1; i >= 0; i--) {
      const blok = targetModel.workBlocks[i]
      if (blok && blok.type === 'text' && blok.text.trim()) {
        return { tekst: blok.text.trim(), noegle: i }
      }
    }
    return null
  })()
  const activeSynthesis = levendeSyntese?.tekst ?? null
  // Hovedet skal stå fra FØRSTE ord — også i det vindue hvor turen lige er
  // startet og der endnu ikke er rapporteret arbejde eller synteser.
  // (Bjørn 17/10-2026: «lige som i code mode skal turhoved vises hele tiden
  // før de første ord».) Uden `streaming` her manglede hovedet netop i det
  // øjeblik turen begyndte, og dukkede først op bagefter.
  // Uret tælles op fra `turStart` og måles til `turSlut` (sat ved
  // `message_stop`) — ikke til `aktiv`, som bliver falsk allerede når svaret
  // begynder. Det giver det rigtige tal gennem hele turen.
  //
  // VENDT 14/11-2026 (Bjørn): «sekunder Xs i turhoved skal forsvinde når
  // turen er slut. og vises mens turen køre». Den tidligere regel var det
  // modsatte — uret blev frosset og STOD i hovedet bagefter (17/10-2026:
  // «ueret skal osse når strømmen er forbi»), og persisterede ture viste
  // deres udledte varighed for evigt. Et tal der står stille på en færdig
  // tur beskriver noget der allerede er sket; det hører i en log, ikke i et
  // hoved der skal fortælle hvad der sker NU.
  //
  // Beregningen bliver stående uanset `streaming`: den bærer stadig
  // `varighedSekunder` for persisterede ture, og `visTurhoved` nedenfor læser
  // den. Det er kun VISNINGEN der gates.
  const sekunder = useTurSekunder(turStart, turSlut) ?? varighedSekunder ?? null
  // Hovedet er turens skillestreg — ikke en overskrift for værktøjskald.
  // (Bjørn 17/10-2026: «tur hoved vises ikke hvis han ikk kalder tools… det
  // skal være der osse uden tool kald».) Derfor bæres det af tre ting: der er
  // arbejde at folde, turen kører, eller vi kender dens varighed.
  const harArbejde = model.hasObservableWork
  // Hovedet bliver stående gennem HELE turen — også mens slutsvaret rulles ud
  // efter `message_stop`.
  //
  // 29/10-2026 fjernede jeg det i pace-vinduet (`pacerSvar`), fordi Bjørn
  // beskrev at «pacen kører først inde i hoved». Det var den forkerte læsning
  // af symptomet: teksten lå dengang i ARBEJDSVISNINGEN under hovedet, fordi
  // de bekræftede tekster blev hentet fra de RÅ blokke. Den vej er lukket
  // siden — `restoredText` henter dem fra de PACEDE arbejdsblokke og lægger
  // dem i svar-lanen, og `retainedWork` filtrerer præcis de samme blokke ud af
  // arbejdet. Så pacen ruller allerede UDEN FOR hovedet.
  //
  // Målt 30/10-2026 (Bjørn: «nu forsvinder turhoved og skill linjen indtil
  // svaret er færdig»): gaten fjernede ikke et problem, den fjernede turens
  // skillestreg midt i turen. `.rv-tur` var væk fra DOM'en gennem hele
  // pace-vinduet og dukkede først op da svaret var færdigt. Hovedet er turens
  // vandrette streg — det er dét der fortæller at turen er én tur — så det må
  // ikke forsvinde mens turen stadig løber.
  //
  // Foldet er lukket under pacen (`arbejdeKoerer` er falsk når `streaming` er
  // falsk), så hovedet står som en stille streg over et svar der skriver sig.
  //
  // MED runder: uændret — hovedet bliver stående gennem hele turen, også mens
  // slutsvaret rulles ud, fordi der ER arbejde at folde ud og en varighed at vise.
  //
  // UDEN runder: kun mens turen kører og slutsvaret ikke er begyndt. `streaming`
  // er nødvendig i den gren — `finalAnswerStarted` er `false` som default for
  // persisterede ture, så uden den ville historikkens direkte svar få et hoved
  // de aldrig havde.
  // OVERLEVERINGEN (Bjørn 14/11-2026): «turhoved skjules, og kun den aktive
  // rundelinje vises indtil den skifter position til under den første syntese
  // eller besked, og så når rundelinjen forsvinder morpher turhoved — som har
  // kørt hele tiden — ind».
  //
  // Uden runder er hovedet under streamen en død etiket: der er intet at
  // folde ud, og det eneste den bærer — uret — står også i rundelinjen. Så
  // rundelinjen er turens ansigt indtil svaret begynder; derefter tager
  // hovedet over med den varighed der blev optjent undervejs. Fordi uret har
  // talt hele tiden, er der intet der starter op ved skiftet — det er dét der
  // gør overgangen uden hop.
  //
  // VENDT 14/11-2026, anden gang samme dag: formiddagens regel var at hovedet
  // helt FORSVANDT når svaret begyndte. Den var rigtig så længe der ikke var
  // noget at overlevere TIL, men med rundelinjen som turens ansigt er der en
  // naturlig arvtager — og et «Tænkte 8s» der først dukker op ved svarets
  // start fortæller hvad turen kostede, ikke hvad der sker nu. Det er derfor
  // det kun er den LEVENDE tur der morpher ind; en persisteret tur uden
  // runder viser stadig intet hoved, for dér ville tallet stå stille på noget
  // der allerede er sket.
  // VENDT 14/11-2026, tredje gang samme dag (Bjørn): «skal vi gemme turhoved
  // til det foldes? og lade den aktive rundelinje trække det levende indtil
  // hoved foldes?»
  //
  // De to første regler var begge halve. Den første lod hovedet forsvinde når
  // svaret begyndte — så var der intet at overlevere til. Den anden lod det
  // morphe ind ved `finalAnswerStarted` — men dér er turen ikke slut, og
  // hovedet stod dermed som en etiket over et svar der stadig skrev sig, mens
  // rundelinjen under det sagde nogenlunde det samme.
  //
  // Den tredje regel er den ene: hovedet er et RESULTAT, ikke en status. Det
  // findes først når turen er slut — når folden lukker (`arbejdeKoerer` falsk).
  // Indtil da er rundelinjen turens ansigt, og den bærer uret, så intet tal
  // går tabt ved skiftet. Fire grene bliver til én.
  // ÉN regel (Bjørn 14/11-2026): «lad turhoved være som det er, gør det usynlig
  // til hoved folder og slut beskeden sker». Hovedet er turens RESULTAT, ikke
  // en status — det findes først når turen er slut. Persisteret historik uden
  // runder får intet hoved: dér ville tallet stå stille på noget der allerede
  // er sket.
  // «Turen lever» og «hvad laver hovedet» er TO spørgsmål, og de må ikke
  // besvares af samme boolean. Hovedet står gennem hele turen — også mens
  // svaret skrives, hvor tilstanden er `formidlet` og ikke `aktiv`. Blandede
  // man dem, forsvandt hovedet i det vindue (målt 18/11-2026).
  const turenKoerer = streaming || arbejdeEfterSvar || (paceFinalAnswer && !svarFaerdigPacet)

  // LIVSCYKLUSSEN: live → kollapset → unmount (Bjørn 27/11-2026).
  //
  // «Containeren skal først afmonteres efter den afsluttede transition, uden et
  // efterfølgende layout-hop.»
  //
  // `kollapset` er ikke en slutning, men et OVERGANGSTRIN: rækken går til 0fr
  // og gap'et neutraliseres over `--fold-varighed` (300ms). Først når det ur er
  // gået, må noden fjernes — på det tidspunkt optager den nul plads, så
  // fjernelsen ændrer ikke layoutet. Sætter man `display: none` mens
  // transitionen kører, er der intet at animere, og så hopper det.
  //
  // Uret armes når turen bliver terminal, og RYDDES hvis den genoptages (et nyt
  // run i samme tur): ellers ville en container der lige var på vej ud blive
  // fjernet midt i en tur der stadig kører.
  // AFMONTERINGEN ER PER CONTAINER, IKKE PER KOMPONENT (GPT, 27/11-2026:
  // «Han bruger én fælles reference … Når dens transition afsluttes, sættes
  // den fælles `afmonteret`-tilstand, og alle rundecontainere fjernes.»)
  //
  // MÅLT 27/11-2026 i Chromium med to selvstændige runde-containere: begge
  // forsvandt efter 303 ms — SAMTIDIGT. Det er den fælles boolean. Det ser
  // rigtigt ud så længe alle transitions starter og slutter i takt, men det er
  // ikke en garanti: en container der kollapser senere (fx fordi dens indhold
  // er højere, eller fordi den blev tilføjet midt i forløbet) ville blive
  // fjernet før dens egen transition var færdig — og dét er præcis det
  // layout-hop kommentaren ovenfor forbyder.
  //
  // Tilstanden er derfor et SÆT af segment-id'er: hver container melder sig
  // selv færdig, når dens EGEN `transitionend` fyrer.
  const [afmonterede, setAfmonterede] = useState<ReadonlySet<string>>(() => new Set())
  const kollapsRefs = useRef(new Map<string, HTMLDivElement>())
  const markérAfmonteret = useCallback((id: string) => {
    setAfmonterede((forrige) => {
      if (forrige.has(id)) return forrige
      const naeste = new Set(forrige)
      naeste.add(id)
      return naeste
    })
  }, [])
  useEffect(() => {
    if (turenKoerer) {
      setAfmonterede((forrige) => (forrige.size === 0 ? forrige : new Set()))
      return
    }
    // AFMONTERINGEN FØLGER TRANSITIONEN, IKKE ET GÆT (GPT, 27/11-2026:
    // «Afmonteringens ur er hardcodet … CSS og JavaScript har stadig hver
    // deres ur.»)
    //
    // Før stod der `setTimeout(…, 300)` — et JS-tal der SPEJLEDE
    // `--dur-sheet`. To ure der beskriver den samme varighed divergerer den
    // dag nogen justerer tokenet, og fejlen ville være usynlig: noden ville
    // bare forsvinde midt i en transition der stadig kørte.
    //
    // Nu lyttes på den FAKTISKE `transitionend` fra HVER kollaps-wrapper. Den
    // fyrer når browseren er færdig — uanset varighed, kurve og om brugeren
    // har `prefers-reduced-motion` (hvor transitionen er slået af og
    // hændelsen derfor aldrig kommer; derfor fallback-uret).
    //
    // FALLBACK: en afbrudt transition (turen genoptages, eller elementet
    // fjernes fra DOM'en af en anden grund) fyrer ingen `transitionend`. Uden
    // et loft ville containeren blive stående for evigt. Loftet er derfor
    // kun et sikkerhedsnet, ikke uret — og det er PER container, så én der
    // hænger ikke trækker de andre med.
    const lyttere: Array<() => void> = []
    const lofter: Array<ReturnType<typeof setTimeout>> = []
    for (const [id, node] of kollapsRefs.current) {
      let færdig = false
      const afslut = () => {
        if (færdig) return
        færdig = true
        markérAfmonteret(id)
      }
      const påTransition = (e: TransitionEvent) => {
        // Kun wrapperens EGEN højde-transition — børnenes transitions bobler
        // op og må ikke afmontere containeren midt i noget andet.
        if (e.target === node && e.propertyName === 'grid-template-rows') afslut()
      }
      node.addEventListener('transitionend', påTransition)
      lyttere.push(() => node.removeEventListener('transitionend', påTransition))
      lofter.push(setTimeout(afslut, 1200))
    }
    return () => {
      lyttere.forEach((fjern) => fjern())
      lofter.forEach((loft) => clearTimeout(loft))
    }
  }, [turenKoerer, markérAfmonteret])
  // HOVEDET ER FIRE TILSTANDE, IKKE EN KOMPONENT MED EN FØDSEL OG EN DØD
  // (Bjørn 18/11-2026: «hvornår og hvorfor folder deres hoved? … det sker ofte
  // hovedets fold bliver til et blink»).
  //
  // MÅLT 18/11-2026 i ChatGPT-mobilens udpakkede `oai_reasoning`-modul
  // (`~/rea/reasoning/`, `ReasoningView.js`): deres hoved er ÉN komponent med
  // fire række-typer — `Summary`, `History`, `Active`, `Placeholder` — og
  // overgangen mellem dem er et `kind`-skift på en række der ALLEREDE står
  // der. Der findes ingen frame hvor turens ansigt er væk, fordi der ikke er
  // noget der monteres eller afmonteres. `Summary` er den foldede form af
  // præcis det samme indhold som `History` viser udfoldet.
  //
  // Vores regel var det modsatte: `!turenKoerer` betød at hovedet blev
  // AFMONTERET når turen sluttede, og gruppen åbnede igen ved hver ekstra
  // runde (`arbejdeEfterSvar`). Hver runde var en hel fold-cyklus — derfor
  // blinker det proportionalt med antallet af runder, ikke med tiden.
  //
  // Reglen er derfor vendt: hovedet STÅR gennem hele turen og skifter ord i
  // stedet for at skifte eksistens. Ordene findes allerede i `hovedTekst`
  // (`chatFlowModel.ts:101`) — «Tænker»/«Arbejder» mens den kører,
  // «Tænkte»/«Arbejdet» når den er færdig, «Afbrudt» og «Fejlede» som de to
  // terminale. Fire tilstande, ét element.
  //
  // Persisteret historik uden runder får stadig intet hoved: dér ville der
  // stå et resultat på en tur der ikke har noget at folde ud, og `harRunder`
  // er den ærlige grænse mellem «denne tur har et forløb» og «den har ikke».
  const visTurhoved = turenKoerer
    || harRunder
    || model.hovedTilstand === 'afbrudt'
    || model.hovedTilstand === 'fejlet'
  // Mens turen kører, er rundelinjen turens ansigt. Den ejer sin EGEN gate:
  // lå den inde i hovedets fragment, forsvandt den sammen med det hoved den
  // skulle overlevere til (målt 14/11-2026: `.rv-tur` var barn af samme gren,
  // og hele fragmentet var betinget af `visTurhoved`).
  const visArbejdsgruppe = turenKoerer || harRunder
  // Rundelinjen må aldrig vise et internt tool-navn. Modellen filtrerer de
  // rå working_step-værdier; indtil den menneskelige etiket er klar, står en
  // rolig fallback i samme stabile celle UNDER syntesen — ikke i turhovedet.
  //
  // Turhovedet ejer allerede den overordnede tilstand «Arbejder». Backendens
  // generiske working_step med samme ord er derfor ikke en ny oplysning i
  // rundelinjen. Mellem de konkrete forklaringer («Læser filen», «Tester …»)
  // viser den i stedet den aktuelle indre fase: «Tænker».
  const generiskArbejde = /^arbejder(?:\s*(?:…|\.\.\.))?$/i.test(activeLine?.trim() ?? '')
  // Placeholder-tilstanden (turen er startet, intet arbejde, intet svar endnu)
  // bærer INGEN rundetekst: turhovedet siger allerede «Tænker», og to ens ord
  // lige under hinanden er ikke en oplysning men støj. Tilstanden viser i
  // stedet kun tilstedeværelses-ringen — se gaten nedenfor.
  // OVERLEVERINGEN: mens hovedet venter, ER rundelinjen turens ansigt — så
  // den skal sige hvad hovedet ville have sagt. Uden denne gren stod der
  // kun en puls uden ord i det vindue hvor turen lige var startet, og den
  // tekst brugeren mistede var præcis den hovedet bærer (`model.hovedTekst`:
  // «Tænker» / «Arbejder»). Målt 14/11-2026: `getByText('Tænker')` fandtes
  // ikke længere i calm mode efter splittet.
  const rundeTekst = harArbejde
    ? (!activeLine || generiskArbejde ? 'Tænker' : activeLine)
    : turenKoerer
      ? model.hovedTekst
      : null

  // ÉN gate — samme form som code mode (`RaekkeTranskript.tsx:434/449/469`).
  //
  // Bjørn 22/10-2026, fjerde runde: «ja gør som i code mode.. det virker». Jeg
  // havde bygget fem gates (`visArbejdslinje`, `aaben`, `rammeAaben`,
  // `arbejdeAabent`, `levendeSyntese`) for at holde linjerne synlige gennem
  // pacing-vinduet — og hver rettelse flyttede fejlen til den næste, fordi
  // `rammeAaben` holdt rammen åben efter at hovedet havde foldet. Resultatet
  // var at foldet så ud som om det ventede på pacen.
  //
  // Code mode har ikke det problem, fordi der kun er ÉN gate: `aaben` følger
  // svarets start, og gruppen skjules i samme frame som hovedet folder. Chat
  // mode gør nu præcis det samme. Glidningen bliver stående i CSS'en, så
  // foldet glider frem for at blinke — men det sker ved svarets start, ikke
  // når pacen er færdig.
  // Folden huskes på beskedens identitet, ikke på komponentinstansen. Målt
  // 30/10-2026 (`foldRemount.maaling.test.tsx`): et remount nulstillede den —
  // og overgangen live → persisteret ER et remount, fordi den levende række
  // afmonteres når turen slutter. `runId` er den fælles nøgle: den levende
  // række har `activeRunId`, og den persisterede besked bærer samme id i
  // `run_id`. Uden nøgle opfører den sig som før (rent lokal state).
  const [aabenManuelt, setAabenManuelt] = useFoldHukommelse(runId ?? beskedId)
  // Låsen beskyttede SVARET, og 14/11-2026 blev folden bundet til TUREN fordi
  // hovedet dengang ikke fandtes under streamen: lukkede gruppen ved slutsvaret,
  // forsvandt både rundelinje og ur (målt: `data-aaben=false`).
  //
  // Den begrundelse er væk 18/11-2026, hvor hovedet findes hele turen — og
  // Bjørn 27/11-2026 kræver det modsatte: «foldet skete stadig ikk før slut
  // beskeden». Folden hører til svarets BEGYNDELSE, ikke turens afslutning.
  // Rundelinjen forsvinder ikke med den: den vises netop når folden er lukket
  // (se `!arbejdeAabent`-grenen nedenfor).
  const arbejdeKoerer = streaming || arbejdeEfterSvar
  // FOLDEN LUKKER FØR DEN EKSTRA RUNDE (Bjørn 27/11-2026): «du skal folde
  // hoved før du køre den extra runde».
  //
  // `aaben` fulgte `arbejdeKoerer`, og `arbejdeKoerer` er også sand i
  // follow-up-vinduet. Så i det øjeblik den ekstra runde ankom, blev `aaben`
  // sand og hovedet foldede UD igen — og foldede først sammen da HELE turen
  // sluttede. Målt: brugeren skulle folde hovedet manuelt sammen for at se
  // den ekstra runde og slutbeskeden.
  //
  // Folden hører til den FØRSTE del af turen: den lukker når slutsvaret er
  // skrevet. Arbejde der ankommer EFTER svaret er ikke en genåbning af
  // hovedet — det har sin egen container under besvarelsen
  // (`[data-runder-efter]`), med sin egen levetid.
  //
  // `arbejdeKoerer` er UÆNDRET: uret og «kører»-markøren skal stadig vise at
  // der arbejdes. Det er kun foldens tilstand der ikke må følge den.
  //
  // MEN kun når hale-containeren FAKTISK ejer arbejdet. Findes der ingen
  // besvarelse at lægge runden under, bliver dens segment `'foer'` og ligger
  // i folden — og så ville et lukket hoved gøre arbejdet usynligt alle steder.
  const haleEjerArbejdet = arbejdeEfterSvar && efterSegmenter.length > 0
  // FOLDEN LUKKER NÅR SLUTSVARET BEGYNDER (Bjørn 27/11-2026: «foldet skete
  // stadig ikk før slut beskeden»).
  //
  // `streaming` er sand gennem HELE turen — også mens slutsvaret skrives. Den
  // forrige gate (`streaming && !haleEjerArbejdet`) holdt derfor hovedet åbent
  // indtil `message_stop`, altså til efter svaret. Folden kom baglæns.
  //
  // UNDTAGELSEN VAR SELV FEJLEN (målt 27/11-2026). Den lød
  // `arbejdeEfterSvar && !haleEjerArbejdet`, men `arbejdeEfterSvar` bliver
  // sand allerede ved det FØRSTE `run_frame` efter `svarLaast` — altså i det
  // øjeblik slutsvaret begynder, længe før nogen hale-container findes. Så
  // undtagelsen var sand gennem hele slutsvaret og holdt hovedet åbent: den
  // «beskyttelse» jeg byggede, var den mekanisme der blokerede folden.
  //
  // Den ægte betingelse er ikke flaget, men om der findes arbejde der reelt
  // ikke kan vises andre steder. To tilfælde:
  //
  //  1. Der findes INGEN besvarelse. Så ligger runde-arbejdet i folden, og et
  //     lukket hoved ville gøre det usynligt alle steder (`svarLaast.test.tsx`
  //     værner præcis dette: `blocks=[summary]` uden besvarelse).
  //  2. Der findes arbejde EFTER besvarelsen som hverken er lagt i
  //     hale-containeren eller vist i besvarelsen.
  //
  // Arbejde FØR besvarelsen hører i folden og er synligt via rundelinjen — det
  // er ikke en grund til at holde hovedet åbent.
  const harBesvarelse = model.segmenter.some((segment) => segment.slags === 'besvarelse')
  const arbejdeUdenContainer = arbejdeEfterSvar
    && !haleEjerArbejdet
    && (!harBesvarelse || model.segmenter.some((segment) =>
      segment.slags === 'runde'
      && segment.plassering === 'efter'
      && segment.blokke.some((block) => block.type !== 'text' && block.type !== 'thinking')))
  const aaben = aabenManuelt ?? ((streaming || (explicitProtocol && !svarFaerdigPacet))
    && (!shownAnswerStarted || (!explicitProtocol && arbejdeUdenContainer)))
  // Arbejdsdetaljerne under rundelinjen. Mens der arbejdes er de foldet
  // sammen som udgangspunkt — den levende linje er nok — men Bjørn kan folde
  // dem ud UNDER streaming (17/10-2026: «runde linjen under streaming bør
  // have > i ende og kunne foldes ud»). Efter turen følger de turhovedets
  // fold, som før.
  const arbejdeAabent = aktiv ? aabenManuelt === true : aaben
  // Once revealed, retain the details through the outer fold's transition.
  const detailsRunRef = useRef<string | null>(null)
  if (arbejdeAabent) detailsRunRef.current = runKey
  const detailsMounted = arbejdeAabent || !turenKoerer || detailsRunRef.current === runKey

  // ── DET FLADE DOKUMENTFLOW (26/11-2026) ────────────────────────────────
  //
  // Bjørn: «det vigtigste er at gøre foldet irrelevant for pacens funktion»,
  // og GPT's tredje krav: «en runde uden for hovedet er stadig arbejde, men
  // dens container skal forblive synlig indtil turafslutningen».
  //
  // Den gamle struktur er TRE containere i fast rækkefølge: hoved, arbejde,
  // svar. Den kan ikke udtrykke Besvarelse A → Runde 1 → Besvarelse B, fordi
  // A og B ligger i samme container og runden i en anden. Rækkefølgen findes
  // nu som data i `model.segmenter`, og her bliver den til DOM i den orden.
  //
  // Hver container har sin egen React-key fra segmentets KILDEIDENTITET (se
  // `kildeNoegl` i chatFlowModel) — ikke fra dets position. En reconnect der
  // udfylder et hul, eller en `skillFlade` der præpendes, forskubber
  // positionen men ikke kilden, så containeren beholder sin instans.
  //
  // `plassering` bærer LEVETIDEN, ikke rollen: et runde-segment efter
  // slutsvaret er stadig arbejde, men det bliver stående til turen slutter.
  // Den flade gren tager KUN over når rækkefølgen faktisk afviger fra den
  // gamle struktur — altså når et runde-segment med RIGTIGT arbejde ligger
  // efter en besvarelse.
  //
  // `progress` og `approval` tæller ikke: begge er blokke der hører til et
  // KALD, men som ved persistens kan havne efter slutsvaret. `progress` bliver
  // samlet sidst i `content_json` (se `ANSWER_BOUNDARY_TYPES`), og en
  // `approval` der ikke kunne matches til sit kald bliver lagt sidst af
  // `indsaetVedKald`. Ingen af dem er en ny runde — og uden denne udelukkelse
  // ville hver persisteret tur med et værktøjskald eller en godkendelse tage
  // den flade gren og rive de målte gates ned.
  // `fladtFlow` er AFLYST (Bjørn 27/11-2026). Den valgte mellem to
  // indre strukturer under `.chat-flow-answer`, og det var selve koblingen:
  // besvarelsen blev remountet i det øjeblik en hale-runde gjorde grenen sand.
  // Sondringen lever nu som `plassering` i modellen og som `efterSegmenter`
  // ovenfor — strukturen skifter ikke, kun hvilken container der ejer hvad.

  return (
    // `control` er kun en chat-flade (14/11-2026). `BlocksRenderer` deles med
    // `RaekkeTranskript` (code mode), så uden denne Provider ville slideren
    // også dukke op i maskinrummet. Kontekstens default er falsk — glemmer
    // nogen at sætte flaget, forsvinder fladen frem for at dukke op forkert.
    <FladeKontrolContext.Provider value>
    <FladeDeferredTurnContext.Provider value={deferredTurn}>
    <div className="chat-flow" data-chat-flow-mode={mode}>
      {visTurhoved ? (
          <TurHoved
          skjult={!shownAnswerStarted && aaben && (streaming || (explicitProtocol && !svarFaerdigPacet))}
            aaben={aaben}
            foldbar={harArbejde}
            koerer={arbejdeKoerer}
            /* Uret er ikke bundet til `streaming` (14/11-2026): hovedet er
               turens RESULTAT og findes først når turen er slut — netop dér
               hvor `streaming` er falsk. Bandt vi tallet til streamen, ville
               hovedet stå uden ur præcis i den fase det nu ejer. */
            sekunder={sekunder}
            tekst={model.hovedTekst}
            /* Token-tallet er ikke bundet til `streaming` (14/11-2026), af
               samme grund som uret: hovedet findes netop i den fase hvor
               streamen er slut. Bandt vi tallet til streamen, stod hovedet
               uden sit resultat præcis når det skulle vise det. */
            meta={tokens > 0
              ? <span className="rv-turMeta">~<RullendeTokens tokens={tokens} /> output</span>
              : null}
            levende={streaming}
            onToggle={() => {
              const naeste = !aaben
              setAabenManuelt(naeste)
              if (naeste) onWorkExpanded?.()
            }}
          />
      ) : null}
      {/* Chat mode viser én levende statuslinje ad gangen. Den erstattes
          på stedet under turhovedets streg og forsvinder, når svaret
          begynder. De fulde arbejdsdetaljer er fortsat tilgængelige ved
          at folde en afsluttet tur ud.

          Bjørn 20/10-2026: «synteser og runder forsvinder i et blink».
          `hidden` er `display: none` i ÉN frame — der er ingen højde at
          animere fra, så hele billedet rykker sammen med præcis linjernes
          højde. Gruppen bliver derfor stående i DOM'en, og den ydre ramme
          glider fra `1fr` til `0fr` (grid-rækker kan animeres i både
          Chromium og Safari; `height: auto` ville kræve `interpolate-size`,
          som kun Chromium har). */}
      {visArbejdsgruppe ? (
          <div className="chat-flow-gruppe-ydre" data-aaben={aaben ? 'true' : 'false'}
            /* `inert` er den ærlige erklæring om den lukkede fold (18/11-2026):
               indholdet bliver i DOM'en så rækken kan animere, men det er
               fjernet fra tilgængelighedstræet og tab-rækkefølgen. Uden den
               ville skjult arbejde være læsbart for skærmlæsere og søgbart i
               DOM'en — prisen for at fjerne blinket må ikke være usynligt
               indhold der alligevel kan tilgås. */
            {...(aaben ? {} : { inert: true })}>
            <div className="chat-flow-gruppe" aria-hidden={!aaben}>
            {/* INDHOLDET BLIVER I DOM'EN (18/11-2026 — blink 1).
                Før var denne blok betinget af `aaben`, så den blev AFMONTERET
                i samme frame som rammen begyndte at glide fra `1fr` til
                `0fr`. Der var da intet indhold tilbage at animere, og folden
                blev et hop i stedet for en glidning — præcis det CSS'en blev
                bygget til at undgå 20/10-2026.
                Nu styrer `visArbejdsgruppe` om indholdet FINDES, og `aaben`
                styrer kun om det er SYNLIGT (via rammens rækkehøjde og
                `aria-hidden`). Så glider det ud i stedet for at forsvinde. */}
            {harArbejde || turenKoerer || levendeSyntese || model.arbejdsTilstand === 'placeholder' ? (
              <div className={`chat-flow-activity chat-flow-activity--${mode} chat-flow-activity--motion-safe`}
                data-testid="chat-flow-activity" role="status" aria-live="polite" aria-atomic="true"
                aria-label={[activeSynthesis, rundeTekst].filter(Boolean).join('. ')}>
                {/* MÅLT 14/11-2026: hele denne blok var betinget af
                    `!arbejdeAabent`, så fold-pilen forsvandt i samme frame som
                    man foldede ud — der var ingen vej tilbage. Syntesen og
                    rundelinjen skal stadig vige for den udfoldede kronologi,
                    men FOLD-KNAPPEN må ikke forsvinde med dem. */}
                {!arbejdeAabent && levendeSyntese ? (
                  <div className="chat-flow-live-synthesis" data-testid="chat-flow-live-synthesis"
                    aria-hidden="true">
                    <SynteseLinje tekst={levendeSyntese.tekst} noegle={levendeSyntese.noegle} />
                  </div>
                ) : null}
                {!arbejdeAabent && (rundeTekst || turenKoerer || model.arbejdsTilstand === 'placeholder') ? (
                  <div className="chat-flow-round" data-testid="chat-flow-round"
                    data-pacing-skjult={skjulAktivRunde ? '' : undefined}>
                    <div className="chat-flow-round-line" data-testid="chat-flow-round-line"
                      aria-hidden="true">
                      <span className="chat-flow-presence" data-testid="chat-flow-presence">
                        <JarvisRing size={15} spinning tone="working" />
                      </span>
                      {rundeTekst ? (
                        <span className="chat-flow-round-label" data-testid="chat-flow-round-label">
                          <TitelCrossfade tekst={rundeTekst} aktiv className="linje-titel shimmer" />
                        </span>
                      ) : null}
                      {/* Uret og token-tallet bor i HOVEDET, ikke her.
                          Bjørn 14/11-2026: «du har blandet turhoved ind i
                          rundelinjen i stedet for at lade dem være adskilt».
                          De blev flyttet herned for at dække et vindue hvor
                          hovedet ikke findes — men det gjorde rundelinjen
                          til en kopi af hovedet. De to linjer har hver sin
                          opgave: rundelinjen siger HVAD der sker nu, hovedet
                          siger HVAD turen kostede. Tallet hører i resultatet. */}
                    </div>
                  </div>
                ) : null}
                {/* Ingen fold-pil her (Bjørn 14/11-2026: «den skal væk»).
                    Den stod som en selvstændig `>` UNDER rundelinjen, fordi
                    aktivitetsgruppen er `display: block` — så den faldt på sin
                    egen linje og læste som en tredje, løsrevet ting i stedet
                    for som en del af runden.

                    Opdelingen er også den rigtige: rundelinjen er STATUS og
                    bærer ingen affordances; hovedet er RESULTATET og har
                    fold-pilen. Under turen er der intet at folde ud — den
                    levende linje ER visningen. Efter turen folder man via
                    `button.rv-tur`. */}
              </div>
            ) : null}

            {/* Arbejdsdetaljerne bliver OGSÅ i DOM'en (18/11-2026 — blink 1,
                anden halvdel). De var de sidste der blev afmonteret ved lukket
                fold: man foldede ud, klikkede luk, og i samme frame som rækken
                begyndte at glide var indholdet væk — rækken gled tom.
                Gaten er derfor ikke `arbejdeAabent` alene, men tre tilfælde:
                  · brugeren har åbnet folden        → monteret og synligt
                  · turen er slut                    → monteret, rammen skjuler
                  · turen kører og er ikke åbnet     → IKKE monteret
                Det sidste er ikke en undtagelse for nemhedens skyld: i den
                levende fold har detaljerne aldrig været vist (rundelinjen er
                turens ansigt), så der er intet at animere — og `foldWork` er
                fyldt allerede under streaming, så en ubetinget montering ville
                vælte hele arbejdsloggen ind under rundelinjen midt i turen.
                Prisen i de to første tilfælde holdes nede af rammen: den
                lukkede gruppe er `display: none`, så browseren springer layout
                og maling af undertræet over. */}
            {foldWork.length > 0 && detailsMounted ? (
              <div className="chat-flow-work-details raekkevisning">
                <Arbejdsforloeb blocks={foldWork} streaming={streaming}
                  rundeEtiketter={rundeEtiketter} beskedId={beskedId} config={config} />
              </div>
            ) : null}
            </div>
          </div>
      ) : null}

      {inlineQuestions.length > 0 ? (
        <div className="chat-flow-inline-question">
          <BlocksRenderer blocks={inlineQuestions} density={density} streaming={streaming}
            beskedId={beskedId} config={config} />
        </div>
      ) : null}

      {/* ÉN STABIL DOKUMENTSTRUKTUR — NU UDEN GREN (Bjørn 27/11-2026).

          GPT's krav 26/11 var at undgå et dynamisk skift mellem gammel og ny
          renderer. Det blev løst halvt: `.chat-flow-answer` blev stabil, men
          dens DIREKTE BARN skiftede mellem `BlocksRenderer`s rod og
          `.chat-flow-segmenter` — så besvarelsen remountede alligevel.

          Bjørns dom 27/11: «Stop med at kompensere for strukturskiftet gennem
          animationer … hver deres uafhængige visuelle livscyklus i én stabil
          dokumentstruktur.» Derfor er grenen væk. Besvarelsen er ALTID denne
          ene `BlocksRenderer` i denne ene `.chat-flow-answer`, fra første tegn
          til turen er slut. En hale-runde tilføjes UNDER den — den flytter
          intet her. */}
      {explicitProtocol ? (
        <div className="chat-flow-answer chat-flow-answer--ordered">
          {model.segmenter.filter((segment) => segment.slags === 'besvarelse' || segment.plassering === 'efter')
            .map((segment) => segment.slags === 'besvarelse' ? (
              <div key={segment.id} className="chat-flow-answer-text">
                <BlocksRenderer blocks={segment.blokke.filter((b) => !erLeverance(b))} density={density}
                  streaming={streaming} hale={turenKoerer} beskedId={beskedId} config={config} />
              </div>
            ) : efterSegmenter.includes(segment) ? (
              <div key={segment.id} className="chat-flow-runde" data-segment="runde" data-plassering="efter"
                data-levetid={turenKoerer ? 'live' : 'kollapset'} aria-hidden={!turenKoerer}
                {...(turenKoerer ? {} : { inert: true })}>
                <div className="chat-flow-runde-indhold">
                  <BlocksRenderer blocks={segment.blokke} density={density} streaming={streaming}
                    rundeEtiketter={rundeEtiketter} tankeResumeer={tankeResumeer} beskedId={beskedId} config={config} />
                </div>
              </div>
            ) : null)}
        </div>
      ) : <>
      {synligeSvar.length > 0 ? (
        <div className="chat-flow-answer">
          <BlocksRenderer blocks={synligeSvar} density={density} streaming={streaming}
            beskedId={beskedId} config={config} />
        </div>
      ) : null}

      {/* RUNDER EFTER BESVARELSEN — EGEN LIVSCYKLUS, SAMME STRUKTUR.

          Hver runde er sin egen container med en key fra KILDEN (se
          `kildeNoegl`), så en reconnect der udfylder et hul eller en
          præpendering ikke river den ned. `data-levetid` bærer fasen:
          live → kollapset → unmount, præcis som før — men nu uden at nogen
          anden container skifter struktur for at gøre plads. */}
      {efterSegmenter.some((segment) => turenKoerer || !afmonterede.has(segment.id)) ? (
        <div className="chat-flow-runder-efter" data-runder-efter>
          {efterSegmenter.map((segment) => {
            const levetid = turenKoerer
              ? 'live'
              : afmonterede.has(segment.id)
                ? 'unmount'
                : 'kollapset'
            if (levetid === 'unmount') return null
            return (
              <div
                key={segment.id}
                ref={(node) => {
                  // Callback-ref PER segment: den registrerer sig selv i
                  // kortet, så effekten ovenfor kan lytte på netop denne
                  // containers transition. `null` betyder afmonteret.
                  if (node) kollapsRefs.current.set(segment.id, node)
                  else kollapsRefs.current.delete(segment.id)
                }}
                className="chat-flow-runde"
                data-segment="runde"
                data-plassering="efter"
                data-levetid={levetid}
                data-segment-id={segment.id}
              >
                {/* ÉN RÆKKE, IKKE SEKS (målt 27/11-2026 i Chromium).
                    `grid-template-rows: 1fr` gælder kun den FØRSTE række.
                    `BlocksRenderer` giver flere søskende, så seks værktøjskald
                    blev seks grid-børn og kun 1/6 af højden animerede. Med én
                    wrapper findes der præcis én række. */}
                <div className="chat-flow-runde-indhold">
                  <BlocksRenderer blocks={segment.blokke} density={density} streaming={streaming}
                    rundeEtiketter={rundeEtiketter} tankeResumeer={tankeResumeer}
                    beskedId={beskedId} config={config} />
                </div>
              </div>
            )
          })}
        </div>
      ) : null}

      </>}

      {/* Leverancen (widgetten) ankommer EFTER pacen — ikke midt i den.
          Bjørn 29/10-2026: «det bør kun tilføjes naturligt i enden af pacen».
          Pladsen reserveres mens den venter, så det er widgetten der fader
          ind og ikke layoutet der hopper. */}
      {ventendeLeverancer.length > 0 ? (
        <div className="chat-flow-leverance-plads" data-leverance-plads aria-hidden="true" />
      ) : null}
      {!venterPaaPace && answer.some(erLeverance) ? (
        <div className="chat-flow-leverance" data-leverance="widget" data-ankomst="ankommet">
          <BlocksRenderer blocks={answer.filter(erLeverance)} density={density}
            streaming={streaming} beskedId={beskedId} config={config} />
        </div>
      ) : null}
    </div>
    </FladeDeferredTurnContext.Provider>
    </FladeKontrolContext.Provider>
  )
}
