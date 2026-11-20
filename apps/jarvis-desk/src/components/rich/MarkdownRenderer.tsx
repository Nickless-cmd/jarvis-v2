import { createContext, isValidElement, memo, useContext, useEffect, useMemo, useState } from 'react'
import { Globe, ListTodo, Bot, GitBranch, AlarmClock, Activity, FileCode } from 'lucide-react'
import ReactMarkdown, { type Components } from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import { stabilizeStreamingMarkdown } from '../../lib/streamingMarkdown'
import { enforceStructure } from '../../lib/enforceStructure'
import { stripToolEchoes } from '../../lib/stripToolEchoes'
import { delIBlokke } from '../../lib/markdownBlokke'
import { safeLinkHref } from '../../lib/sanitize'
import { isCommitHref, linkifyRefs, refKind, refVaerdi, type RefKind } from '../../lib/linkifyRefs'
import { aabnRef } from '../../lib/refAabn'
import { openExternalUrl } from '../../lib/host'
import { ChatCodeBlock } from './ChatCodeBlock'
import { MermaidBlock, MermaidStreamingContext } from './MermaidBlock'
import { NativeRichBlock, parseNativeRichSpec } from './NativeRichBlock'
import { logFlade } from '../../lib/fladeLog'
import { STREAMING_TAIL_WORD_LIMIT, rehypeStreamingTextTail } from '../../lib/streamingTextTail'

const githubMark = new URL('../../assets/github.svg', import.meta.url).href

/** Bærer `streaming` ned til `pre`-grenen.
 *
 *  30/10-2026 (Bjørn): «enten fejler fladerne ellers hænger de på flade
 *  forberedes». Placeholderen blev indført 29/10 mod at rå JSON blinkede frem
 *  under streaming — men den havde ingen udgang. På en PERSISTERET besked
 *  står den for evigt og påstår at noget er i gang, når intet er. Det er en
 *  løgn i grænsefladen, ikke en ventetilstand.
 *
 *  `MermaidStreamingContext` bærer allerede samme boolean, men navnet lyver om
 *  hvem der ejer den; en delt context med to betydninger er den slags kobling
 *  der senere knækker stille. Derfor en dedikeret. */
const FladeStreamingContext = createContext(false)

/** Render markdown sikkert. INGEN rehype-raw → rå HTML renderes aldrig
 *  (XSS-guard mod fjendtligt tool-output). Links saniteres + åbnes eksternt.
 *
 *  Strukturel håndhævelse: enforceStructure() konverterer Jarvis' uvaner
 *  (inline `## Header`, lister og tabeller mast sammen på én linje) til ægte
 *  markdown-blokke FØR ReactMarkdown ser teksten. Fede etiketter bevares.
 *
 *  remarkBreaks FJERNET (2026-06-13): den gjorde ÉT newline til <br>, hvilket
 *  forstærkede HVER parse-fejl (især malformede tabeller) til en <br>-jammet
 *  mur = "kastet ind". GLM emitterer korrekte blanklinjer, og backend-
 *  normalizeren (markdown_structure) + enforceStructure genskaber struktur for
 *  de sjældne 0-newline-tilfælde — så remarkBreaks er nu overflødig og skadelig.
 *  (Den var et band-aid mod deepseeks single-\n-afsnit; rod-årsagen løses
 *  server-side i stedet.) */
// Stabile referencer: et nyt `components`-objekt eller plugin-array ved hver
// render ville få react-markdown til at bygge alt om, også uændrede blokke.
const PLUGINS = [remarkGfm, remarkMath, linkifyRefs]
// `throwOnError: false` er ikke kosmetik: en ødelagt formel må ALDRIG vælte
// hele beskeden. KaTeX tegner så fejlen rødt i stedet, og resten af svaret
// står uændret. `strict: false` gør det samme for halvfærdige udtryk — mens
// svaret streames er `$e^{i\pi` en lovlig mellemtilstand.
const REHYPE_PLUGINS = [
  [rehypeKatex, { throwOnError: false, strict: false, output: 'html' }],
] as const
/** `pre`-grenen: kode, mermaid og flader.
 *
 *  Egen komponent fordi den kalder `useContext` — React's rules-of-hooks
 *  kræver et navn med stort begyndelsesbogstav. Lå hooken i en anonym
 *  `pre`-funktion, fejlede lint med 1 error (målt 30/10-2026), og CI kører lint.
 */
