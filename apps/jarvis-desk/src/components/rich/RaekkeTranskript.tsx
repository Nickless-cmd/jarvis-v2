/**
 * Rækkevisningen: synteser med foldbare arbejdsrunder imellem.
 *
 * ## Hvad den er
 *
 * Et alternativ til bobblevisningen, bag en knap. Turens eksisterende
 * Working-linje rummer synlige synteser og en foldbar række for hvert stykke
 * værktøjsarbejde imellem dem. Det endelige svar bliver stående.
 *
 * ## Hvorfor den føles glat
 *
 * Det er ikke animation. Det er at intet skifter højde mens svaret streamer:
 * rækken er 24px før, under og efter, og teksten klippes i stedet for at
 * ombryde. `contain: size layout` sidder ÉT sted — på den sammenfoldede
 * tænke-række — præcis som i forlægget.
 *
 * ## Hvad den IKKE rører
 *
 * Composer, liveness-indikator og save-rail (Bjørn 22/9-2026: «vores composer
 * og liveness indikator og savedrail osv. Skal blive»). Kun transskriptet.
 * Prosaen går stadig gennem `BlocksRenderer`, så markdown, kodeblokke og
 * billeder er nøjagtig som i bobblevisningen.
 */
import { memo, useRef, useState } from 'react'
import { Sparkles, Sparkle, ChevronDown, ChevronRight, SquareTerminal, BookOpen, type LucideIcon } from 'lucide-react'
import type { ContentBlock } from '../../lib/sseProtocol'
import type { ApiConfig } from '../../lib/api'
import { opdel, opdelArbejdsrunder, turFortalt, type ArbejdsElement } from '../../lib/raekkeModel'
import { lookupTool } from '../../lib/toolRegistry'
import { describeTool, subjectFromInput, summarizeRound, summerDiff } from '../../lib/toolRound'
import { diffFraResultat, diffStat } from '../../lib/diffStat'
import { postFor, kropFor } from './raekkeKroppe'
import { erUnderagent } from '../../lib/agentKald'
import { BlocksRenderer, etiketterFraBlokke } from './BlocksRenderer'
import { MarkdownRenderer } from './MarkdownRenderer'
import { useFoldPosition } from './useFoldPosition'

/** Første linje af en tanke — resten ligger i kroppen. */
function foersteLinje(s: string): string {
  const t = s.trim().split('\n').find((l) => l.trim()) ?? ''
  return t.trim()
}

/** Fold-pilen. Et RIGTIGT ikon — ikke teksttegnet ▸/▾ (Bjørn 23/9-2026:
 *  «slippe for ▸ som ikon og så bare bruge den rigtige >»).
 *
 *  Retningen skiftes ved at BYTTE ikonet frem for at rotere det, så stregen
 *  står skarp i begge tilstande — samme greb som forlægget
 *  (DisclosureRow.tsx:68: `leading = open ? <Chevron/> : icon`). */
function FoldPil({ aaben }: { aaben: boolean }) {
  return aaben
    ? <ChevronDown size={18} strokeWidth={1.75} />
    : <ChevronRight size={18} strokeWidth={1.75} />
}

function Syntese({ tekst, streaming }: { tekst: string; streaming: boolean }) {
  return <div className="rv-mellem"><MarkdownRenderer text={tekst} streaming={streaming} /></div>
}

const KOMMANDOER = new Set(['bash', 'bash_session_run', 'bash_session_open', 'bash_session_close', 'bash_output', 'run_in_background', 'session_run'])

/**
 * Værktøjer der henter viden IND — filer, kode, hukommelse, net, efterforskning
 * — uden selv at ændre noget.
 *
 * Navnene er GRUNDNAVNE: `arbejdsIkon` stripper `operator_` før opslaget, så
 * `operator_read_file` rammer `read_file`. Et navn med præfiks her ville
 * aldrig matche — samme stille dødsfald som `_CORE_TOOL_GROUPS` advarer om.
 *
 * Grænsen: drifts- og statusværktøjer (`daemon_status`, `central_query`,
 * `list_self_wakeups`) er IKKE med. De inspicerer maskineriet; de henter ikke
 * viden ind.
 */
