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
 * Composer og save-rail ligger udenfor. Den tidligere separate liveness-linje
 * er siden samlet ind i den aktive arbejdsrunde.
 * Prosaen går stadig gennem `BlocksRenderer`, så markdown, kodeblokke og
 * billeder er nøjagtig som i bobblevisningen.
 */
import { memo, useEffect, useRef, useState } from 'react'
import { Sparkles, Sparkle, ChevronDown, Check, X, CircleSlash, Loader2, type LucideIcon } from 'lucide-react'
import { FoldPil, TitelCrossfade, TurHoved } from './TurHoved'
import type { ContentBlock } from '../../lib/sseProtocol'
import type { ApiConfig } from '../../lib/api'
import { CODE_FOLD_MS, codeAnswerStarted } from '../../lib/codeTurnPresentation'
import { opdel, opdelArbejdsrunder, turFortalt, type ArbejdsElement } from '../../lib/raekkeModel'
import { lookupTool } from '../../lib/toolRegistry'
import { describeTool, subjectFromInput, summarizeRound, summerDiff } from '../../lib/toolRound'
import { arbejdsTrin, trinMeta, type TrinStatus } from '../../lib/rundeTrin'
import { isMeaningfulStatus } from '../../lib/chatFlowModel'
import { diffFraResultat, diffStat } from '../../lib/diffStat'
import { postFor, kropFor } from './raekkeKroppe'
import { erUnderagent } from '../../lib/agentKald'
import { BlocksRenderer, afslutForladteKald, etiketterFraBlokke, resumeerFraBlokke } from './BlocksRenderer'
import { MarkdownRenderer } from './MarkdownRenderer'
import { useFoldPosition } from './useFoldPosition'
import { useFoldHukommelse } from '../../lib/foldHukommelse'
import { BilledArbejdeAnimation, levendeBilledArbejde } from './ImageGeneration'
import { JarvisRing } from '../shell/JarvisRing'
import { RullendeCifre, RullendeTokens, RullendeUr } from '../feedback/RullendeTal'

/** Første linje af en tanke — resten ligger i kroppen. */
function foersteLinje(s: string): string {
  const t = s.trim().split('\n').find((l) => l.trim()) ?? ''
  return t.trim()
}

/** Fold-pilen bor nu i TurHoved.tsx, så code og chat deler ÉN definition. */

/** `+N −M` på en række der har ændret en fil — KUN den side der faktisk har
 * ændringer. Bjørn 15/11-2026: «hvis den ene er 0 skal den ikk vises … hvis
 * det kun er indsættelser X+ eller hvis det er fjernelse X- … vis diffen er
 * begge dele».
 *
 * Samme regel som `ArtifactsView` bruger på artefaktlisten. Et `+0` er ikke et
 * tal om arbejdet: en række der kun slettede linjer skal ikke se ud som om den
 * også skrev nye. Er begge nul, tegnes intet — rækken handlede om noget andet,
 * og `diffFraResultat` returnerer `0/0` som et MÅLT svar (ikke som «ingen
 * data»), så det tilfælde findes i praksis.
 *
 * `git-add`/`git-del` er desks egne, pinnet af tokens.test.ts og brugt fem
 * steder i forvejen (ToolCard, ToolGroupCard, ReviewPanel, ArtifactsView). Vi
 * låner dem — rækkevisningen skal ikke have sin egen grønne og røde. */

/** Et diff-tal der ruller som uret (Bjørn 18/11-2026: «kan de gøres
 *  rullende? lige som timeren?»). Retningen følger ændringen, så hjulet
 *  ruller ned hvis tallet falder — samme regel som token-tælleren.
 *
 *  `+`/`−` står UDEN om `RullendeCifre`: de er notation, ikke tal, og
 *  `.rullende .tegn` ville male dem grå. Inde i `git-add`/`git-del` beholder
 *  de rækkens grønne/røde. Hjulene arver heller ikke farven af sig selv —
 *  `.rullende` sætter `color: var(--fg-2)`, så `raekkevisning.css` binder
 *  `.hjul-ciffer` til `--rv-tilf`/`--rv-fjern` eksplicit. */
function RullendeDiffTal({ vaerdi }: { vaerdi: number }) {
  const forrige = useRef(vaerdi)
  const retning: 'op' | 'ned' = vaerdi >= forrige.current ? 'op' : 'ned'
  useEffect(() => {
    forrige.current = vaerdi
  }, [vaerdi])
  return <RullendeCifre tekst={String(vaerdi)} retning={retning} />
}

function DiffStat({ add, del }: { add: number; del: number }) {
  if (add <= 0 && del <= 0) return null
  const linjer = (n: number) => `${n} ${n === 1 ? 'linje' : 'linjer'}`
  const label = [
    add > 0 ? `tilføjet ${linjer(add)}` : null,
    del > 0 ? `fjernet ${linjer(del)}` : null,
  ].filter(Boolean).join(', ')
  return (
    <span className="rv-diffstat" aria-label={label}>
      {add > 0 && (
        <span className="git-add">
          +<RullendeDiffTal vaerdi={add} />
        </span>
      )}
      {add > 0 && del > 0 ? ' ' : null}
      {del > 0 && (
        <span className="git-del">
          −<RullendeDiffTal vaerdi={del} />
        </span>
      )}
    </span>
  )
}

