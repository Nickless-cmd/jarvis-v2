import { isValidElement, memo, useEffect, useMemo } from 'react'
import { Globe, ListTodo } from 'lucide-react'
import ReactMarkdown, { type Components } from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import { stabilizeStreamingMarkdown } from '../../lib/streamingMarkdown'
import { enforceStructure } from '../../lib/enforceStructure'
import { stripToolEchoes } from '../../lib/stripToolEchoes'
import { delIBlokke } from '../../lib/markdownBlokke'
import { safeLinkHref } from '../../lib/sanitize'
import { isCommitHref, linkifyRefs, sideOpgaveIdFromHref } from '../../lib/linkifyRefs'
import { aabnSideOpgave } from '../../lib/sideOpgaveHighlight'
import { openExternalUrl } from '../../lib/host'
import { ChatCodeBlock } from './ChatCodeBlock'
import { MermaidBlock, MermaidStreamingContext } from './MermaidBlock'
import { NativeRichBlock, parseNativeRichSpec } from './NativeRichBlock'
import { logFlade } from '../../lib/fladeLog'

const githubMark = new URL('../../assets/github.svg', import.meta.url).href

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
const REHYPE_PLUGINS = [[rehypeKatex, { throwOnError: false, strict: false, output: 'html' }]] as const
const KOMPONENTER: Components = {
  pre: ({ children }) => {
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
      const spec = parseNativeRichSpec(code)
      logFlade({
        udfald: spec ? 'native' : 'parse-null',
        foer: '', efter: '',
        blok: code,
        className: props.className ?? '',
        lang,
        kode: code,
      })
      if (spec) return <NativeRichBlock code={code} />
    }
    return <ChatCodeBlock code={code} lang={lang} className={props.className} />
  },
  a: ({ href, children }) => {
    const safe = href ? safeLinkHref(href) : null
    if (!safe) return <span>{children}</span>
    // 25/10-2026 (Bjørn): et link skal kunne SES, ikke kun rammes. Et lille
    // globus-ikon foran gør eksterne links genkendelige på et blik — også når
    // de står som en grå kode-badge midt i en sætning, hvor blå farve ikke
    // bærer alene.
    const sideOpgave = sideOpgaveIdFromHref(safe)
    const ekstern = /^https?:/i.test(safe)
    const commit = isCommitHref(safe)
    const klasse = sideOpgave
      ? 'ref-link ref-link--sideopgave'
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
          // 27/10-2026: en side-opgave har ingen URL — den bor i et panel.
          // Klikket åbner panelet og fremhæver rækken via en CustomEvent i
          // stedet for openExternal, som ville fejle på scheme'et.
          if (sideOpgave) {
            aabnSideOpgave(sideOpgave)
            return
          }
          openExternal(safe)
        }}
      >
        {sideOpgave ? (
          <ListTodo
            size="0.85em"
            aria-hidden="true"
            className="link-todo"
          />
        ) : commit ? (
          <img src={githubMark} alt="" aria-hidden="true" className="link-github" />
        ) : ekstern ? (
          <Globe
            size="0.85em"
            aria-hidden="true"
            className="link-globe"
          />
        ) : null}
        {children}
      </a>
    )
  },
}

/** Én blok markdown. Memoiseret på strengen: en færdig blok parses én gang. */
export const MarkdownBlok = memo(function MarkdownBlok({
  md,
  streaming = false,
}: {
  md: string
  streaming?: boolean
}) {
  // 29/9-2026: en frossen blok har stabil tekst, så strukturarbejdet skal
  // følge blokkens levetid i stedet for at genkøre på hele streamets historie.
  const struktureret = useMemo(() => enforceStructure(md), [md])
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
    if (!fence) {
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
    <MermaidStreamingContext.Provider value={streaming}>
      <ReactMarkdown remarkPlugins={PLUGINS} rehypePlugins={REHYPE_PLUGINS as never} components={KOMPONENTER}>{struktureret}</ReactMarkdown>
    </MermaidStreamingContext.Provider>
  )
})

export function MarkdownRenderer({ text, streaming }: { text: string; streaming: boolean }) {
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
  const blokke = useMemo(() => (streaming ? delIBlokke(md) : null), [md, streaming])
  if (!blokke) return <MarkdownBlok md={md} />
  // Kun den SIDSTE blok er levende — de øvrige er frosne og færdige. Det er
  // samme antagelse delIBlokke selv bygger på (kun halen parses igen). Derfor
  // må et diagram i en frossen blok gerne tegnes straks, mens halen venter.
  const sidste = blokke.length - 1
  return (
    <>
      {blokke.map((b, i) => <MarkdownBlok key={i} md={b} streaming={i === sidste} />)}
    </>
  )
}

function openExternal(url: string): void { openExternalUrl(url) }