const LAESERE = new Set([
  // Filer og kode
  'read_file', 'pdf_read', 'docs_read', 'list_dir', 'find_files', 'glob', 'search', 'grep',
  // Hukommelse
  'recall', 'recall_memories', 'search_memory', 'search_jarvis_brain',
  'read_memory_topic', 'curiosity_search_memory',
  // Nettet
  'web_search', 'web_fetch', 'drive_search',
  // Efterforskning
  'scout_agent',
])

/**
 * Arbejdsrundens ikon — rundens FORM, ikke dens sidste skridt.
 *
 * Læste runden noget og gjorde den så noget mekanisk, er den en undersøgelse
 * (bogen). Var ALT mekanisk, er den en kommando (terminalen). Ellers bærer den
 * det sidste værktøjs eget ikon.
 *
 * Bogen hang før på ét eneste navn (`read_file`), så `search`+`bash`,
 * `recall`+`bash` og `web_search`+`bash` — alle research-runder — faldt til
 * terminalen. Prædikatet er derfor et SÆT læsere (Bjørn 24/9-2026).
 */
function arbejdsIkon(vaerktoejer: Extract<ContentBlock, { type: 'tool_use' }>[]): LucideIcon {
  const navne = vaerktoejer.map((t) => t.name.replace(/^operator_/, ''))
  if (navne.some((n) => LAESERE.has(n)) && navne.some((n) => KOMMANDOER.has(n))) return BookOpen
  if (navne.length > 0 && navne.every((n) => KOMMANDOER.has(n))) return SquareTerminal
  return lookupTool(vaerktoejer[vaerktoejer.length - 1]?.name ?? '').Icon
}

function Raekke({
  Ikon, slags, sum, krop, koerer, fejl, tanke, mrkat, kind,
}: {
  Ikon: LucideIcon
  /** Kort etiket foer sammenfatningen. Udelades naar raekken ER sit eget
   *  emne — progress-sporet viser vaerktoejets ikon og emnet i stedet for et
   *  navn for handlingen (Bjoern 23/9-2026: «Koerer kommando skal helt vaek»). */
  slags?: string
  sum: React.ReactNode
  krop?: React.ReactNode
  koerer?: boolean
  fejl?: boolean
  tanke?: boolean
  /** Lille etiket yderst — «subagent». Kun naar den betyder noget. */
  mrkat?: string
  /** Resultatformen fra navnekortet (`postFor`). Farver KUN glyffen — aldrig
   *  rækken: de to malede flader (siden, brugerboblen) er dét der holder
   *  visningen rolig. Farve på blæk er ikke en flade; farve på rækken ville
   *  være det. Rækkefølgen bliver en farvekodet margen man scanner med øjet. */
  kind?: string
}) {
  const [aaben, setAaben] = useState(false)
  const foldRef = useRef<HTMLDivElement>(null)
  const huskFold = useFoldPosition(foldRef, aaben)
  const foldbar = krop != null
  return (
    <div
      ref={foldRef}
      className="rv-r"
      {...(foldbar ? { 'data-foldbar': '' } : {})}
      {...(aaben ? { 'data-aaben': '' } : {})}
      {...(koerer ? { 'data-koerer': '' } : {})}
      {...(fejl ? { 'data-fejl': '' } : {})}
      {...(tanke ? { 'data-tanke': '' } : {})}
      {...(kind ? { 'data-kind': kind } : {})}
      {...(foldbar
        ? { role: 'button', tabIndex: 0, 'aria-expanded': aaben, onClick: () => { huskFold(); setAaben((v) => !v) },
            onKeyDown: (e: React.KeyboardEvent) => {
              if (e.target !== e.currentTarget || (e.key !== 'Enter' && e.key !== ' ')) return
              e.preventDefault(); huskFold(); setAaben((v) => !v)
            } }
        : {})}
    >
      <div className="rv-hoved">
        {/* Rigtigt ikon pr. vaerktoej fra TOOL_REGISTRY — en `read_file` og en
            `web_search` saa ens ud da alle raekker delte den samme tekst-glyf.
            Paa hover falmer ikonet ud og en chevron ind over 100ms; ingen
            raekke-fill, praecis som forlaegget (DisclosureRow.module.css:63). */}
        <span className="rv-ikon" aria-hidden="true">
          <Ikon className="rv-glyf" size={14} strokeWidth={1.75} />
          <ChevronDown className="rv-hoverChev" size={14} strokeWidth={1.75} />
        </span>
        {slags ? <span className="rv-slags">{slags}</span> : null}
        {sum !== '' && sum != null ? (
          <>
            {slags ? <span className="rv-sep" aria-hidden="true" /> : null}
            {/* Mens raekken koerer foelger teksten ENDEN — ellers ser man kun
                begyndelsen af en lang tanke, og raekken virker doed. */}
            <span className="rv-sum" {...(koerer ? { 'data-foelg-ende': '' } : {})}>
              <span className={`rv-sumT${koerer ? ' shimmer' : ''}`}>{sum}</span>
            </span>
          </>
        ) : <span className="rv-sum" />}
        {mrkat && <span className="rv-mrkat">{mrkat}</span>}
        {foldbar && <span className="rv-chev" aria-hidden="true"><FoldPil aaben={aaben} /></span>}
      </div>
      {foldbar && aaben && <div className="rv-krop">{krop}</div>}
    </div>
  )
}