const Syntese = memo(function Syntese({ tekst, streaming, hale }: { tekst: string; streaming: boolean; hale?: boolean }) {
  return <div className="rv-mellem"><MarkdownRenderer text={tekst} streaming={streaming} hale={hale} /></div>
})

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
          <Ikon className="rv-glyf" size={13} strokeWidth={1.75} />
          <Ikon className="rv-ikon-glimt rv-glyf-glimt" size={13} strokeWidth={1.75} />
          <ChevronDown className="rv-hoverChev" size={13} strokeWidth={1.75} />
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
        {foldbar && <span className="rv-chev" aria-hidden="true"><FoldPil aaben={aaben} /><FoldPil aaben={aaben} className="rv-ikon-glimt" /></span>}
      </div>
      {foldbar && aaben && <div className="rv-krop">{krop}</div>}
    </div>
  )
}

function Element({ e, streaming, hale, config, beskedId }: {
  e: ArbejdsElement; streaming: boolean; hale?: boolean; config?: ApiConfig; beskedId?: string
}) {
  if (e.slags === 'mellemsvar') {
    // Jarvis' korte narration MELLEM kaldene. Den bor i gruppen og folder sig
    // sammen med arbejdet — den er ikke en besked (Bjoern 22/9-2026).
    return <Syntese tekst={e.tekst} streaming={streaming} hale={hale} />
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
    const sum = ds ? <>{emne} <DiffStat add={ds.add} del={ds.del} /></> : emne
    return (
      <Raekke
        Ikon={meta.Icon} slags={etiket}
        sum={sum}
        koerer={streaming && b.status === 'running'}
        fejl={fejl}
        krop={kropFor(b.name, b.input, b.result, fejl, config,
          {
            partialJson: b.partialJson,
            running: streaming && b.result == null && (b.status ?? 'running') === 'running',
            output: b.liveOutput,
            truncated: b.liveOutputTruncated,
          },
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

/** Arbejdsrundernes skjulte kroppe bliver stående i DOM'en. Under streaming
 *  kommer der nye blok-arrays ved hvert delta, men færdige blok-objekter er
 *  stabile. Spring deres dyre kort-render over, når indholdet er det samme. */
function sammeArbejdsElementer(a: ArbejdsElement[], b: ArbejdsElement[]): boolean {
  if (a.length !== b.length) return false
  for (let i = 0; i < a.length; i++) {
    const x = a[i]!
    const y = b[i]!
    if (x.slags !== y.slags) return false
    if (x.slags === 'blok' && y.slags === 'blok' && x.blok !== y.blok) return false
    if (x.slags === 'mellemsvar' && y.slags === 'mellemsvar' && x.tekst !== y.tekst) return false
    if (x.slags === 'spor' && y.slags === 'spor'
      && (x.trin.length !== y.trin.length || x.trin.some((t, j) => t !== y.trin[j]))) return false
  }
  return true
}

const Arbejdsdetaljer = memo(function Arbejdsdetaljer({ elementer, aaben, streaming, hale, config, beskedId }: {
  elementer: ArbejdsElement[]
  aaben: boolean
  streaming: boolean
  hale?: boolean
  config?: ApiConfig
  beskedId?: string
}) {
  return (
    <div className="rv-arbejdsdetaljer" hidden={!aaben}>
      {elementer.map((e, i) => <Element key={i} e={e} streaming={streaming} hale={hale} config={config} beskedId={beskedId} />)}
    </div>
  )
}, (a, b) => a.aaben === b.aaben && a.streaming === b.streaming && a.hale === b.hale
  && a.config === b.config && a.beskedId === b.beskedId
  && sammeArbejdsElementer(a.elementer, b.elementer))

/** Et trin i rundens arbejdsliste. Glyffen er STATUS, ikke dekoration: et
 *  hak betyder «kaldet svarede», et kryds «det fejlede», den skrå streg
 *  «det fik aldrig et svar». Den kørende række beholder rundens egen ring
 *  som aktivitetseffekt — spinneren her er samme `.spin` som resten af huset
 *  bruger, så der ikke kommer en ny animation ind i sproget. */
function TrinGlyf({ status }: { status: TrinStatus }) {
  if (status === 'done') return <Check size={12} strokeWidth={2.5} />
  if (status === 'failed') return <X size={12} strokeWidth={2.5} />
  if (status === 'afbrudt') return <CircleSlash size={12} strokeWidth={2} />
  return <Loader2 size={12} strokeWidth={2.5} className="spin" />
}

function ArbejdsrundeImpl({
  elementer, streaming, hale, sidste, config, etiket, beskedId, turSekunder, skjult = false, workingStep,
}: {
  workingStep?: string | null
  elementer: ArbejdsElement[]
  streaming: boolean
  hale?: boolean
  sidste: boolean
  config?: ApiConfig
  beskedId?: string
  etiket?: string
  turSekunder?: number | null
  skjult?: boolean
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
  //
  // 3/10-2026 (Bjørn): «i runde linjerne … skal shimmer fortsætte til første
  // tænke i næste runde, ellers opstår der et par sekunders stilhed hvor du
  // tænker». Fejlen var `harSvar`: den tæller ALT efter sidste værktøjskald som
  // «svar» — også rundeopsummeringen (`tool_use_summary`), som lander lige når
  // værktøjet er færdigt. Derfor døde shimmeren i præcis det vindue hvor
  // modellen tænker på næste runde, og rækken stod død i et par sekunder.
  // Puls, det samlede tur-ur og ét fælles shimmerfelt bliver derfor på den
  // sidste aktive runde helt til stream-stop.
  const aktivRunde = streaming && sidste
  const mekanisk = summarizeRound(vaerktoejer)
  // Under udførelse: Jarvis' `description` eller den aktuelle handling.
  // Bagefter: modelens rundeopsummering, ellers en faktuel afslutning.
  //
  // Bjørn 24/9-2026: «det er bare <færdig> der ikk passer ind». Linjen bar før
  // et «Færdig · »-præfiks foran den mekaniske tekst, sat ind for at skelne en
  // afsluttet runde fra en kørende. Ordet var et fremmedelement i en linje der
  // ellers er ren handling — og skelnen findes allerede i shimmeren.
  //
  // Levende kilde (side-2974014f15): serverens `working_step`, når den er
  // meningsfuld — samme vagt som chat mode, så `operator_bash` ikke blinker
  // frem. `workingStep` er global (nyeste), men kun den aktive runde får den
  // (`sidste`), og kun mens dens seneste kald kører.
  const levendeStep = koerer && sidste ? (workingStep ?? '').replace(/\s+/g, ' ').trim() : ''
  const beskrivelse = koerer && seneste
    ? (levendeStep && isMeaningfulStatus(levendeStep) ? levendeStep : describeTool(seneste.name, seneste.input, true, seneste.partialJson, seneste.result, seneste.status))
    : etiket || mekanisk
  // ── Arbejdstrinnene (Bjørn 15/11-2026) ──────────────────────────────────
  // Den AKTIVE runde viser processen, den AFSLUTTEDE viser resultatet.
  // Trinnene udledes af rundens egne `tool_use`-blokke (`lib/rundeTrin.ts`),
  // så et trin kun kan stå der hvis serveren faktisk sendte kaldet.
  const trin = arbejdsTrin(elementer, aktivRunde)
  // ── Højden må ikke springe når runden forlades (målt 27/11-2026) ────────
  //
  // `arbejdsTrin(elementer, aktivRunde)` giver en TOM liste i samme frame som
  // runden holder op med at være aktiv. Målt i Chromium: linjen faldt 74px →
  // 38px — 36px, som er trinlistens højde — mens resten af huset bevæger sig
  // over `--dur-fold`. Naboen (slutbeskeden) rykkede derfor 36px op i én
  // frame, og det så ud som om faden tog den med.
  //
  // Listen holdes derfor i live i præcis `--dur-fold` efter runden er forladt,
  // så wrapperen kan kollapse den animeret. Den er `aria-hidden` i det vindue:
  // den er visuel overgang, ikke indhold man kan læse som en kørende proces.
  const forladtTrin = useRef<typeof trin>([])
  const [trinHolder, setTrinHolder] = useState(false)
  useEffect(() => {
    if (aktivRunde) {
      forladtTrin.current = []
      setTrinHolder(false)
      return
    }
    if (forladtTrin.current.length === 0) return
    setTrinHolder(true)
    const t = window.setTimeout(() => { forladtTrin.current = []; setTrinHolder(false) }, 400)
    return () => window.clearTimeout(t)
  }, [aktivRunde])
  if (aktivRunde && trin.length > 0) forladtTrin.current = trin
  const visteTrin = aktivRunde ? trin : (trinHolder ? forladtTrin.current : [])
  // Overskriften ER det kørende trin når serveren ikke har sin egen
  // arbejdsbeskrivelse (`working_step`). Så må den ikke stå to gange: linjen
  // bærer den — med ring og shimmer — og listen viser historikken op til den.
  // Kun ved `active`: et FEJLET enkelt-kald må ikke forsvinde ind i
  // overskriften, for så ville krydset forsvinde sammen med det.
  const sidsteTrin = trin[trin.length - 1]
  const overskriftErSidste = Boolean(
    sidsteTrin && sidsteTrin.status === 'active' && sidsteTrin.tekst === beskrivelse,
  )
  const synligeTrin = overskriftErSidste ? visteTrin.slice(0, -1) : visteTrin
  // Kun det man ikke kan se af sig selv: at noget fejlede eller aldrig fik et
  // svar. Antallet og «Fold ud» stod her før, men pilen viser allerede at
  // rækken kan foldes, og tallet sagde intet om udfaldet (Bjørn 15/11-2026).
  const advarsel = aktivRunde ? '' : trinMeta(trin)
  return (
    <div className="rv-arbejdsrunde"
      {...(aktivRunde ? { 'data-aktiv-runde': '', 'data-pacing-skjult': skjult ? '' : undefined } : {})}
      {...(!aktivRunde && trin.some((t) => t.status === 'failed') ? { 'data-fejl': '' } : {})}
      aria-hidden={aktivRunde && skjult ? true : undefined}>
      <button type="button" ref={foldRef} className="rv-arbejdsknap" aria-expanded={aaben}
        {...(aktivRunde ? { 'data-koerer': '' } : {})}
        onClick={() => { huskFold(); setAaben((v) => !v) }}>
        {/* Kun den AKTIVE runde bærer et ikon (Bjørn 15/11-2026: «fjern
            iconerne foran de færdige rundelinjer men ikk den aktive»).
            Den færdige runde er ren tekst — dens form er allerede fortalt i
            ordene, og et værktøjsikon foran hver afsluttet linje gjorde
            kolonnen urolig uden at tilføje noget man kunne handle på. */}
        {aktivRunde && (
          <span className="rv-arbejdsikon" aria-hidden="true">
            <JarvisRing size={15} spinning tone="working" />
          </span>
        )}
        <span className={`rv-arbejdsindhold${aktivRunde ? ' shimmer' : ''}`}>
          {aktivRunde
            ? <TitelCrossfade tekst={beskrivelse} aktiv className="rv-arbejdsfortaelling" />
            : <span className="rv-arbejdsfortaelling">{beskrivelse}</span>}
          {diff && <DiffStat add={diff.add} del={diff.del} />}
          {aktivRunde && typeof turSekunder === 'number'
            ? <span className="rv-rundeur"><RullendeUr sek={turSekunder} /></span>
            : null}
          {/* Niveau 2: kun det udfald man ikke kan se af sig selv. Den
              afsluttede runde bærer sin syntese; fejl og kald uden svar får
              et ord med på vejen. */}
          {advarsel
            ? <span className="rv-arbejdsmeta">{advarsel}</span>
            : null}
        </span>
        <span className="rv-turC" aria-hidden="true"><FoldPil aaben={aaben} /><FoldPil aaben={aaben} className="rv-ikon-glimt" /></span>
      </button>
      {/* Niveau 1: den aktive rundes proces. Ligger UDEN for knappen, så
          trinnene ikke er klikbare som en del af folden — de er indhold man
          læser, ikke en affordance. Hver række er nøglet på kaldets id, så en
          statusændring opdaterer glyffen i stedet for at genopbygge listen
          (kravet om at indholdet ikke hopper, Bjørn 15/11-2026). */}
      {/* Niveau 1: den aktive rundes proces. Ligger UDEN for knappen, så
          trinnene ikke er klikbare som en del af folden — de er indhold man
          læser, ikke en affordance. Hver række er nøglet på kaldets id, så en
          statusændring opdaterer glyffen i stedet for at genopbygge listen
          (kravet om at indholdet ikke hopper, Bjørn 15/11-2026).

          WRAPPEREN ER NY (27/11-2026). Målt i Chromium: da runden holdt op med
          at være aktiv, faldt den fra 74px til 38px — 36px, som er præcis
          trinlistens højde — i ÉN frame, mens resten af huset bevæger sig over
          `--dur-fold`. Naboen (slutbeskeden) rykkede derfor 36px op, og det så
          ud som om faden tog den med. Nu bliver listen stående i DOM'en og
          wrapperen animerer `1fr → 0fr`, så højden glider med foldens egen
          varighed. Samme mønster som `.chat-flow-runde`; `align-self: start`
          og `min-height: 0` er ikke kosmetik — se chat-flow.css. */}
      <div className="rv-trin-ydre" data-aaben={aktivRunde && synligeTrin.length > 0 ? 'true' : 'false'}>
        <div className="rv-trin-indre">
          {synligeTrin.length > 0 && (
            <ol className="rv-trin" aria-label="Arbejdstrin" aria-hidden={aktivRunde ? undefined : true}>
              {synligeTrin.map((t) => (
                <li key={t.id} className="rv-trinRaekke" data-status={t.status}>
                  <span className="rv-trinGlyf" aria-hidden="true"><TrinGlyf status={t.status} /></span>
                  <span className="rv-trinTekst">{t.tekst}</span>
                  {t.note ? <span className="rv-trinNote">{t.note}</span> : null}
                </li>
              ))}
            </ol>
          )}
        </div>
      </div>
      <Arbejdsdetaljer elementer={elementer} aaben={aaben} streaming={streaming} hale={hale} config={config} beskedId={beskedId} />
    </div>
  )
}

const Arbejdsrunde = memo(ArbejdsrundeImpl, (a, b) =>
  a.streaming === b.streaming && a.hale === b.hale && a.sidste === b.sidste
  && a.turSekunder === b.turSekunder
  && a.skjult === b.skjult && a.workingStep === b.workingStep
  && a.config === b.config && a.beskedId === b.beskedId && a.etiket === b.etiket
  && sammeArbejdsElementer(a.elementer, b.elementer))

/** Shared round-line view inside a turn's work fold. */
export function Arbejdsforloeb({ blocks, streaming, config, beskedId, rundeEtiketter = {} }: {
  blocks: ContentBlock[]; streaming: boolean; config?: ApiConfig; beskedId?: string
  rundeEtiketter?: Record<string, string>
}) {
  const labels = { ...etiketterFraBlokke(blocks), ...rundeEtiketter }
  const thoughts = resumeerFraBlokke(blocks)
  const usedThoughts = new Set<string>()
  const work = blocks.flatMap((b): ContentBlock[] => {
    if (b.type === 'tool_use_summary') return []
    if (b.type === 'text') return [{ ...b, phase: 'commentary', code_answer_protocol: 1, code_answer_start: false }]
    const thought = b.type === 'tool_use' ? thoughts[b.id] : undefined
    if (!thought || usedThoughts.has(thought)) return [b]
    usedThoughts.add(thought)
    return [{ type: 'thinking', thinking: thought }, b]
  })
  const sections = opdelArbejdsrunder(opdel(work, true).arbejde)
  return <>{sections.map((section, index) => {
    if (section.slags === 'syntese') return <Syntese key={`s${index}`} tekst={section.tekst} streaming={streaming} />
    if (section.slags === 'enkelt') return <Element key={`e${index}`} e={section.element}
      streaming={streaming} config={config} beskedId={beskedId} />
    return <Arbejdsrunde key={noegleForRunde(section.elementer) ?? index}
      elementer={section.elementer} streaming={streaming} sidste={index === sections.length - 1}
      config={config} beskedId={beskedId} etiket={etiketFor(section.elementer, labels)} />
  })}</>
}

function etiketFor(elementer: ArbejdsElement[], etiketter: Record<string, string>): string | undefined {
  for (let i = elementer.length - 1; i >= 0; i--) {
    const e = elementer[i]
    if (e?.slags === 'blok' && e.blok.type === 'tool_use' && etiketter[e.blok.id]) return etiketter[e.blok.id]
  }
  return undefined
}

function noegleForRunde(elementer: ArbejdsElement[]): string | undefined {
  for (const e of elementer) {
    if (e.slags === 'blok' && e.blok.type === 'tool_use') return `runde:${e.blok.id}`
  }
  return undefined
}

function RaekkeTranskriptImpl({
  blocks, streaming, finalAnswerStarted = false, svarRuller, arbejdeEfterSvar = false, beskedId, runId, turId, config, rundeEtiketter,
  elapsedMs = 0, tokens = 0, varighedSekunder = null,
  skjulAktivRunde = false, workingStep,
}: {
  /** Serverens nyeste `working_step` — levende kilde til den aktive rundelinje. */
  workingStep?: string | null
  blocks: ContentBlock[]
  streaming: boolean
  finalAnswerStarted?: boolean
  /** Ruller svaret stadig? Sand til det sidste tegn er vist — ogsaa efter
   *  `message_stop`, hvor paceren indhenter resten. Sene runder venter her. */
  svarRuller?: boolean
  /** Der er kommet arbejde efter svar-låsen; hovedet forbliver foldet. */
  arbejdeEfterSvar?: boolean
  beskedId?: string
  /** Run'et der skrev beskeden. Sammen med `beskedId` den nøgle folden huskes
   *  på, så den overlever overgangen live → persisteret besked. */
  runId?: string | null
  turId?: string | null
  config?: ApiConfig
  rundeEtiketter?: Record<string, string>
  elapsedMs?: number
  tokens?: number
  varighedSekunder?: number | null
  skjulAktivRunde?: boolean
}) {
  // `pause_and_ask` er en besked til brugeren, ikke skjult arbejdsdiagnostik.
  // Hold den derfor ude af arbejdsfolden og stående i transkriptet, mens resten
  // af værktøjssporet stadig kan foldes sammen.
  const inlineQuestions = blocks.filter((blok) => blok.type === 'tool_use' && blok.name === 'pause_and_ask')
  const transcriptBlocks = inlineQuestions.length > 0
    ? blocks.filter((blok) => !(blok.type === 'tool_use' && blok.name === 'pause_and_ask'))
    : blocks
  const declaredProtocol = transcriptBlocks.some((b) => b.type === 'text' && b.code_answer_protocol === 1)
  const effectiveAnswerStarted = declaredProtocol ? codeAnswerStarted(transcriptBlocks) : finalAnswerStarted
  // Kald uden svar bærer `status: 'running'` videre fra `foldToolResults`, og
  // `arbejdsTrin` gør dem til «afbrudt» når runden ikke længere er aktiv.
  // `afslutForladteKald` må IKKE bruges her: den stempler et kald som «done» så
  // snart der kommer tekst efter det, fordi den læser tekst som «svaret er
  // begyndt». For en rundelinje er det forkert — kaldet kan stadig køre, og
  // «Læser app.ts» blev til «Læste app.ts» (målt 15/11-2026).
  // `effectiveAnswerStarted` sendes ogsaa som SVAR-LAAS: naar serveren har
  // bekræftet at svaret er begyndt, maa et senere vaerktoejskald ikke flytte
  // skillelinjen og goere slutteksten til arbejde (målt 21/11-2026).
  const { arbejde: oprindeligtArbejde, svar, svarSektioner, kald } = opdel(transcriptBlocks, streaming && !effectiveAnswerStarted, effectiveAnswerStarted)
  const svarSamles = !streaming && !(svarRuller ?? false)
  // Text always stays in the answer lane. Only work rows collapse; their
  // details remain available behind the head after the turn.
  const arbejde = svarSamles
    ? [...oprindeligtArbejde, ...svarSektioner.flatMap((s) => s.slags === 'runde' ? s.elementer : [])]
    : oprindeligtArbejde
  const billedArbejde = streaming
    ? levendeBilledArbejde(afslutForladteKald(blocks, true).flatMap((b) => b.type === 'tool_use' ? [b] : []))
    : null
  const sektioner = opdelArbejdsrunder(arbejde)
  // Kun en runde der faktisk er sidste sektion ejer den levende bundplads.
  // Når dens syntese lander bagefter, bliver runden stående historisk foran
  // syntesen i stedet for at blive løftet ned under den.
  let sidsteRundeIndex = -1
  for (let i = 0; i < sektioner.length; i++) {
    if (sektioner[i]?.slags === 'runde') sidsteRundeIndex = i
  }
  const aktivRundeIndex = streaming
    ? sidsteRundeIndex
    : -1
  // Den aktive runde efter foldet. Bjørn 27/11-2026: «runderne og den aktive
  // runde linje skal forsætte udenfor foldet» — også den der kører lige nu.
  // Den skal have samme levende markering som den aktive runde inde i folden,
  // ellers står en kørende runde død uden for hovedet.
  let sidsteSvarRundeIndex = -1
  for (let i = 0; i < svarSektioner.length; i++) {
    if (svarSektioner[i]?.slags === 'runde') sidsteSvarRundeIndex = i
  }
  const aktivSvarRundeIndex = streaming ? sidsteSvarRundeIndex : -1
  // Familien pr. kald — SAMME kilde som kroppene (`postFor`), så turens
  // hoved og rækkerne aldrig kan fortælle to forskellige historier.
  const familier = arbejde.flatMap((e) =>
    e.slags === 'blok' && e.blok.type === 'tool_use' ? [postFor(e.blok.name).familie] : [],
  )
  const etiketter = { ...etiketterFraBlokke(blocks), ...(rundeEtiketter ?? {}) }
  // Fold først ved serverens bekræftede grænse, før det første svar-delta.
  // En mellemsyntese må aldrig få headeren til at hoppe ind og ud.
  // Folden huskes på beskedens identitet, ikke på komponentinstansen. Målt
  // 30/10-2026 (`foldRemount.maaling.test.tsx`): et remount nulstillede den —
  // og overgangen live → persisteret ER et remount. `runId` er den fælles
  // nøgle: den levende række har `activeRunId`, den persisterede besked bærer
  // samme id i `run_id`. Uden nøgle opfører den sig som før (rent lokal state).
  const [aabenManuelt, setAabenManuelt] = useFoldHukommelse(runId ?? beskedId, turId)
  const svarRullerAktiv = svarRuller ?? (streaming && (!effectiveAnswerStarted || arbejdeEfterSvar))
  const arbejdeKoerer = arbejdeEfterSvar || svarRullerAktiv
  // Ordhalen skal leve mens TEKSTEN ruller — ikke mens SSE-socket'en er aaben.
  // MÅLT 20/11-2026 (Bjørn: «Kan det passe farven forsvinder fra ord
  // animationen efter hoveds fold?»): `MarkdownRenderer` fik kun `streaming`,
  // som bliver falsk ved `message_stop`, mens paceren stadig indhentede de
  // sidste ord. `svarRuller` er sand til det sidste tegn er vist.
  const hale = svarRuller ?? streaming
  // ── Folden lukker naar SVARET FINDES, ikke naar det er faerdigt ──────────
  //
  // VENDT 21/11-2026 (Bjørn: «Hoved folder foerst naar beskeden er faerdig..
  // Det skal ske naar slutbeskeden fortsaetter? Hvad goer GPT?»). Svar: GPT
  // afleder `completed` af om der FINDES assistent-indhold — ikke af om
  // streamen er slut. Deres hoved folder altsaa i det oejeblik svaret begynder,
  // og teksten ruller videre inde i det feredige hoved.
  //
  // Den gamle regel bandt folden til `svarRuller` (sand til sidste tegn), saa
  // arbejdet blev revet vaek i praecis den frame teksten landede — oejets hop.
  // `svarLaas` i `opdel` goer at teksten bliver i `svar` naar den foerst er
  // begyndt, saa der ER et svar at folde om; den tomme flade fra 20/11 kan
  // derfor ikke opstaa her.
  //
  // `arbejdeEfterSvar` er daekket: naar et nyt run arbejder efter svaret, er
  // `svarBegyndt` stadig sand — folden bliver lukket, og hovedet bliver
  // turens ansigt. Det var netop fejlen 20/11 at den sprang OP i stedet.
  const explicitProtocol = declaredProtocol
  const svarBegyndt = effectiveAnswerStarted || codeAnswerStarted(transcriptBlocks)
    || (!explicitProtocol && svar.some((b) => b.type === 'text' ? b.text.trim().length > 0
      : b.type === 'image' || b.type === 'file' || b.type === 'video'))
  const aaben = aabenManuelt ?? (arbejdeKoerer && !svarBegyndt)
  // ── Folden skal GLIDE, ikke blinke (målt 21/11-2026) ────────────────────
  //
  // Bjørn: «så skal foldet bar matche ord animationen.. lige nu sker foldet i
  // et blink». Folden blev fjernet med `hidden` — `display: none` i ÉN frame —
  // så der var ingen højde at animere fra, og billedet rykked sammen med
  // præcis linjernes højde. Samme fejl som chat mode målte 20/10-2026, og
  // løsningen er den samme: rammen bliver i layoutet og glider `1fr → 0fr`.
  //
  // Indholdet må heller ikke forsvinde i samme frame som rammen begynder at
  // glide. Uden børn er der intet at animere, og folden bliver et hop igen —
  // så det bliver stående `FOLD_MS` efter folden er lukket.
  //
  // Hvorfor ikke bare lade det stå altid? Fordi skjulte runder ikke må fylde
  // DOM'en i en lang gemt samtale (målt 22/9-2026, se `monterer først
  // rækkerne`). Forsinkelsen er præcis så lang som folden varer.
  //
  // 379 ms = `--dur-fold` i `styles/tokens.css`, som er ord-animationens
  // samlede landing for `Snappy` (220 + 99 + 2×30 i `lib/streamingTextTail.ts`).
  // To tal for samme varighed er en kendt pris: CSS kan ikke læse en TS-konstant,
  // og en transition kan ikke vente på en tilstand. Ændres den ene, skal den
  // anden følge med — derfor står udregningen begge steder.
  const [indholdVises, setIndholdVises] = useState(aaben)
  useEffect(() => {
    if (aaben) { setIndholdVises(true); return }
    const t = setTimeout(() => setIndholdVises(false), CODE_FOLD_MS)
    return () => clearTimeout(t)
  }, [aaben])
  const turSekunder = streaming ? Math.max(0, Math.floor(elapsedMs / 1000)) : varighedSekunder
  // Invarianten: hovedet er turens resultat og dens fold-knap. Paa en FÆRDIG
  // tur findes det altid — ogsaa naar folden staar aaben, for det er hovedet
  // man folder sammen med. Mens arbejdet koerer, er rundelinjen turens ansigt,
  // og hovedet vises kun hvis folden er lukket (saa det er det eneste ansigt).
  // Den formel daekker begge: der findes ingen tilstand hvor arbejdet er
  // skjult OG hovedet vaek — det var den tomme flade.
  // Before the first model content, the animated mark carries liveness.
  // It is not a work round and must not duplicate the first real round.
  const venterPaaModel = streaming && !effectiveAnswerStarted && !arbejdeEfterSvar
    && !transcriptBlocks.some((block) =>
    block.type === 'text' ? block.text.trim().length > 0
      : block.type === 'thinking' ? block.thinking.trim().length > 0
        : block.type === 'tool_use')
  const visTurhoved =
    (arbejde.length > 0 && (!arbejdeKoerer || !aaben))
    || (arbejde.length === 0 && arbejdeKoerer)
  // Tokenfeltet eksisterer først når tælleren faktisk er begyndt. Dermed står
  // der hverken `0 tokens` eller et ensomt `k tokens` ved turstart.
  //
  // Ikke bundet til `streaming` (15/11-2026): hovedet er turens RESULTAT og
  // findes først når folden lukker — netop dér hvor `streaming` kan være
  // falsk. Bandt vi tallet til streamen, ville resultatet mangle sit eget
  // resultat i den fase det ejer. Samme regel som chat mode.
  const visTokens = Number.isFinite(tokens) && tokens > 0
  const turRef = useRef<HTMLButtonElement>(null)
  const huskFold = useFoldPosition(turRef, aaben)

  return (
    <div className="raekkevisning">
      {venterPaaModel ? (
        <div className="rv-modelventer" role="status" aria-label="Jarvis tænker">
          <JarvisRing size={15} spinning tone="working" />
        </div>
      ) : null}
      {visTurhoved && !venterPaaModel && (
        <TurHoved
          knapRef={turRef}
          aaben={aaben}
          koerer={arbejdeKoerer}
          tekst={streaming ? 'Arbejder' : turFortalt(familier, kald, 0)}
          meta={visTokens ? <span className="rv-turMeta">~<RullendeTokens tokens={tokens} /> output</span> : null}
          levende={streaming}
          sekunder={!streaming ? turSekunder : null}
          foldbar={arbejde.length > 0}
          onToggle={() => { huskFold(); setAabenManuelt(!aaben) }}
        />
      )}
      {/* Arbejdsgruppen har sin EGEN gate — ikke hovedets.
          Lå den inde i hovedets fragment, forsvandt arbejdet sammen med det
          hoved det skulle overlevere til, i præcis det øjeblik hovedet blev
          usynligt. Chat mode målte den fejl 14/11-2026 (`.rv-tur` var barn af
          samme gren); code mode arvede den og får samme split her. */}
      {/* Her stod en ventende rundelinje før det første værktøjskald. Den er
          fjernet (Bjørn 27/11-2026): den viste den første rundes tekst uden
          for folden, mens de rigtige rundelinjer står inde i den. Turen har
          ét ansigt uden for folden — hovedet ovenfor — og det bærer turen fra
          første frame via `visTurhoved`. */}
      {arbejde.length > 0 && !venterPaaModel && (
        <div className="rv-gruppe-ydre" data-aaben={aaben ? 'true' : 'false'}
          {...(aaben ? {} : { inert: true })}>
          <div className="rv-gruppe" aria-hidden={!aaben}>
              {indholdVises && sektioner.map((s, i) => {
                if (s.slags === 'syntese') return <Syntese key={i} tekst={s.tekst} streaming={streaming} hale={hale} />
                if (s.slags === 'enkelt') return <Element key={i} e={s.element} streaming={streaming} hale={hale} config={config} beskedId={beskedId} />
                const aktiv = i === aktivRundeIndex
                return <Arbejdsrunde key={noegleForRunde(s.elementer) ?? i}
                  elementer={s.elementer} streaming={streaming} hale={hale} sidste={aktiv}
                  config={config} etiket={etiketFor(s.elementer, etiketter)} beskedId={beskedId}
                  turSekunder={turSekunder} skjult={aktiv && skjulAktivRunde}
                  workingStep={aktiv ? workingStep : undefined} />
              })}
          </div>
        </div>
      )}
      {billedArbejde ? <BilledArbejdeAnimation arbejde={billedArbejde} config={config} /> : null}
      {inlineQuestions.length > 0 ? (
        <div className="rv-inline-question">
          <BlocksRenderer
            blocks={inlineQuestions} density="compact" streaming={streaming} hale={hale}
            beskedId={beskedId} config={config}
          />
        </div>
      ) : null}
      {/* Svar-containeren findes fra FØRSTE frame (målt 19/10-2026).
          FØR: den var betinget af `svar.length > 0`, så den opstod i samme
          øjeblik grænsen faldt — og slutsvarets node fik dermed både ny
          container og ny forælder på én gang (målt: `.rv-svar` = 0 før,
          1 efter). En container der allerede står der kan ikke poppe ind.
          Den er tom indtil det første svar-delta, og `:not(:empty)` i CSS'en
          holder marginen væk så længe. */}
      <div className="rv-svar">
        {svarSektioner.map((s, i) => {
          if (s.slags === 'blokke') {
            return (
              <div key={`b${i}`} className="rv-svar-tekst">
                <BlocksRenderer blocks={s.blokke} density="compact" streaming={streaming} hale={hale}
                  beskedId={beskedId} config={config} />
              </div>
            )
          }
          // Runden EFTER foldet tegnes med den SAMME komponent som runderne inde
          // i folden (Bjørn 27/11-2026: «det er runderne efter foldet der skal
          // være lige som dem ingen i»). Faldt den i `svar`, tog
          // `BlocksRenderer`s bobble-sprog den — fast `</>`-ikon, ur, og
          // tænkningen som sin EGEN linje ved siden af. To sprog for den samme
          // ting; nu er der ét.
          const aktiv = streaming && i === aktivSvarRundeIndex
          return (
            <div key={`r${i}`} className="rv-sen-runde" data-samles={svarSamles ? 'true' : 'false'}
              aria-hidden={svarSamles} {...(svarSamles ? { inert: true } : {})}>
              <div className="rv-sen-runde-indhold">
                <Arbejdsrunde
                  elementer={s.elementer} streaming={streaming} hale={hale} sidste={aktiv}
                  config={config} etiket={etiketFor(s.elementer, etiketter)} beskedId={beskedId}
                  turSekunder={turSekunder} skjult={aktiv && skjulAktivRunde}
                  workingStep={aktiv ? workingStep : undefined} />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export const RaekkeTranskript = memo(RaekkeTranskriptImpl)