function Pre({ children }: { children?: React.ReactNode }) {
  // Hooken ligger FØR enhver betinget return. Lå den efter, ville antallet
  // af hooks skifte mellem renders og React ville rive hele beskeden ned —
  // den fejl der ser ud som om indholdet «forsvandt».
  const streaming = useContext(FladeStreamingContext)
  if (!isValidElement(children)) return <pre>{children}</pre>
  const props = children.props as { className?: string; children?: unknown }
  const code = typeof props.children === 'string' ? props.children : String(props.children ?? '')
  const lang = /^language-([^\s]+)/.exec(props.className ?? '')?.[1] ?? ''
  // 6/10-2026: ```mermaid tegnes som diagram. Blokken venter til den er
  // færdig (se MermaidStreamingContext) — en uafsluttet fence kan ikke
  // parses, og et forsøg ville skifte blokken fra kode til diagram midt i
  // turen. Alt andet går til ChatCodeBlock som før.
  if (lang === 'mermaid') return <MermaidBlock code={code} />
  if (lang === 'jarvis-ui') {
    // Klientlog (25/10-2026, side-155f2dc398): her træffes beslutningen, og
    // før blev den truffet lydløst. Fire diagnoser i træk pegede forkert,
    // fordi der ikke var ét eneste spor af hvad grenen faktisk så.
    //
    // Der logges KUN her hvor grenen faktisk blev kørt. En fejl der betyder
    // at grenen aldrig nås (`no-pre-node`) kan denne log pr. definition ikke
    // se — den fanges i MarkdownBlok nedenfor.
    const spec = parseNativeRichSpec(code, streaming)
    logFlade({
      // 14/11-2026: «native-delvis» er en flade tegnet af en HALV blok. Den
      // skal kunne skelnes i loggen — ellers ville en delvis flade se ud som
      // en komplet, og næste fejlsøgning ville lede efter den forkerte fejl.
      udfald: spec ? (streaming && !code.trim().endsWith('}') ? 'native-delvis' : 'native') : 'parse-null',
      foer: '', efter: '',
      blok: code,
      className: props.className ?? '',
      lang,
      kode: code,
    })
    const fallbackNode = (() => {
    // 29/10-2026 (Bjørn): «kode boksen der udvider sig og så blink».
    //
    // Uden denne gren faldt en ufuldstændig flade til `ChatCodeBlock`, så
    // rå JSON stod på skærmen som om det var indhold. Persisterede
    // beskeder, replay og genindlæsning går ALDRIG gennem pacerens spring,
    // så de rammer ikke den vej der ellers løser problemet — de skal have
    // en placeholder her.
    // 30/10-2026 (Bjørn): «enten fejler fladerne ellers hænger de på flade
    // forberedes». To krav stod i konflikt: rå JSON i en kodeboks er dårligt
    // (29/10), og en ventetilstand der aldrig ender er også dårligt (30/10).
    // Begge er sande, så løsningen er en TREDJE vej — ikke et kompromis
    // mellem dem:
    //
    //   streaming  → «flade forberedes…». Påstanden er SAND her: blokken er
    //                ufuldstændig og bliver til en flade om lidt.
    //   færdig     → en stille note der siger hvad der faktisk skete. Ingen
    //                spinner (intet forberedes), ingen rå JSON (den er ikke
    //                indhold). Noten er dæmpet, ikke en fejlalarm — fladen
    //                fejlede, men svaret er intet i vejen med.
    if (streaming) {
      return (
        <div className="flade-pending" aria-live="polite">
          <span className="flade-pending-tekst">flade forberedes…</span>
        </div>
      )
    }
    return (
      <div className="flade-utilgaengelig" role="note">
        <span className="flade-utilgaengelig-tekst">Fladen kunne ikke tegnes</span>
      </div>
    )
    })()
    // DIL lag 4: NativeRichBlock ejer «sidst virkende» — også når det nyeste forsøg ikke kan
    // parses. Placeholderen/noten ovenfor bruges kun hvis der aldrig var en flade.
    return <NativeRichBlock code={code} hostMessageIsStreaming={streaming} fallbackNode={fallbackNode} />
  }
  return <ChatCodeBlock code={code} lang={lang} className={props.className} />
}