function Element({ e, streaming, config, beskedId }: {
  e: ArbejdsElement; streaming: boolean; config?: ApiConfig; beskedId?: string
}) {
  if (e.slags === 'mellemsvar') {
    // Jarvis' korte narration MELLEM kaldene. Den bor i gruppen og folder sig
    // sammen med arbejdet — den er ikke en besked (Bjoern 22/9-2026).
    return <Syntese tekst={e.tekst} streaming={streaming} />
  }
  if (e.slags === 'spor') {
    // ÉN linje der opdaterer sig — den viser det SENESTE trin, og hele
    // forloebet ligger i kroppen. Ni «Koerer kommando: python» under
    // hinanden er stoej; det ene man vil vide er hvor den er naaet til.
    const sidste = e.trin[e.trin.length - 1]!
    // Hvert trin viser vaerktoejets IKON og emnet — ikke serverens label-tekst
    // («Koerer kommando: git status») raat. Bjoern 23/9-2026: «Koerer kommando
    // skal helt vaek og erstattes af ikone og dette echo === burde vise den
    // faktisk kommando». `tool`/`hint` kom med 23/9; en gemt besked fra foer
    // dem har dem ikke, og falder tilbage til `message`.
    const emne = (t: (typeof e.trin)[number]) => t.hint || t.message
    return (
      <Raekke
        Ikon={lookupTool(sidste.tool ?? '').Icon}
        sum={emne(sidste)}
        koerer={streaming && sidste.status === 'running'} fejl={sidste.status === 'error'}
        krop={
          <div className="rv-kort rv-liste rv-sporListe">
            {e.trin.map((t, i) => {
              const TrinIkon = lookupTool(t.tool ?? '').Icon
              return (
                <div key={i} className="rv-i">
                  <TrinIkon className="rv-iIkon" size={13} strokeWidth={1.75} aria-hidden="true" />
                  <span>{emne(t)}</span>
                </div>
              )
            })}
          </div>
        }
      />
    )
  }
  const b = e.blok
  if (b.type === 'thinking') {
    return (
      <Raekke
        tanke Ikon={Sparkles} slags="Think"
        sum={foersteLinje(b.thinking)}
        koerer={streaming && !b.seconds}
        krop={<div className="rv-kort"><pre>{b.thinking}</pre></div>}
      />
    )
  }
  if (b.type === 'skill_surface') {
    return <Raekke Ikon={Sparkle} slags="Skill" sum={b.matches.map((m) => m.name).join(' · ')} />
  }
  if (b.type === 'tool_use') {
    const { etiket } = postFor(b.name)
    const meta = lookupTool(b.name)
    const fejl = b.status === 'error'
    // `input` er TOMT mens argumenterne stroemmer ind — de ligger i
    // `partialJson` imens (toolRound.ts:142). Bruger man kun registrets
    // `summarize`, staar raekken tom netop mens den er mest interessant, og
    // fyldes foerst naar hele svaret er faerdigt (Bjoern 23/9-2026).
    // `subjectFromInput` er bobblevisningens egen loesning paa praecis det.
    const emne = subjectFromInput(b.input, b.partialJson) || meta.summarize(b.input, b.result)
    // `+N −M` paa redigerende vaerktoejer. Serverens maalte tal foerst, ellers
    // regnet ud af kaldets argumenter — samme raekkefoelge som bobblevisningen
    // (toolRound.ts:402). Uden den stod `.rv-diffstat` som en DOED klasse:
    // stilen fandtes, men ingen tegnede den (Bjoern 23/9-2026).
    const ds = diffFraResultat(b.result) ?? diffStat(b.name, b.input)
    const sum = ds
      ? <>{emne} <span className="rv-diffstat">
          {/* `git-add`/`git-del` er desks egne, pinnet af tokens.test.ts og
              brugt fem steder i forvejen (ToolCard, ToolGroupCard, ReviewPanel,
              ArtifactsView). Vi laaner dem — raekkevisningen skal ikke have sin
              egen groenne og roede. */}
          <span className="git-add">+{ds.add}</span> <span className="git-del">−{ds.del}</span>
        </span></>
      : emne
    return (
      <Raekke
        Ikon={meta.Icon} slags={etiket}
        sum={sum}
        koerer={streaming && b.status === 'running'}
        fejl={fejl}
        krop={kropFor(b.name, b.input, b.result, fejl, config,
          { partialJson: b.partialJson, running: streaming && b.result == null && (b.status ?? 'running') === 'running' },
          { beskedId, toolUseId: b.id })}
        kind={postFor(b.name).familie}
        mrkat={erUnderagent(b.name) ? 'subagent' : undefined}
      />
    )
  }
  // Alt andet — `image`, `file`, `tool_use_summary` og hvad der maatte komme
  // til — gaar gennem bobblevisningens renderer. En `return null` her ville
  // lade blokke forsvinde SPORLOEST: ingen fejl, ingen tom raekke, bare
  // indhold der ikke er der. Det er praecis hvad der skete for `progress`.
  return <BlocksRenderer blocks={[b]} density="compact" streaming={streaming} />
}

