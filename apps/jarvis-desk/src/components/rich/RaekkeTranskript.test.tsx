import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { RaekkeTranskript } from './RaekkeTranskript'
import { RAEKKE_KEY } from '../../lib/visningsPref'
import type { ContentBlock } from '../../lib/sseProtocol'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

/**
 * Rækkevisningens form.
 *
 * Testene måler dét Bjørn faktisk pegede på undervejs, så de fejl ikke kan
 * komme igen: arbejdet skal folde sig SAMMEN når streamingen slutter, de
 * korte synteser skal ligge INDE i arbejdet, og svaret skal blive stående.
 */

const tekst = (t: string): ContentBlock => ({ type: 'text', text: t })
const tanke = (t: string, s?: number): ContentBlock =>
  s == null ? { type: 'thinking', thinking: t } : { type: 'thinking', thinking: t, seconds: s }
const kald = (navn: string, input: Record<string, unknown> = {}, result?: string): ContentBlock => ({
  type: 'tool_use', id: `${navn}-1`, name: navn, input, ...(result ? { result } : {}),
})

/** En hel tur: tanke → kald → kort syntese → kald → svar. */
const TUR: ContentBlock[] = [
  tanke('Nøglen starter med xpl_ — det mønster kender jeg ikke.', 41),
  kald('web_search', { query: 'experiential labs api key' }),
  tekst('Den svarer 200. Nu finder jeg ud af hvad nøglen reelt giver.'),
  kald('bash', { command: 'curl -s /v1/models' }, '{"result":{"stdout":"http=200 bytes=96185","exit_code":0}}'),
  tekst('Nøglen er gyldig — men ikke betalingsklar.'),
]

beforeEach(() => { localStorage.setItem(RAEKKE_KEY, '1') })

describe('RaekkeTranskript', () => {
  it('folder arbejdet SAMMEN når streamingen er slut — svaret bliver stående', () => {
    // Det var praecis fejlen 22/9: raekkerne blev staaende bagefter, og
    // synteserne druknede i dem.
    render(<RaekkeTranskript blocks={TUR} streaming={false} />)
    expect(screen.getByText('Thought for 41s · 2 tool calls')).toBeInTheDocument()
    // `hidden` fjerner ikke noden — den skjuler den. Og bemaerk: jsdom
    // indlaeser ikke CSS, saa DENNE test kan ikke se om reglen der faktisk
    // skjuler gruppen findes. Det maaler `raekkevisning.css`-testen nedenfor.
    expect(screen.getByText('Bash')).not.toBeVisible()
    expect(screen.getByText(/ikke betalingsklar/)).toBeInTheDocument()
  })

  it('viser arbejdet mens der streames — man skal kunne følge med', () => {
    render(<RaekkeTranskript blocks={TUR} streaming />)
    expect(screen.getByText('Working…')).toBeInTheDocument()
    expect(screen.getByText('Bash')).toBeInTheDocument()
  })

  it('lægger den korte syntese INDE i arbejdet, ikke i svaret', () => {
    const { container } = render(<RaekkeTranskript blocks={TUR} streaming />)
    const mellem = container.querySelector('.rv-gruppe .rv-mellem')
    expect(mellem?.textContent).toBe('Den svarer 200. Nu finder jeg ud af hvad nøglen reelt giver.')
    // …og ikke som en selvstaendig besked ved siden af svaret.
    expect(container.querySelectorAll('.raekkevisning > .rv-mellem')).toHaveLength(0)
  })

  it('bruger engelske etiketter (Bjørn 22/9-2026)', () => {
    render(<RaekkeTranskript blocks={TUR} streaming />)
    expect(screen.getByText('Think')).toBeInTheDocument()
    expect(screen.getByText('Search')).toBeInTheDocument()
    expect(screen.getByText('Bash')).toBeInTheDocument()
  })

  it('folder en enkelt række ud og ind igen, og chevronen skifter retning', () => {
    const { container } = render(<RaekkeTranskript blocks={TUR} streaming />)
    const raekke = [...container.querySelectorAll('.rv-r')]
      .find((r) => r.querySelector('.rv-slags')?.textContent === 'Bash')!
    expect(raekke.querySelector('.rv-chev')?.textContent).toBe('▸')
    expect(raekke.querySelector('.rv-krop')).toBeNull()
    fireEvent.click(raekke)
    expect(raekke.querySelector('.rv-chev')?.textContent).toBe('▾')
    expect(raekke.querySelector('.rv-krop')).not.toBeNull()
    fireEvent.click(raekke)
    expect(raekke.querySelector('.rv-chev')?.textContent).toBe('▸')
  })

  it('tegner INGEN exit-pille ved 0 — kun ikke-nul markeres', () => {
    // Maalt i DSH: `exit 0` tegner ingenting. En groen «exit code 0» paa hvert
    // kald er halvdelen af hvorfor et transskript foeles terminal-agtigt.
    const { container } = render(<RaekkeTranskript blocks={TUR} streaming />)
    const raekke = [...container.querySelectorAll('.rv-r')]
      .find((r) => r.querySelector('.rv-slags')?.textContent === 'Bash')!
    fireEvent.click(raekke)
    expect(raekke.querySelector('.rv-term')?.getAttribute('data-exit')).toBe('0')
  })

  it('en besked uden værktøjskald får intet turhoved', () => {
    const { container } = render(<RaekkeTranskript blocks={[tekst('Ja, det passer.')]} streaming={false} />)
    expect(container.querySelector('.rv-tur')).toBeNull()
    expect(screen.getByText('Ja, det passer.')).toBeInTheDocument()
  })

  it('kan åbnes igen efter turen er slut', () => {
    render(<RaekkeTranskript blocks={TUR} streaming={false} />)
    fireEvent.click(screen.getByRole('button', { name: /Thought for 41s/ }))
    expect(screen.getByText('Bash')).toBeInTheDocument()
  })
})

