import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
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
const statusKald = (navn: string, input: Record<string, unknown>, status: 'running' | 'done'): ContentBlock => ({
  type: 'tool_use', id: `${navn}-1`, name: navn, input, status,
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
  it('holder billedrækken åben og viser lightbox uden for rækken ved klik', async () => {
    const fetchMock = vi.fn(async (_url: string) => new Response(new Blob([new Uint8Array([1])]), { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)
    ;(URL as unknown as { createObjectURL: unknown }).createObjectURL = vi.fn(() => 'blob:preview')
    ;(URL as unknown as { revokeObjectURL: unknown }).revokeObjectURL = vi.fn()
    try {
      const { container } = render(<RaekkeTranskript
        blocks={[kald('analyze_image', { image_path: '/tmp/crop-nederst.png' }, '{"analysis":"udsnit"}'), tekst('Færdig.') ]}
        streaming={false} beskedId="message-1"
        config={{ apiBaseUrl: 'http://server', authToken: 'tok' }} />)
      fireEvent.click(container.querySelector('.rv-tur')!)
      fireEvent.click(container.querySelector('.rv-arbejdsknap')!)
      const raekke = container.querySelector('.rv-r')!
      fireEvent.click(raekke.querySelector('.rv-hoved')!)
      await waitFor(() => expect(raekke.querySelector('.billed-knap')).toBeInTheDocument())
      expect(String(fetchMock.mock.calls[0]?.[0])).toContain('besked_id=message-1')
      expect(String(fetchMock.mock.calls[0]?.[0])).toContain('tool_use_id=analyze_image-1')

      fireEvent.click(raekke.querySelector('.billed-knap')!)
      expect(raekke).toHaveAttribute('data-aaben')
      expect(screen.getByRole('dialog', { name: 'crop-nederst.png' })).toBeInTheDocument()
      expect(raekke.querySelector('.billed-lightbox')).toBeNull()
      fireEvent.keyDown(window, { key: 'Escape' })
      expect(screen.queryByRole('dialog')).toBeNull()
    } finally {
      vi.unstubAllGlobals()
      vi.restoreAllMocks()
    }
  })
  it('bevarer Working øverst og samler rækker mellem synlige synteser', () => {
    const { container } = render(<RaekkeTranskript blocks={[
      tekst('Jeg finder filen.'), kald('read_file'), kald('grep'),
      tekst('Jeg retter den nu.'), kald('edit_file'), tekst('Færdig.'),
    ]} streaming />)
    expect(screen.getByText('Working…')).toBeInTheDocument()
    const gruppe = container.querySelector('.rv-gruppe')!
    expect([...gruppe.children].map((e) => e.className)).toEqual([
      'rv-mellem', 'rv-arbejdsrunde', 'rv-mellem', 'rv-arbejdsrunde',
    ])
    expect(gruppe.querySelectorAll('.rv-arbejdsrunde')).toHaveLength(2)
    expect(screen.getByText('Færdig.')).toBeInTheDocument()
  })

  it('folder værktøjsrækkerne ud fra deres egen arbejdsrække', () => {
    const { container } = render(<RaekkeTranskript blocks={TUR} streaming />)
    const arbejdsrunde = container.querySelectorAll('.rv-arbejdsrunde')[1]!
    const knap = arbejdsrunde.querySelector('button')!
    expect(knap).toHaveAttribute('aria-expanded', 'false')
    expect(screen.getByText('Bash')).not.toBeVisible()
    fireEvent.click(knap)
    expect(knap).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByText('Bash')).toBeVisible()
    expect(screen.getByText('Search')).not.toBeVisible()
  })

  it('bruger Jarvis’ egen kommandobeskrivelse og en levende værktøjsfallback', () => {
    const medTekst = render(<RaekkeTranskript blocks={[
      tekst('Jeg undersøger filen.'),
      kald('bash', { command: 'cat app.ts', description: 'Læs koden i app.ts' }),
      tekst('Færdig.'),
    ]} streaming />)
    expect(medTekst.container.querySelector('.rv-arbejdsrunde > button')?.textContent)
      .toContain('Læs koden i app.ts')
    expect(medTekst.container.querySelector('.rv-mellem')?.textContent).toBe('Jeg undersøger filen.')
    medTekst.unmount()
    const uden = render(<RaekkeTranskript blocks={[kald('read_file'), tekst('Svar.')]} streaming />)
    expect(uden.container.querySelector('.rv-arbejdsrunde > button')?.textContent)
      .toContain('Læser')
  })

  it('skifter tekst og Lucide-ikon når det aktuelle værktøj skifter', () => {
    const start = [tekst('Jeg undersøger problemet.'),
      statusKald('read_file', { path: 'app.ts' }, 'running'), tekst('Svar.')]
    const { container, rerender } = render(<RaekkeTranskript blocks={start} streaming />)
    expect(container.querySelectorAll('.rv-arbejdsrunde')).toHaveLength(1)
    expect(container.querySelector('.rv-arbejdsknap')?.textContent).toContain('Læser app.ts')
    expect(container.querySelector('.rv-arbejdsknap svg')).toHaveClass('lucide-file-text')
    expect(container.querySelector('.rv-arbejdsfortaelling')).toHaveClass('shimmer')
    expect(container.querySelector('.rv-arbejdsknap')?.textContent).not.toContain('Jarvis arbejder')
    rerender(<RaekkeTranskript blocks={[
      tekst('Jeg undersøger problemet.'),
      statusKald('read_file', { path: 'app.ts' }, 'done'),
      statusKald('edit_file', { path: 'app.ts' }, 'running'),
      tekst('Svar.'),
    ]} streaming />)
    expect(container.querySelectorAll('.rv-arbejdsrunde')).toHaveLength(1)
    expect(container.querySelector('.rv-arbejdsknap')?.textContent).toContain('Redigerer app.ts')
    expect(container.querySelector('.rv-arbejdsknap svg')).toHaveClass('lucide-file-pen')
  })

  it('opdaterer teksten mens argumenterne til samme kald strømmer ind', () => {
    const start: ContentBlock[] = [{ type: 'tool_use', id: 'r1', name: 'read_file', input: {}, status: 'running' }]
    const { container, rerender } = render(<RaekkeTranskript blocks={start} streaming />)
    expect(container.querySelector('.rv-arbejdsknap')?.textContent).toContain('Læser')
    rerender(<RaekkeTranskript blocks={[
      { ...start[0], partialJson: '{"path":"src/app.ts"' } as ContentBlock,
    ]} streaming />)
    expect(container.querySelector('.rv-arbejdsknap')?.textContent).toContain('Læser app.ts')
    rerender(<RaekkeTranskript blocks={[
      { type: 'tool_use', id: 'r1', name: 'read_file', input: { path: 'src/app.ts' }, status: 'done' },
    ]} streaming />)
    expect(container.querySelector('.rv-arbejdsknap')?.textContent).toContain('Læste app.ts')
    expect(container.querySelector('.rv-arbejdsfortaelling')).not.toHaveClass('shimmer')
  })

  it('skifter fra løbende handling til modelens rundeopsummering', () => {
    const aktivt: ContentBlock[] = [
      statusKald('read_file', { path: 'app.ts' }, 'running'), tekst('Svar.'),
    ]
    const { container, rerender } = render(<RaekkeTranskript blocks={aktivt} streaming />)
    expect(container.querySelector('.rv-arbejdsknap')?.textContent).toContain('Læser app.ts')
    rerender(<RaekkeTranskript blocks={[
      statusKald('read_file', { path: 'app.ts' }, 'done'), tekst('Svar.'),
    ]} streaming rundeEtiketter={{ 'read_file-1': 'Fandt fejlen i filen' }} />)
    expect(container.querySelector('.rv-arbejdsknap')?.textContent).toContain('Fandt fejlen i filen')
    expect(container.querySelector('.rv-arbejdsknap')?.textContent).not.toContain('Læser app.ts')
    expect(container.querySelector('.rv-arbejdsfortaelling')).not.toHaveClass('shimmer')
  })

  it('viser gemt rundeopsummering efter genindlæsning', () => {
    const medGemt: ContentBlock[] = [
      statusKald('read_file', { path: 'app.ts' }, 'done'), tekst('Svar.'),
      { type: 'tool_use_summary', summary: 'Gennemgik filen', preceding_tool_use_ids: ['read_file-1'] },
    ]
    const { container } = render(<RaekkeTranskript blocks={medGemt} streaming={false} />)
    fireEvent.click(container.querySelector('.rv-tur')!)
    expect(container.querySelector('.rv-arbejdsknap')?.textContent).toContain('Gennemgik filen')
  })

  it('viser kommandoens egen beskrivelse — uden et «Færdig»-præfiks', () => {
    // Bjørn 24/9-2026: «det er bare <færdig> der ikk passer ind». Præfikset er
    // væk; linjen er Jarvis' egen beskrivelse og intet andet. Vagt, så ordet
    // ikke sniger sig ind igen ad en anden vej.
    const blocks: ContentBlock[] = [
      statusKald('bash', { command: 'npm test', description: 'Kør testene' }, 'done'),
      tekst('Alle tests bestod.'),
    ]
    const { container } = render(<RaekkeTranskript blocks={blocks} streaming />)
    const knap = container.querySelector('.rv-arbejdsknap')
    expect(knap?.textContent).toContain('Kør testene')
    expect(knap?.textContent).not.toContain('Færdig')
    expect(container.querySelector('.rv-arbejdsknap svg')).toHaveClass('lucide-square-terminal')
  })

  it('viser handlingens ikon også efter en runde er færdig', () => {
    const { container } = render(<RaekkeTranskript blocks={[
      kald('operator_channel', { action: 'open' }), tekst('Kanalen er åben.'),
    ]} streaming={false} />)
    fireEvent.click(container.querySelector('.rv-tur')!)
    expect(container.querySelector('.rv-arbejdsknap svg')).toHaveClass('lucide-monitor')
  })

  it('viser blandet fil- og kommandoarbejde med bogikon', () => {
    const { container } = render(<RaekkeTranskript blocks={[
      kald('read_file', { path: 'app.ts' }), kald('bash', { command: 'npm test' }), tekst('Færdig.'),
    ]} streaming />)
    expect(container.querySelector('.rv-arbejdsknap svg')).toHaveClass('lucide-book-open')
  })

  it('giver ogsaa rene research-runder bogikonet', () => {
    // Bogen hang foer paa ét eneste navn (`read_file`), saa `search`+`bash` og
    // `recall`+`bash` faldt til terminalen. Praedikatet er nu et SAET laesere
    // (Bjoern 24/9-2026).
    for (const laeser of ['search', 'recall', 'web_search', 'operator_grep', 'find_files']) {
      const { container } = render(<RaekkeTranskript blocks={[
        kald(laeser, { pattern: 'x' }), kald('bash', { command: 'npm test' }), tekst('Færdig.'),
      ]} streaming />)
      expect(container.querySelector('.rv-arbejdsknap svg')).toHaveClass('lucide-book-open')
    }
  })

  it('giver IKKE bogikon naar runden kun laeser', () => {
    // Bogen betyder «laeste og gjorde saa noget». Uden en kommando i runden er
    // der ikke noget «saa» — ikonet skal vaere det sidste vaerktoejs eget.
    const { container } = render(<RaekkeTranskript blocks={[
      kald('read_file', { path: 'a.ts' }), kald('search', { pattern: 'x' }), tekst('Fandt den.'),
    ]} streaming />)
    expect(container.querySelector('.rv-arbejdsknap svg')).toHaveClass('lucide-search')
  })

  it('har ingen operator-praefiksede navne i laeser-saettet', () => {
    // `arbejdsIkon` stripper `operator_` FOER opslaget, saa et navn med praefiks
    // i LAESERE ville aldrig matche. Vagten laeser kilden — som CSS-vagten goer.
    const src = readFileSync(resolve(__dirname, 'RaekkeTranskript.tsx'), 'utf8')
    const blok = src.match(/const LAESERE = new Set\(\[([\s\S]*?)\]\)/)?.[1] ?? ''
    expect(blok).not.toBe('')
    expect(blok).not.toContain("'operator_")
  })

  it('lægger turens fold-ud-pil efter tiden og formaterer synteser uden indrykning', () => {
    const { container } = render(<RaekkeTranskript blocks={[
      tekst('Jeg har **fjernet** fejlen i `app.ts`.'),
      kald('bash', { command: 'npm test' }),
      tekst('Færdig.'),
    ]} streaming={false} />)
    const header = container.querySelector('.rv-tur')!
    expect(header.lastElementChild).toHaveClass('rv-turC')
    fireEvent.click(header)
    const syntese = container.querySelector('.rv-mellem')!
    expect(syntese.querySelector('strong')?.textContent).toBe('fjernet')
    expect(syntese.querySelector('code')?.textContent).toBe('app.ts')
    expect(syntese.textContent).not.toContain('**')
    const css = readFileSync(resolve(__dirname, '../../styles/raekkevisning.css'), 'utf8')
    expect(css).toMatch(/\.raekkevisning \.rv-mellem \{[^}]*padding-left:\s*0/)
  })

  it('folder arbejdet SAMMEN når streamingen er slut — svaret bliver stående', () => {
    // Det var praecis fejlen 22/9: raekkerne blev staaende bagefter, og
    // synteserne druknede i dem.
    render(<RaekkeTranskript blocks={TUR} streaming={false} />)
    expect(screen.getByText('Slog noget op og kørte en kommando · 41s')).toBeInTheDocument()
    // Skjulte runder maa ikke fylde DOM'en i en lang gemt samtale.
    expect(screen.queryByText('Bash')).toBeNull()
    expect(screen.getByText(/ikke betalingsklar/)).toBeInTheDocument()
  })

  it('monterer først rækkerne når hele turen foldes ud', () => {
    const { container } = render(<RaekkeTranskript blocks={TUR} streaming={false} />)
    expect(container.querySelectorAll('.rv-arbejdsrunde')).toHaveLength(0)
    fireEvent.click(container.querySelector('.rv-tur')!)
    expect(container.querySelectorAll('.rv-arbejdsrunde')).toHaveLength(2)
    expect(container.querySelectorAll('.rv-r').length).toBeGreaterThan(0)
    fireEvent.click(container.querySelector('.rv-tur')!)
    expect(container.querySelectorAll('.rv-arbejdsrunde')).toHaveLength(0)
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

  it('fører delvise argumenter ind i den åbne Bash-krop under kørslen', () => {
    const med: ContentBlock[] = [{
      type: 'tool_use', id: 'b1', name: 'operator_bash', input: {}, status: 'running',
      partialJson: '{"command":"sleep 5"',
    }]
    const { container } = render(<RaekkeTranskript blocks={med} streaming />)
    fireEvent.click(container.querySelector('.rv-arbejdsknap')!)
    fireEvent.click(container.querySelector('.rv-r[data-foldbar]')!)
    expect(container.querySelector('.rv-term .rv-kh')?.textContent).toContain('sleep 5')
    expect(container.querySelector('.rv-term pre')?.textContent).toContain('Kører…')
  })

  it('tegner progress-blokke som en række', () => {
    const med: ContentBlock[] = [
      kald('bash'),
      { type: 'progress', tool_use_id: 't1', parent_tool_use_id: null,
        message: 'Analyserede billede…', status: 'running' },
      tekst('Færdig.'),
    ]
    render(<RaekkeTranskript blocks={med} streaming />)
    // Uden `tool`/`hint` (en gemt besked fra foer 23/9) falder linjen tilbage
    // til `message`. Labelen «Progress» findes ikke laengere — raekken viser
    // vaerktoejets ikon i stedet (Bjoern 23/9-2026).
    expect(screen.queryByText('Progress')).toBeNull()
    expect(screen.getByText('Analyserede billede…')).toBeInTheDocument()
  })

  it('viser vaerktoejets ikon og emnet — ikke labelen «Koerer kommando»', () => {
    // Bjoern 23/9-2026: «Koerer kommando skal helt vaek og erstattes af ikone
    // og dette echo === burde vise den faktisk kommando». Serveren sender nu
    // `tool` + `hint` ved siden af den flade `message`, saa klienten kan
    // vaelge ikonet selv i stedet for at vise label-teksten raat.
    const med: ContentBlock[] = [
      kald('bash'),
      { type: 'progress', tool_use_id: 't1', parent_tool_use_id: null,
        tool: 'bash', hint: 'git commit', message: 'Kører kommando: git commit',
        status: 'done' },
      tekst('Færdig.'),
    ]
    const { container } = render(<RaekkeTranskript blocks={med} streaming />)
    expect(container.textContent).not.toContain('Kører kommando')
    expect(screen.getByText('git commit')).toBeInTheDocument()
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

  it('viser grønne og røde diff-tal på den foldbare arbejdsrække', () => {
    const redigering: ContentBlock[] = [
      kald('edit_file', { path: 'a.ts', old_text: 'a', new_text: 'a\nb' }),
      kald('edit_file', { path: 'b.ts', old_text: 'c', new_text: 'c\nd\ne' }),
      tekst('Rettet.'),
    ]
    const { container, rerender } = render(<RaekkeTranskript blocks={redigering} streaming />)
    const tal = container.querySelector('.rv-arbejdsknap .rv-diffstat')
    expect(tal?.querySelector('.git-add')?.textContent).toBe('+5')
    expect(tal?.querySelector('.git-del')?.textContent).toBe('−2')
    rerender(<RaekkeTranskript blocks={redigering} streaming={false} />)
    fireEvent.click(container.querySelector('.rv-tur')!)
    expect(container.querySelector('.rv-arbejdsknap .rv-diffstat')?.textContent).toContain('+5')
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
    expect(container.querySelector('.rv-arbejdsknap .rv-diffstat')).toBeNull()
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
    expect(raekke.querySelector('.rv-chev .lucide-chevron-right')).not.toBeNull()
    expect(raekke.querySelector('.rv-krop')).toBeNull()
    fireEvent.click(raekke)
    expect(raekke.querySelector('.rv-chev .lucide-chevron-down')).not.toBeNull()
    expect(raekke.querySelector('.rv-krop')).not.toBeNull()
    fireEvent.click(raekke)
    expect(raekke.querySelector('.rv-chev .lucide-chevron-right')).not.toBeNull()
  })

  it('fold-pilen er et rigtigt ikon — teksttegnet ▸/▾ findes ikke længere', () => {
    const { container } = render(<RaekkeTranskript blocks={TUR} streaming />)
    // Bjørn 23/9-2026: «slippe for ▸ som ikon og så bare bruge den rigtige >».
    // Vagten er på TEGNET, ikke på markuppen: et ▸ kan snige sig ind igen via
    // en helt anden komponent, og så skal den fanges her.
    expect(container.textContent).not.toMatch(/[▸▾]/)
    expect(container.querySelectorAll('.lucide-chevron-right, .lucide-chevron-down').length)
      .toBeGreaterThan(0)
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
    fireEvent.click(screen.getByRole('button', { name: /Slog noget op og kørte en kommando · 41s/ }))
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
    expect(css).toMatch(/\.rv-arbejdsdetaljer\[hidden\]\s*\{\s*display:\s*none/)
  })

  it('har ingen rygrad — stregen gennem gruppen er fjernet', () => {
    // Bjørn 24/9-2026: «det hele.... synes den er grim» → «Fjern stregen helt».
    // Det var en 1px lodret linje gennem hver udfoldet gruppe, med ikonerne
    // siddende på den. Vagt, så den ikke sniger sig ind igen ad en anden vej.
    expect(css).not.toMatch(/rv-gruppe::before/)
    expect(css).not.toMatch(/rv-ikon\s*\{[^}]*background/)
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
