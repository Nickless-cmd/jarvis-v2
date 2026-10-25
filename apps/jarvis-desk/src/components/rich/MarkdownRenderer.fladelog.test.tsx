import { describe, it, expect, beforeEach } from 'vitest'
import { cleanup, render } from '@testing-library/react'
import { MarkdownRenderer } from './MarkdownRenderer'
import { nulstilFladeLog, saetFladeLogSender, MAKS_PR_SESSION, type FladeSnapshot } from '../../lib/fladeLog'

// Side-opgave side-155f2dc398: klientlog ved renderbeslutningen.
//
// Kravet var eksplicit: testen skal fyre på en tekst der IKKE bliver en flade
// — den fejlform der ellers er usynlig. En test der kun dækker den korrekte
// vej ville bevise at loggen kan tie, ikke at den kan sige noget.
const SPEC = '{"type":"comparison","title":"Test","columns":["A","B"],"rows":[{"label":"x","values":["1","2"]}]}'
const KORREKT = `Her er fladen:\n\n\`\`\`jarvis-ui\n${SPEC}\n\`\`\`\n\nEfter.`
const MAST = `Her er fladen:\n\n\`\`\`jarvis-ui ${SPEC}\n\`\`\`\n\nEfter.`
const UDEN_FENCE = `Her er fladen: jarvis-ui ${SPEC} — uden hegn overhovedet.`

let fanget: FladeSnapshot[] = []

beforeEach(() => {
  cleanup()
  nulstilFladeLog()
  fanget = []
  saetFladeLogSender((s) => fanget.push(s))
})

const udfald = () => fanget.map((s) => s.udfald)

describe('klientlog ved renderbeslutningen', () => {
  it('logger native når blokken FAKTISK bliver en flade', () => {
    render(<MarkdownRenderer text={KORREKT} streaming={false} />)
    expect(udfald()).toContain('native')
  })

  it('den maste form når ikke længere loggen — den reddes før render', () => {
    // HISTORIK (25/10-2026): denne test hed før «logger wrong-lang for den
    // maste form» og krævede at fejlformen blev LOGGET. Loggen var det eneste
    // spor, fordi kodeblokken blev tom og hverken teksten eller DB'en viste
    // hvorfor.
    //
    // Nu reddes formen i `enforceStructure.unfoldJarvisUiFence`, FØR
    // `pre`-grenen ser den. Så der er intet at logge — og det er pointen:
    // en log der stadig fyrer her ville betyde at reparationen ikke virkede.
    //
    // Kravet er bevaret i skarpere form: formen må hverken give en tom
    // kodeblok eller et `wrong-lang`-snapshot.
    render(<MarkdownRenderer text={MAST} streaming={false} />)
    expect(udfald()).not.toContain('wrong-lang')
  })

  it('logger no-pre-node når blokken aldrig bliver et <pre>', () => {
    // `pre`-grenen ser denne slet ikke. Det er derfor loggen har to steder.
    render(<MarkdownRenderer text={UDEN_FENCE} streaming={false} />)
    expect(udfald()).toContain('no-pre-node')
  })

  it('begrænser antallet af snapshots gennem en hel stream', () => {
    // Streaming kalder rendereren én gang pr. delta. Målt 25/10-2026 er
    // nøglen `udfald + lang + blokkens første 80 tegn`, så hver NY blokform
    // er en ny observation — det er information, ikke støj. Men antallet skal
    // være en brøkdel af deltaerne, ellers bliver loggen selv problemet.
    //
    // Jeg krævede først præcis ÉT snapshot. Det var forkert: blokken vokser
    // gennem streamen, så der ER flere former. Kravet skal være en grænse,
    // ikke et fast tal — ellers måler testen noget andet end den påstår.
    const { rerender } = render(<MarkdownRenderer text="" streaming />)
    for (let n = 1; n <= MAST.length; n++) {
      rerender(<MarkdownRenderer text={MAST.slice(0, n)} streaming />)
    }
    const antal = fanget.length
    expect(antal).toBeGreaterThan(0)
    expect(antal).toBeLessThan(MAST.length / 10)
  })

  it('holder sig under loftet pr. sidevisning', () => {
    for (let i = 0; i < MAKS_PR_SESSION + 10; i++) {
      const tekst = `jarvis-ui uden hegn, variant ${i}`
      render(<MarkdownRenderer text={tekst} streaming={false} />)
      cleanup()
    }
    expect(fanget.length).toBeLessThanOrEqual(MAKS_PR_SESSION)
  })
})