function Arbejdsrunde({
  elementer, streaming, sidste, harSvar, config, rundeEtiketter, beskedId,
}: {
  elementer: ArbejdsElement[]
  streaming: boolean
  sidste: boolean
  harSvar: boolean
  config?: ApiConfig
  beskedId?: string
  rundeEtiketter: Record<string, string>
}) {
  const [aaben, setAaben] = useState(false)
  const foldRef = useRef<HTMLButtonElement>(null)
  const huskFold = useFoldPosition(foldRef, aaben)
  const vaerktoejer: Extract<ContentBlock, { type: 'tool_use' }>[] = []
  for (const e of elementer) {
    if (e.slags === 'blok' && e.blok.type === 'tool_use') vaerktoejer.push(e.blok)
  }
  const seneste = vaerktoejer[vaerktoejer.length - 1]
  const diff = summerDiff(vaerktoejer)
  const koerer = Boolean(seneste && streaming && (seneste.status ?? 'running') === 'running')
  // Et afsluttet kald afslutter ikke nødvendigvis Jarvis' arbejdsrunde. Hold
  // den sidste fortælling levende indtil en ny sektion eller svaret begynder.
  const visShimmer = streaming && sidste && (koerer || !harSvar)
  const etiket = [...vaerktoejer].reverse().map((t) => rundeEtiketter[t.id]).find(Boolean)
  const mekanisk = summarizeRound(vaerktoejer)
  // Under udførelse: Jarvis' `description` eller den aktuelle handling.
  // Bagefter: modelens rundeopsummering, ellers en faktuel afslutning.
  //
  // Bjørn 24/9-2026: «det er bare <færdig> der ikk passer ind». Linjen bar før
  // et «Færdig · »-præfiks foran den mekaniske tekst, sat ind for at skelne en
  // afsluttet runde fra en kørende. Ordet var et fremmedelement i en linje der
  // ellers er ren handling — og skelnen findes allerede i shimmeren.
  const beskrivelse = koerer && seneste
    ? describeTool(seneste.name, seneste.input, true, seneste.partialJson, seneste.result, seneste.status)
    : etiket || mekanisk
  const Ikon = arbejdsIkon(vaerktoejer)
  return (
    <div className="rv-arbejdsrunde">
      <button type="button" ref={foldRef} className="rv-arbejdsknap" aria-expanded={aaben}
        {...(visShimmer ? { 'data-koerer': '' } : {})}
        onClick={() => { huskFold(); setAaben((v) => !v) }}>
        <Ikon className="rv-arbejdsikon" size={17} strokeWidth={1.8} aria-hidden="true" />
        <span className={`rv-arbejdsfortaelling${visShimmer ? ' shimmer' : ''}`}>{beskrivelse}</span>
        {diff && <span className="rv-diffstat" aria-label={`Tilføjet ${diff.add} linjer, fjernet ${diff.del} linjer`}>
          <span className="git-add">+{diff.add}</span> <span className="git-del">−{diff.del}</span>
        </span>}
        <span className="rv-turC" aria-hidden="true"><FoldPil aaben={aaben} /></span>
      </button>
      <div className="rv-arbejdsdetaljer" hidden={!aaben}>
        {elementer.map((e, i) => <Element key={i} e={e} streaming={streaming} config={config} beskedId={beskedId} />)}
      </div>
    </div>
  )
}

