import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { RaekkeTranskript } from './RaekkeTranskript'
import { SettingsProvider } from '../../contexts/SettingsContext'
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

describe('underagent-rækken', () => {
  const SCOUT: ContentBlock[] = [{
    type: 'tool_use', id: 's1', name: 'scout_agent', input: { goal: 'find kaldere' },
    result: '[scout_agent]: [UTROET kilde=subagent] { "agent_id": "agent-35aa724fd0454660bc7150d7bbc86403" }',
  }, tekst('Fundet.')]

  it('mærker rækken som subagent', () => {
    const { container } = render(<RaekkeTranskript blocks={SCOUT} streaming />)
    expect(container.querySelector('.rv-mrkat')?.textContent).toBe('subagent')
  })

  it('henter FØRST agentens kald når rækken foldes ud', async () => {
    // Det er hele pointen. Hentede vi ved render, ville hver scout_agent-raekke
    // i en lang traad fyre et kald af ved indlaesning — samme fejl som
    // poll-stormen. Kroppen monteres foerst ved udfoldning, saa `useEffect`
    // er dovent af sig selv; testen pinner at det BLIVER saadan.
    const hent = vi.fn(async () => ({ tool_calls: [{ tool_name: 'search', status: 'ok' }] }))
    vi.doMock('../../lib/api', async (rigtig) => ({
      ...(await rigtig<Record<string, unknown>>()), apiFetch: hent,
    }))
    const cfg = { apiBaseUrl: 'http://t', authToken: 'tok' }
    const { container } = render(<RaekkeTranskript blocks={SCOUT} streaming config={cfg} />)
    expect(hent).not.toHaveBeenCalled()

    const raekke = [...container.querySelectorAll('.rv-r')]
      .find((r) => r.querySelector('.rv-mrkat'))!
    fireEvent.click(raekke)
    // Kroppen er nu monteret — og dermed er opslaget i gang.
    expect(container.querySelector('.rv-underagent')).not.toBeNull()
    vi.doUnmock('../../lib/api')
  })

  it('siger det når der ikke er nogen forbindelse', () => {
    // Uden config kan vi ikke spoerge. En tom liste ville ligne «agenten
    // gjorde ingenting», og det er en anden besked.
    const { container } = render(<RaekkeTranskript blocks={SCOUT} streaming />)
    fireEvent.click([...container.querySelectorAll('.rv-r')].find((r) => r.querySelector('.rv-mrkat'))!)
    expect(container.querySelector('.rv-uaTom')?.textContent).toMatch(/[Ii]ngen forbindelse/)
  })
})

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

  it('viser emnet MENS argumenterne stadig strømmer ind', () => {
    // Bjoern 23/9-2026: «under streaming er linjerne tomme, og foerst naar
    // streamen er endt bliver raekkerne udfyldt».
    // Aarsagen: `input` er {} indtil blokken lukker — argumenterne ligger i
    // `partialJson` imens. Registrets `summarize` kender ikke det felt, saa
    // raekken stod tom praecis mens den var mest interessant.
    const streamende: ContentBlock[] = [{
      type: 'tool_use', id: 'b1', name: 'bash', input: {}, status: 'running',
      partialJson: '{"command": "grep -rn tool_calls apps/jarvis-desk',
    }]
    const { container } = render(<RaekkeTranskript blocks={streamende} streaming />)
    const sum = container.querySelector('.rv-sumT')?.textContent ?? ''
    expect(sum).not.toBe('')
    expect(sum).toContain('grep')
  })

  it('tegner progress-blokke som en række', () => {
    const med: ContentBlock[] = [
      kald('bash'),
      { type: 'progress', tool_use_id: 't1', parent_tool_use_id: null,
        message: 'Analyserede billede…', status: 'running' },
      tekst('Færdig.'),
    ]
    render(<RaekkeTranskript blocks={med} streaming />)
    expect(screen.getByText('Progress')).toBeInTheDocument()
    expect(screen.getByText('Analyserede billede…')).toBeInTheDocument()
  })

  it('lader INGEN bloktype forsvinde sporløst', () => {
    // `Element` returnerede `null` for alt den ikke kendte — ingen fejl,
    // ingen tom raekke, bare indhold der ikke var der. `progress` blev spist
    // paa praecis den maade indtil 23/9-2026.
    //
    // En `file`-blok er proevestenen, fordi dens EGEN kommentar i
    // sseProtocol.ts beskriver samme fejl fra 15/9: `foldToolResults` kendte
    // ikke typen og droppede den, saa filen aldrig naaede skaermen. Den
    // ligger her FOER det sidste kald, altsaa i arbejdsomraadet, hvor det er
    // `Element` og ikke BlocksRenderer der afgoer om den ses.
    const medFil: ContentBlock[] = [
      { type: 'file', filename: 'chatview-run.html', url: 'https://api.srvlab.dk/files/chatview-run.html', kilde: 'published' },
      kald('bash'),
      tekst('Svar.'),
    ]
    // `AttachmentBlock` slaar op i settings-konteksten. At den overhovedet
    // NAAR dertil er beviset: blokken bliver renderet i stedet for droppet.
    const { container } = render(
      <SettingsProvider initialConfig={{ apiBaseUrl: '', authToken: null }}>
        <RaekkeTranskript blocks={medFil} streaming />
      </SettingsProvider>,
    )
    expect(container.textContent).toContain('chatview-run.html')
  })

  it('viser +N −M på redigerende rækker', () => {
    // Bjoern 23/9-2026: «i raekkerne mangler +xx -xx diff for edit linjer».
    // `.rv-diffstat` fandtes som CSS, men ingen tegnede den — en doed klasse.
    const redigering: ContentBlock[] = [
      kald('edit_file', { path: 'app.css', old_text: 'a\nb', new_text: 'a\nb\nc\nd' }),
      tekst('Rettet.'),
    ]
    const { container } = render(<RaekkeTranskript blocks={redigering} streaming />)
    expect(container.querySelector('.rv-diffstat')?.textContent?.trim()).toBe('+4 −2')
    // Farverne skal komme fra desks EGNE klasser, ikke fra nye.
    expect(container.querySelector('.rv-diffstat .git-add')?.textContent).toBe('+4')
    expect(container.querySelector('.rv-diffstat .git-del')?.textContent).toBe('−2')
  })

  it('bruger serverens målte tal frem for et gæt ud fra argumenterne', () => {
    // `write_file` kan klienten ikke regne slettede linjer for — den ved ikke
    // om filen fandtes. Serveren har filen i haanden og maaler rigtigt.
    const medResultat: ContentBlock[] = [
      { type: 'tool_use', id: 'w1', name: 'write_file', input: { path: 'x.ts', content: 'en\nto' },
        result: '{"linjer_tilfoejet": 9, "linjer_fjernet": 4}' },
      tekst('Skrevet.'),
    ]
    const { container } = render(<RaekkeTranskript blocks={medResultat} streaming />)
    expect(container.querySelector('.rv-diffstat')?.textContent?.trim()).toBe('+9 −4')
  })

  it('tegner INTET diff-tal på læsende værktøjer', () => {
    // «ingenting at vise» er en anden besked end «nul».
    const laesning: ContentBlock[] = [kald('read_file', { path: 'x.ts' }), tekst('Læst.')]
    const { container } = render(<RaekkeTranskript blocks={laesning} streaming />)
    expect(container.querySelector('.rv-diffstat')).toBeNull()
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

  it('viser exit-koden ogsaa naar den er 0 (Bjørn 22/9-2026)', () => {
    // DSH's kilde skjuler «exit code 0» helt. Bjørn vil have tallet vist, som
    // i hans eget forlaeg — saa koden staar altid, og det er KUN farven der
    // er forbeholdt ikke-nul.
    const { container } = render(<RaekkeTranskript blocks={TUR} streaming />)
    const raekke = [...container.querySelectorAll('.rv-r')]
      .find((r) => r.querySelector('.rv-slags')?.textContent === 'Bash')!
    fireEvent.click(raekke)
    const term = raekke.querySelector('.rv-term')!
    expect(term.getAttribute('data-exit')).toBe('0')
    expect(term.querySelector('.rv-exit')?.textContent).toBe('exit code 0')
  })

  it('markerer en ikke-nul exit-kode', () => {
    const fejlTur: ContentBlock[] = [
      kald('bash', { command: 'pytest' },
        '{"result":{"stdout":"1 failed","exit_code":1}}'),
      tekst('Den fejlede.'),
    ]
    const { container } = render(<RaekkeTranskript blocks={fejlTur} streaming />)
    const raekke = container.querySelector('.rv-r')!
    fireEvent.click(raekke)
    const term = raekke.querySelector('.rv-term')!
    expect(term.getAttribute('data-exit')).toBe('1')
    expect(term.querySelector('.rv-exit')?.textContent).toBe('exit code 1')
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

  it('skjuler ikke exit-koden, og farver kun ikke-nul', () => {
    // jsdom indlaeser ingen CSS, saa raekke-testene ovenfor kan ikke se om
    // koden faktisk er synlig. Kilden maales.
    expect(css).not.toMatch(/data-exit='0'\]\s*\.rv-exit\s*\{[^}]*display:\s*none/)
    expect(css).toMatch(/:not\(\[data-exit='0'\]\)\s*\.rv-exit\s*\{[^}]*color:\s*var\(--error-fg\)/)
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