describe('raekkevisning.css', () => {
  // Stien er fra pakkeroden: vitest koerer med cwd = apps/jarvis-desk.
  const css = readFileSync(resolve('src/styles/raekkevisning.css'), 'utf8')

  it('overstyrer [hidden] — ellers skjuler `hidden` INTET', () => {
    // Den dyreste fejl i hele arbejdet (22/9-2026): `.rv-gruppe` fik
    // `display:flex`, og en author-regel slaar browserens egen [hidden].
    // Gruppen blev staaende, fold-knappen saa doed ud, og synteserne
    // druknede mellem raekker der skulle vaere foldet vaek. Tre symptomer,
    // een manglende linje. jsdom kan ikke se det — derfor maales kilden.
    expect(css).toMatch(/\.rv-gruppe\s*\{[^}]*display:\s*flex/)
    expect(css).toMatch(/\.rv-gruppe\[hidden\]\s*\{\s*display:\s*none/)
  })

  it('scoper ALT under .raekkevisning, så bobblevisningen ikke rammes', () => {
    // Vi deler stylesheet med bobblevisningen. En regel som `.rv-r { ... }`
    // uden rod-klassen ville ramme klasser vi ikke ejer.
    // Kommentarerne SKAL stripes foerst. Uden det laeser en regex-vagt
    // kommentartekst som selektorer og maaler naesten ingenting — den
    // foerste udgave af denne test rapporterede «/* Diff — maalt: +/-» som
    // en uscopet selektor.
    const uden = css.replace(/\/\*[\s\S]*?\*\//g, '')
    const uscopede = [...uden.matchAll(/(^|\})\s*([^@{}]+?)\s*\{/g)]
      .map((m) => m[2] ?? '')
      .flatMap((s) => s.split(','))
      .map((s) => s.trim())
      .filter((s) => s.length > 0)
      // keyframe-trin (`0%`, `90%, 100%`) er ikke selektorer
      .filter((s) => !/^(\d|from\b|to\b)/.test(s))
      .filter((s) => !s.includes('.raekkevisning') && !s.includes('.composer-tal'))
    expect(uscopede).toEqual([])
  })
})
