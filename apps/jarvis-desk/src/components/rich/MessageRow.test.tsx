import { describe, it, expect, vi } from 'vitest'
import { act, render, screen, fireEvent } from '@testing-library/react'
import { MessageRow } from './MessageRow'
import { PanelProvider } from '../../contexts/PanelContext'
import { SettingsProvider } from '../../contexts/SettingsContext'
import { RAEKKE_KEY } from '../../lib/visningsPref'
import type { ContentBlock } from '../../lib/sseProtocol'
import { paaAendringsFokus } from '../../lib/aendringsFokus'

const REDIGERING: ContentBlock[] = [
  { type: 'tool_use', id: 'e1', name: 'edit_file', input: { path: 'src/app.ts', old_text: 'før', new_text: 'efter' },
    status: 'done', result: '{"linjer_tilfoejet":9,"linjer_fjernet":4}' },
  { type: 'text', text: 'Filen er rettet.' },
]

describe('MessageRow', () => {
  it('lader live-tekst komme frem i flere trin uden at ændre det færdige svar', () => {
    vi.useFakeTimers()
    try {
      const text = 'Et synligt svar med mange ord. '.repeat(10)
      const row = <MessageRow role="assistant" blocks={[{ type: 'text', text }]} density="compact" streaming />
      const view = render(row)
      expect(view.container.textContent).not.toContain(text.trim())
      act(() => vi.advanceTimersByTime(99))
      expect(view.container.textContent?.length).toBeGreaterThan(0)
      expect(view.container.textContent).not.toContain(text.trim())
      view.rerender(<MessageRow role="assistant" blocks={[{ type: 'text', text }]} density="compact" streaming={false} />)
      expect(view.container.textContent).toContain(text.trim())
    } finally { vi.useRealTimers() }
  })
  it('viser billedgenerering også i rækkevisning', () => {
    localStorage.setItem(RAEKKE_KEY, '1')
    try {
      render(<MessageRow role="assistant" blocks={[
        { type: 'tool_use', id: 'im1', name: 'pollinations_image', input: { prompt: 'kat' }, status: 'running' },
      ]} density="compact" streaming />)
      expect(screen.getByLabelText('Genererer billede')).toBeInTheDocument()
    } finally { localStorage.removeItem(RAEKKE_KEY) }
  })
  it('fjerner ventefladen i rækkevisning når Jarvis er gået videre', () => {
    localStorage.setItem(RAEKKE_KEY, '1')
    try {
      render(<MessageRow role="assistant" blocks={[
        { type: 'tool_use', id: 'im1', name: 'pollinations_image', input: {}, status: 'running' },
        { type: 'text', text: 'Her er billedet.' },
      ]} density="compact" streaming />)
      expect(screen.queryByLabelText('Genererer billede')).not.toBeInTheDocument()
    } finally { localStorage.removeItem(RAEKKE_KEY) }
  })
  it('viser ændringskortet under svaret i rækkevisning med målte +/− tal', () => {
    localStorage.setItem(RAEKKE_KEY, '1')
    try {
      const { container } = render(<MessageRow role="assistant" blocks={REDIGERING} density="compact" streaming={false} />)
      const kort = container.querySelector('.edited-files')!
      expect(kort).toBeInTheDocument()
      expect(kort).toHaveTextContent('Redigerede 1 fil')
      expect(kort).toHaveTextContent('+9')
      expect(kort).toHaveTextContent('−4')
      expect(container.querySelectorAll('.edited-files')).toHaveLength(1)
      expect(container.querySelector('.rv-svar')!.compareDocumentPosition(kort) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    } finally { localStorage.removeItem(RAEKKE_KEY) }
  })

  it('viser ændringskortet kun én gang i almindelig visning', () => {
    localStorage.setItem(RAEKKE_KEY, '0')
    const { container } = render(<MessageRow role="assistant" blocks={REDIGERING} density="compact" streaming={false} />)
    expect(container.querySelectorAll('.edited-files')).toHaveLength(1)
  })

  it('kortets fil åbner ændringsvisningen på den valgte sti', () => {
    localStorage.setItem(RAEKKE_KEY, '1')
    const fokus = vi.fn()
    const stop = paaAendringsFokus(fokus)
    try {
      render(<MessageRow role="assistant" blocks={REDIGERING} density="compact" streaming={false} />)
      fireEvent.click(screen.getByRole('button', { name: /app\.ts/ }))
      expect(fokus).toHaveBeenCalledWith('src/app.ts')
    } finally { stop(); localStorage.removeItem(RAEKKE_KEY) }
  })
  it('renders assistant text block as markdown', () => {
    render(<MessageRow role="assistant" blocks={[{ type: 'text', text: '**hej**' }]} density="compact" streaming={false} />)
    expect(screen.getByText('hej').tagName).toBe('STRONG')
  })
  it('tænkning er én linje: live med tid, bagefter foldbar — monologen står aldrig åben i tråden', () => {
    // 16/9-2026: live strømmede hele monologen ind i tråden, og bagefter var
    // den væk. Nu en linje begge steder, som mobilen.
    const { rerender } = render(<MessageRow role="assistant" blocks={[{ type: 'thinking', thinking: 'intern' }]} density="compact" streaming />)
    expect(screen.getByText(/Tænker/)).toBeInTheDocument()
    expect(screen.queryByText('intern')).not.toBeInTheDocument()
    rerender(<MessageRow role="assistant" blocks={[{ type: 'thinking', thinking: 'intern', seconds: 8 }]} density="compact" streaming={false} />)
    fireEvent.click(screen.getByRole('button', { name: /Tænkte i 8s/ }))
    expect(screen.getByText('intern')).toBeInTheDocument()
  })
  it('en tanke FØR et værktøjskald er færdig, selv mens turen streamer', () => {
    render(<MessageRow role="assistant" blocks={[{ type: 'thinking', thinking: 'plan' }, { type: 'text', text: 'svar' }]} density="compact" streaming />)
    expect(screen.queryByText(/Tænker/)).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Tænkte' })).toBeInTheDocument()
  })
  it('renders user message as plain bubble text', () => {
    render(<MessageRow role="user" blocks={[{ type: 'text', text: 'hej Jarvis' }]} density="compact" streaming={false} />)
    expect(screen.getByText('hej Jarvis')).toBeInTheDocument()
  })
  it('viser gensend-knap på bruger-besked og kalder onResend med teksten', () => {
    const onResend = vi.fn()
    render(<MessageRow role="user" blocks={[{ type: 'text', text: 'kør igen' }]} density="compact" streaming={false} onResend={onResend} />)
    fireEvent.click(screen.getByTitle('Send igen'))
    expect(onResend).toHaveBeenCalledWith('kør igen')
  })
  it('ingen gensend-knap uden onResend', () => {
    render(<MessageRow role="user" blocks={[{ type: 'text', text: 'x' }]} density="compact" streaming={false} />)
    expect(screen.queryByTitle('Send igen')).not.toBeInTheDocument()
  })

  it('viser en PERSISTERET upload gennem token-hentning — ikke et tomt <img>', () => {
    // Bjørn 27/9-2026: «billeder jeg uploader via composer bliver først vist i
    // chatview når dit run er færdig». Årsagen var en manglende forgrening:
    // bruger-grenen tegnede ALT med `KlikbartBillede src={img.src ?? ''}`.
    // Live-previewet (blob) virkede, men i det øjeblik serveren overtog
    // beskeden, havde blokken kun en REFERENCE (`attachment_id`) — og `src`
    // blev tom. Assistent-grenen havde forgreningen hele tiden.
    //
    // Beviset er at blokken NÅR `AttachmentBlock`, som slår op i
    // settings-konteksten og henter med token: navnet står på skærmen med det
    // samme (før hentningen er færdig). En tom `<img src="">` ville vise intet.
    const upload: ContentBlock[] = [
      { type: 'text', text: 'her ser du hvad jeg ser' },
      { type: 'image', attachment_id: 'abc123', filename: 'Skærmbillede.png' },
    ]
    const { container } = render(
      <SettingsProvider initialConfig={{ apiBaseUrl: '', authToken: null }}>
        <MessageRow role="user" blocks={upload} density="compact" streaming={false} />
      </SettingsProvider>,
    )
    expect(container.querySelector('.msg-user-images')).toBeInTheDocument()
    expect(container.textContent).toContain('Skærmbillede.png')
  })

  it('tegner et LIVE billede (blob) direkte — uden token-hentning', () => {
    const live: ContentBlock[] = [{ type: 'image', src: 'blob:preview-1', alt: 'mit billede' }]
    const { container } = render(
      <SettingsProvider initialConfig={{ apiBaseUrl: '', authToken: null }}>
        <MessageRow role="user" blocks={live} density="compact" streaming={false} />
      </SettingsProvider>,
    )
    const img = container.querySelector('.msg-user-images img')
    expect(img?.getAttribute('src')).toBe('blob:preview-1')
  })
  it('viser INGEN "Åbn"-affordance for langt markdown-svar — svaret står lige der', () => {
    // Bjørn 29/9-2026: «aaben dokument badge, den bliver vist under din besked.
    // den skal ud.» detectArtifacts' regel 2 gjorde ethvert svar på 40+ linjer
    // med to overskrifter til et «Dokument»-artifact, og badgen faldt tilbage
    // til netop titlen «Dokument» når svaret ikke havde en `# `-overskrift.
    // Testen stod før på `getByRole(...)`: den beskriver den gamle adfærd, og
    // den SKAL fejle hvis nogen fører reglen tilbage.
    const long = '# Titel\n' + Array.from({ length: 45 }, (_, i) => `linje ${i}`).join('\n') + '\n## Sektion\nx'
    const { container } = render(
      <PanelProvider defaultWidth={400}>
        <MessageRow role="assistant" blocks={[{ type: 'text', text: long }]} density="compact" streaming={false} />
      </PanelProvider>,
    )
    expect(screen.queryByRole('button', { name: /åbn/i })).toBeNull()
    expect(container.querySelector('.artifact-affordance')).toBeNull()
  })
})