function RaekkeTranskriptImpl({
  blocks, streaming, beskedId, config, rundeEtiketter,
}: {
  blocks: ContentBlock[]
  streaming: boolean
  beskedId?: string
  config?: ApiConfig
  rundeEtiketter?: Record<string, string>
}) {
  const { arbejde, svar, kald, sekunder } = opdel(blocks)
  const sektioner = opdelArbejdsrunder(arbejde)
  // Familien pr. kald — SAMME kilde som kroppene (`postFor`), så turens
  // hoved og rækkerne aldrig kan fortælle to forskellige historier.
  const familier = arbejde.flatMap((e) =>
    e.slags === 'blok' && e.blok.type === 'tool_use' ? [postFor(e.blok.name).familie] : [],
  )
  const etiketter = { ...etiketterFraBlokke(blocks), ...(rundeEtiketter ?? {}) }
  // Aaben mens der arbejdes, lukket naar turen er slut — man skal kunne
  // FOELGE MED, og bagefter skal rodet vaek (Bjoern 22/9-2026).
  const [aabenManuelt, setAabenManuelt] = useState<boolean | null>(null)
  const aaben = aabenManuelt ?? streaming
  const turRef = useRef<HTMLButtonElement>(null)
  const huskFold = useFoldPosition(turRef, aaben)

  return (
    <div className="raekkevisning">
      {arbejde.length > 0 && (
        <>
          <button
            type="button" ref={turRef} className="rv-tur" aria-expanded={aaben}
            {...(streaming && aabenManuelt === null ? { 'data-koerer': '' } : {})}
            onClick={() => { huskFold(); setAabenManuelt(!aaben) }}
          >
            {streaming && aabenManuelt === null
              ? <span className="rv-turTekst shimmer">Working…</span>
              : <span className="rv-turTekst">{turFortalt(familier, kald, sekunder)}</span>}
            <span className="rv-turC" aria-hidden="true"><FoldPil aaben={aaben} /></span>
          </button>
          <div className="rv-gruppe" hidden={!aaben}>
            {aaben && sektioner.map((s, i) => {
              if (s.slags === 'syntese') return <Syntese key={i} tekst={s.tekst} streaming={streaming} />
              if (s.slags === 'enkelt') return <Element key={i} e={s.element} streaming={streaming} config={config} beskedId={beskedId} />
              return <Arbejdsrunde key={i} elementer={s.elementer} streaming={streaming}
                sidste={i === sektioner.length - 1} harSvar={svar.length > 0}
                config={config} rundeEtiketter={etiketter} beskedId={beskedId} />
            })}
          </div>
        </>
      )}
      {svar.length > 0 && (
        <div className="rv-svar">
          <BlocksRenderer
            blocks={svar} density="compact" streaming={streaming}
            beskedId={beskedId} config={config}
          />
        </div>
      )}
    </div>
  )
}

export const RaekkeTranskript = memo(RaekkeTranskriptImpl)