/** Halen animeres af CSS alene.
 *
 *  MÅLT 18/11-2026 i Chromium: et JS-lag oven på CSS'en gav TO animationer på
 *  samme element. CSS'en er den eneste animationskilde; JS her styrer kun
 *  IDENTITET og levetid, aldrig opacity/color/transform.
 *
 *  Genstarter (MÅLT 20/11-2026): react-markdown nøgler børn `<tagName>-<antal>`.
 *  Dengang kun de tre sidste ord var pakket ind, rykkede hvert nyt ord alle
 *  tre ét trin ned, React genmonterede dem, og HVERT ord animerede op til tre
 *  gange (ord2: 3 opacity- og 3 color-starter). Nu pakker transformen alle
 *  afsluttede ord ind, så hvert ord har en stabil nøgle og en stabil node.
 *
 *  Derfor fryser komponenten sin klasse og sin rækkefølge ved første render:
 *  når ordet senere forlader «de sidste tre», må dets animation ikke kappes.
 *  Når farve-animationen (den længste) er færdig, slipper ordet klassen — og
 *  slutværdierne er identiske med almindelig tekst, så der er intet spring.
 */
type StreamingWordProps = React.HTMLAttributes<HTMLSpanElement> & {
  node?: unknown
  'data-stream-part-key'?: string
  'data-stream-tail-order'?: string | number
}

/** Rækkefølge inden for ÉT commit: ord der monteres sammen forskydes, et enkelt
 *  nyt ord starter straks (order 0) i stedet for at vente 2× forskydningen. */
let batchOrder = 0
let batchOpen = false
function naesteBatchOrder(): number {
  if (!batchOpen) {
    batchOpen = true
    batchOrder = 0
    queueMicrotask(() => { batchOpen = false })
  }
  return batchOrder++
}

function StreamingWord({ node: _node, ...props }: StreamingWordProps) {
  const erHale = typeof props.className === 'string' && props.className.includes('streaming-word-tail')
  const [frossen] = useState(() => ({
    className: props.className,
    style: props.style,
    order: erHale ? Math.min(naesteBatchOrder(), STREAMING_TAIL_WORD_LIMIT - 1) : 0,
  }))
  const [faerdig, setFaerdig] = useState(false)
  if (!erHale && !frossen.className?.includes('streaming-word-tail')) {
    return <span {...props} />
  }
  if (faerdig) return <span className="streaming-word-settled">{props.children}</span>
  return (
    <span
      {...props}
      className={frossen.className}
      data-stream-tail-order={frossen.order}
      style={{ ...frossen.style, '--streaming-tail-order': frossen.order } as React.CSSProperties}
      onAnimationEnd={(e) => { if (e.animationName === 'streaming-word-color') setFaerdig(true) }}
    />
  )
}

const KOMPONENTER = {
  // Navnet SKAL starte med stort: `useContext` kaldes indeni, og React's
  // rules-of-hooks afviser en hook i en funktion der ikke ligner en komponent.
  // Målt 30/10-2026 — lint fejlede på `pre` med 1 error, og CI kører lint.
  pre: Pre,
  'jarvis-stream-word': StreamingWord,
  a: ({ href, children }) => {
    const safe = href ? safeLinkHref(href) : null
    if (!safe) return <span>{children}</span>
    // 25/10-2026 (Bjørn): et link skal kunne SES, ikke kun rammes. Et lille
    // ikon foran gør referencer genkendelige på et blik — også når de står som
    // en grå kode-badge midt i en sætning, hvor blå farve ikke bærer alene.
    //
    // 27/10-2026 (Bjørn): ikonet valgte før kun mellem «side-opgave», «commit»
    // og «eksternt». Agent-, worktree-, wake-, run- og fil-referencer fandtes
    // ikke i den tabel, så de faldt igennem til globe-ikonet — eller til
    // ingenting. Nu afgør `refKind` både ikon, klasse og klikmål ét sted.
    const kind = refKind(safe)
    const vaerdi = kind ? refVaerdi(safe) : null
    const ekstern = /^https?:/i.test(safe)
    const commit = isCommitHref(safe)
    const klasse = kind
      ? `ref-link ref-link--${kind}`
      : commit
        ? 'ref-link ref-link--commit'
        : ekstern
          ? 'ref-link ref-link--external'
          : 'ref-link'
    return (
      <a
        href={safe}
        className={klasse}
        rel="noopener noreferrer"
        onClick={(e) => {
          e.preventDefault()
          // 27/10-2026: disse id'er har ingen URL — de bor i et panel. Klikket
          // sender en CustomEvent (se lib/refAabn.ts) i stedet for
          // openExternal, som ville fejle på det interne scheme.
          if (kind && vaerdi) {
            aabnRef(kind, vaerdi)
            return
          }
          openExternal(safe)
        }}
      >
        {ikonFor(kind, commit, ekstern)}
        {children}
      </a>
    )
  },
} as Components

