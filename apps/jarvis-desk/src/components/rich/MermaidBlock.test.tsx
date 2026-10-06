import { describe, it, expect, vi, beforeEach } from 'vitest'
import { cleanup, render, waitFor } from '@testing-library/react'

// Mermaid er ~4 MB og rører DOM'en. Vi måler KALDENE, ikke biblioteket.
const renderMock = vi.fn()
const initializeMock = vi.fn()

vi.mock('mermaid', () => ({
  default: {
    initialize: (...a: unknown[]) => initializeMock(...a),
    render: (...a: unknown[]) => renderMock(...a),
  },
}))

// Shiki er tungt og ligegyldigt her — vi skal kun se HVILKEN blok der valgtes.
vi.mock('./CodeBlock', () => ({
  CodeBlock: ({ code, lang }: { code: string; lang: string }) => (
    <pre data-testid="kodeblok" data-lang={lang}>{code}</pre>
  ),
}))

import { MarkdownRenderer } from './MarkdownRenderer'

const diagram = (navn: string) => `\`\`\`mermaid\nflowchart TD\n  ${navn} --> B\n\`\`\``

describe('mermaid i chatview', () => {
  beforeEach(() => {
    renderMock.mockReset()
    cleanup()
  })

  it('er koblet på: en mermaid-fence bliver til et diagram, ikke en kodeblok', () => {
    const { container } = render(<MarkdownRenderer text={diagram('KOBLING')} streaming />)
    expect(container.querySelector('.mermaid-pending')).not.toBeNull()
    expect(container.querySelector('[data-testid="kodeblok"]')).toBeNull()
  })

  it('tegner IKKE mens blokken stadig streamer', async () => {
    renderMock.mockResolvedValue({ svg: '<svg id="VENTER" />' })
    const { container } = render(<MarkdownRenderer text={diagram('VENTER')} streaming />)
    // En uafsluttet fence kan ikke parses. Et forsøg ville skifte blokken fra
    // kode til diagram midt i turen — præcis den formændring vi undgår.
    //
    // VI SKAL VENTE: mermaid-kaldet sker i en mikrotask bag `import()`. En
    // synkron kontrol ville passere uanset hvad og måle ingenting — den fejl
    // blev målt 6/10, hvor mutationen «streaming={false}» gik igennem.
    await new Promise((r) => setTimeout(r, 0))
    expect(renderMock).not.toHaveBeenCalled()
    expect(container.querySelector('.mermaid-pending')).not.toBeNull()
  })

  it('tegner diagrammet når blokken er færdig', async () => {
    renderMock.mockResolvedValue({ svg: '<svg id="FAERDIG"><rect /></svg>' })
    const { container } = render(<MarkdownRenderer text={diagram('FAERDIG')} streaming={false} />)
    await waitFor(() => expect(container.querySelector('.mermaid-block svg')).not.toBeNull())
    expect(renderMock).toHaveBeenCalledTimes(1)
  })

  it('tegner et FROSSET diagram mens den levende hale stadig streamer', async () => {
    // Kun den sidste blok er levende (samme antagelse delIBlokke bygger på).
    // Derfor må et diagram i en færdig blok tegnes straks — ikke vente på
    // hele svaret.
    renderMock.mockResolvedValue({ svg: '<svg id="FROSSET" />' })
    const tekst = `${diagram('FROSSET')}\n\nResten skrives stadig`
    const { container } = render(<MarkdownRenderer text={tekst} streaming />)
    await waitFor(() => expect(container.querySelector('.mermaid-block svg')).not.toBeNull())
  })

  it('holder en mermaid-fence SAMLET gennem blokdelingen', async () => {
    renderMock.mockResolvedValue({ svg: '<svg id="SAMLET" />' })
    const tekst = `Før.\n\n${diagram('SAMLET')}\n\nEfter.`
    const { container } = render(<MarkdownRenderer text={tekst} streaming />)
    // Ét diagram, ingen kodeblok: var fencen splittet, ville halen stå som kode.
    // Blokken er frossen (den er ikke halen), så den tegner straks — vi venter
    // på at tegningen lander i stedet for at måle midt i en state-update.
    await waitFor(() => expect(container.querySelectorAll('.mermaid-block')).toHaveLength(1))
    expect(container.querySelectorAll('[data-testid="kodeblok"]')).toHaveLength(0)
    expect(container.textContent).toContain('Efter.')
  })

  it('falder tilbage til en kodeblok når kilden ikke kan parses', async () => {
    renderMock.mockRejectedValue(new Error('parse-fejl'))
    const { container } = render(
      <MarkdownRenderer text={'```mermaid\nikke gyldig mermaid\n```'} streaming={false} />,
    )
    // Et dårligt diagram bliver kode — ikke en tom rude.
    await waitFor(() => expect(container.querySelector('[data-testid="kodeblok"]')).not.toBeNull())
    expect(container.querySelector('[data-testid="kodeblok"]')?.getAttribute('data-lang')).toBe('mermaid')
  })

  it('tegner kun ÉN gang for samme kilde', async () => {
    renderMock.mockResolvedValue({ svg: '<svg id="CACHE" />' })
    const kode = diagram('CACHE')
    const a = render(<MarkdownRenderer text={kode} streaming={false} />)
    await waitFor(() => expect(a.container.querySelector('svg')).not.toBeNull())
    a.unmount()
    const b = render(<MarkdownRenderer text={kode} streaming={false} />)
    // Modul-cachen: remount tegner ikke forfra (ingen flicker i StrictMode).
    expect(b.container.querySelector('svg')).not.toBeNull()
    expect(renderMock).toHaveBeenCalledTimes(1)
  })

  it('saniterer diagram-outputtet', async () => {
    renderMock.mockResolvedValue({ svg: '<svg id="SEC" />' })
    render(<MarkdownRenderer text={diagram('SEC')} streaming={false} />)
    // Mermaid initialiseres ÉN gang for hele modulet (løftet caches), så
    // kaldet kan stamme fra en tidligere test i denne fil. Vi kræver derfor
    // at HVERT kald satte strict — ikke at netop dette gjorde.
    await waitFor(() => expect(initializeMock.mock.calls.length).toBeGreaterThan(0))
    for (const [arg] of initializeMock.mock.calls) {
      // SVG'en indsættes med dangerouslySetInnerHTML — strict er værn mod
      // fjendtlige labels i diagram-kilden.
      expect((arg as Record<string, unknown>).securityLevel).toBe('strict')
    }
  })
})
