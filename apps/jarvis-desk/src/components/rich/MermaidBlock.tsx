import { createContext, useContext, useEffect, useState } from 'react'
import { CodeBlock } from './CodeBlock'

/** Bærer «er denne blok stadig levende?» ned til diagrammet.
 *
 *  Context og ikke en prop, fordi `KOMPONENTER` i MarkdownRenderer er en
 *  modul-konstant med vilje: et nyt `components`-objekt ved hver render ville
 *  få react-markdown til at bygge hele træet om, også de frosne blokke. En
 *  context lader objektet stå stille mens værdien følger med ned. */
export const MermaidStreamingContext = createContext(false)

/** Mermaid er ~4 MB. Den loades først når et diagram faktisk skal tegnes —
 *  ellers betaler hver desk-opstart for et bibliotek de fleste svar ikke rører. */
let mermaidModul: Promise<typeof import('mermaid')> | null = null

function hentMermaid(): Promise<typeof import('mermaid')> {
  if (!mermaidModul) {
    mermaidModul = import('mermaid').then((m) => {
      m.default.initialize({
        startOnLoad: false,
        theme: 'dark',
        // Vi indsætter mermaid's EGEN SVG med dangerouslySetInnerHTML.
        // strict saniterer labels/klik-handlere i det output, så en
        // fjendtlig diagram-titel ikke bliver en script-vektor.
        securityLevel: 'strict',
      })
      return m
    })
  }
  return mermaidModul
}

/** Mermaid lægger loopende CSS-animationer i sit output (kant-flow, puls).
 *  De kører for evigt og stjæler opmærksomhed i en samtale der står stille.
 *
 *  **Reglen SKAL scopes til diagrammets eget id.** En `<style>` inde i et
 *  INLINE svg er ikke scopet til svg'en — den er et dokument-niveau stylesheet
 *  som alle andre. Et bart `* { animation: none !important }` dér slog derfor
 *  hver animation og transition i HELE desk ud, og `!important` gjorde den
 *  uovervindelig. Bjørn så det med det samme på 0.6.202: «desk animationer er
 *  stuck dem alle sammen på det nye build». Fejlen var usynlig i test, fordi
 *  ingen test renderer et diagram OG en animation i samme dokument.
 *
 *  `id` er `mermaid-<base36>` og dermed en gyldig CSS-identifikator. */
function udenAnimation(svg: string, id: string): string {
  return svg.replace(
    /(<style[^>]*>)/,
    `$1#${id} * { animation: none !important; transition: none !important; }`,
  )
}

/** Modul-niveau: overlever StrictMode's dobbelt-mount og remounts uden flicker.
 *  Værdi `null` = «denne kilde kan ikke parses» — så prøver vi ikke igen. */
const svgCache = new Map<string, string | null>()

function erFejlet(code: string): boolean {
  return svgCache.has(code) && svgCache.get(code) === null
}

/** Mermaid-diagram, lazy-loaded og kun tegnet når blokken er færdig.
 *
 *  Under streaming vises en placeholder i stedet for et halvt diagram: en
 *  uafsluttet fence kan ikke parses, og et forsøg ville skifte blokken fra
 *  kode til diagram midt i turen. Kan kilden ikke parses, falder vi tilbage
 *  til en rå kodeblok — et dårligt diagram bliver kode, ikke en tom rude. */
export function MermaidBlock({ code }: { code: string }) {
  const streaming = useContext(MermaidStreamingContext)
  const [svg, setSvg] = useState<string | null>(() => svgCache.get(code) ?? null)
  const [fejlet, setFejlet] = useState(() => erFejlet(code))

  useEffect(() => {
    if (streaming) return

    if (svgCache.has(code)) {
      const cachet = svgCache.get(code) ?? null
      setSvg(cachet)
      setFejlet(cachet === null)
      return
    }

    let alive = true
    // Unikt id: mermaid's render skriver til DOM'en under dette navn, og to
    // diagrammer med samme id kolliderer i StrictMode's dobbelt-mount.
    const id = `mermaid-${Math.random().toString(36).slice(2)}`
    hentMermaid()
      .then((m) => m.default.render(id, code))
      .then(({ svg: tegnet }) => {
        const ren = udenAnimation(tegnet, id)
        svgCache.set(code, ren)
        if (alive) {
          setSvg(ren)
          setFejlet(false)
        }
      })
      .catch(() => {
        svgCache.set(code, null)
        if (alive) setFejlet(true)
      })
    return () => {
      alive = false
    }
  }, [code, streaming])

  if (streaming || (!svg && !fejlet)) {
    return (
      <div className="mermaid-block mermaid-pending">
        <span className="mermaid-pending-tekst">diagram tegnes…</span>
      </div>
    )
  }

  if (fejlet || !svg) return <CodeBlock code={code} lang="mermaid" />

  return (
    <div
      className="mermaid-block"
      // Mermaid's EGET SVG-output af diagram-kilden — bibliotekets tilsigtede
      // API, ikke model-leveret HTML. Samme begrundelse som CodeBlock's Shiki.
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  )
}

/** Test-søm. Egenskaben «reglen er scopet» kan ikke måles gennem en render:
 *  mermaid er 4 MB og lazy, og ingen test renderer et diagram OG en animation
 *  i samme dokument — det var præcis derfor 0.6.202 slap igennem. */
export const udenAnimationForTest = udenAnimation