/** Ikonet foran en reference. Én tabel, så et nyt id ikke kan få et tilfældigt
 *  ikon fordi nogen glemte en gren. */
function ikonFor(kind: RefKind | null, commit: boolean, ekstern: boolean) {
  switch (kind) {
    case 'sideopgave':
      return <ListTodo size="0.85em" aria-hidden="true" className="link-todo" />
    case 'agent':
      return <Bot size="0.85em" aria-hidden="true" className="link-agent" />
    case 'worktree':
      return <GitBranch size="0.85em" aria-hidden="true" className="link-worktree" />
    case 'wake':
      return <AlarmClock size="0.85em" aria-hidden="true" className="link-wake" />
    case 'run':
      return <Activity size="0.85em" aria-hidden="true" className="link-run" />
    case 'fil':
      return <FileCode size="0.85em" aria-hidden="true" className="link-fil" />
    default:
      break
  }
  if (commit) return <img src={githubMark} alt="" aria-hidden="true" className="link-github" />
  if (ekstern) return <Globe size="0.85em" aria-hidden="true" className="link-globe" />
  return null
}

/** Ulige antal ```-hegn = et hegn er stadig åbent (streaming-tilstand). */
export function harAabentHegn(tekst: string): boolean {
  return ((tekst.match(/```/g) ?? []).length % 2) === 1
}

/** Én blok markdown. Memoiseret på strengen: en færdig blok parses én gang. */
export const MarkdownBlok = memo(function MarkdownBlok({
  md,
  streaming = false,
  hale = streaming,
}: {
  md: string
  streaming?: boolean
  /** Ordhalen kører også efter streamens slutning (`HALE_AFVIKLING_MS`) — uden
   *  at fladernes streaming-kontekst gør det. Standard: følger `streaming`. */
  hale?: boolean
}) {
  // 29/9-2026: en frossen blok har stabil tekst, så strukturarbejdet skal
  // følge blokkens levetid i stedet for at genkøre på hele streamets historie.
  const struktureret = useMemo(() => enforceStructure(md), [md])
  const rehypePlugins = useMemo(
    () => (hale ? [...REHYPE_PLUGINS, [rehypeStreamingTextTail, {}]] : REHYPE_PLUGINS),
    [hale],
  )
  // De to udfald `pre`-grenen ALDRIG kan se (25/10-2026, side-155f2dc398):
  //
  //   wrong-lang  — blokken HAR en fence med jarvis-ui, men linjen er ikke
  //                 præcis «```jarvis-ui». Det er den maste form
  //                 («```jarvis-ui {json}»), hvor JSON'en lægges i
  //                 info-stringen og forsvinder — kodeblokken bliver TOM.
  //   no-pre-node — «jarvis-ui» står i teksten uden nogen fence. Blokken
  //                 bliver aldrig et <pre>, så `pre`-grenen ser den ikke.
  useEffect(() => {
    if (!struktureret.includes('jarvis-ui')) return
    const fence = struktureret
      .split('\n')
      .find((l) => l.trimStart().startsWith('```') && l.includes('jarvis-ui'))
    // Et åbent hegn er en streaming-tilstand, ikke et render-udfald: log først
    // den afsluttende tilstand (5/11-2026: 42 wrong-lang = én besked).
    if (harAabentHegn(struktureret)) return
    if (!fence) {
      // no-pre-node kræver et ægte ```jarvis-ui-hegn der bare ikke står på
      // linjestart; ren prosa-omtale af ordet er støj (39 linjer = én besked).
      if (!struktureret.includes('```jarvis-ui')) return
      logFlade({ udfald: 'no-pre-node', foer: '', efter: struktureret,
        blok: struktureret, className: '', lang: '', kode: '' })
      return
    }
    if (fence.trim() !== '```jarvis-ui') {
      logFlade({ udfald: 'wrong-lang', foer: '', efter: struktureret,
        blok: struktureret, className: '', lang: '', kode: '' })
    }
  }, [struktureret])
  return (
    <FladeStreamingContext.Provider value={streaming}>
      <MermaidStreamingContext.Provider value={streaming}>
        <ReactMarkdown remarkPlugins={PLUGINS} rehypePlugins={rehypePlugins as never} components={KOMPONENTER}>{struktureret}</ReactMarkdown>
      </MermaidStreamingContext.Provider>
    </FladeStreamingContext.Provider>
  )
})

/** Hvor længe halen får lov at løbe færdig når streamen slutter. Længere end
 *  den langsomste variants landing (Normal 426 ms), kortere end et blik. Teksten
 *  er HELE tiden fuldt synlig — dette holder intet tilbage, det afbryder bare
 *  ikke de sidste ords animation ved at skifte til færdig-render. */
export const HALE_AFVIKLING_MS = 500

export function MarkdownRenderer({ text, streaming }: { text: string; streaming: boolean }) {
  // Afvikling: streaming true→false i samme instans. Afledt tilstand under
  // render (ikke i en effekt), så der ikke nås en færdig-render imellem, som
  // ville afmontere de sidste ord midt i deres animation.
  const [forrigeStreaming, setForrigeStreaming] = useState(streaming)
  const [afvikler, setAfvikler] = useState(false)
  if (forrigeStreaming !== streaming) {
    setForrigeStreaming(streaming)
    setAfvikler(forrigeStreaming && !streaming)
  }
  useEffect(() => {
    if (!afvikler) return
    const id = setTimeout(() => setAfvikler(false), HALE_AFVIKLING_MS)
    return () => clearTimeout(id)
  }, [afvikler])
  const levende = streaming || afvikler
  const md = useMemo(() => {
    const stabilized = streaming ? stabilizeStreamingMarkdown(text) : text
    return stripToolEchoes(stabilized)
  }, [text, streaming])

  // Målepunkt 1 — «teksten før og efter stabilizeStreamingMarkdown».
  //
  // Den hører HER og ikke i den enkelte blok: `foer` er hele den rå tekst, og
  // at sende den ned som prop brød `memo` på MarkdownBlok, så frosne blokke
  // blev re-parset ved hver delta. Det blev målt som en regression af de to
  // performance-vagter i MarkdownRenderer.streaming.test.tsx — 60 grønne blev
  // 58. Effekten her kører kun når stabiliseringen FAKTISK ændrede noget i en
  // jarvis-ui-blok, så den koster intet i den normale vej.
  useEffect(() => {
    if (!streaming) return
    const stabilized = stabilizeStreamingMarkdown(text)
    if (stabilized === text) return
    // Åbent hegn = stabiliseringen lukkede det midt i streamingen; ikke et udfald.
    if (harAabentHegn(text)) return
    if (!text.includes('jarvis-ui') && !stabilized.includes('jarvis-ui')) return
    logFlade({
      udfald: 'wrong-lang',
      foer: text.slice(-2000), efter: stabilized.slice(-2000),
      blok: '', className: '', lang: '', kode: '',
    })
  }, [text, streaming])
  // Under streaming: blokke, så kun den sidste (levende) parses ved hver
  // delta (lib/markdownBlokke). Færdig tekst: ét samlet parse — det er den
  // endelige gengivelse, og blokdelingen skal aldrig kunne ændre den.
  const blokke = useMemo(() => (levende ? delIBlokke(md) : null), [md, levende])
  if (!blokke) return <MarkdownBlok md={md} />
  // Kun den SIDSTE blok er levende — de øvrige er frosne og færdige. Det er
  // samme antagelse delIBlokke selv bygger på (kun halen parses igen). Derfor
  // må et diagram i en frossen blok gerne tegnes straks, mens halen venter.
  const sidste = blokke.length - 1
  return (
    <>
      {blokke.map((b, i) => <MarkdownBlok key={i} md={b} streaming={streaming && i === sidste} hale={levende && i === sidste} />)}
    </>
  )
}

function openExternal(url: string): void { openExternalUrl(url) }
