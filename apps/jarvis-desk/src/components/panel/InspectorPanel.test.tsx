import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { InspectorPanel } from './InspectorPanel'

describe('InspectorPanel', () => {
  it('renderer artifact gennem den fælles shell', () => {
    render(<InspectorPanel
      target={{ type: 'artifact', artifact: { kind: 'markdown', title: 'Min spec', content: '# Hej' } }}
      canGoBack={false} onBack={() => {}} onClose={() => {}} onOpenTarget={() => {}}
    />)
    expect(screen.getByText('Min spec')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Hej' })).toBeInTheDocument()
  })

  it('viser tilbage til Miljø for et tool-target', async () => {
    const back = vi.fn()
    render(<InspectorPanel
      target={{ type: 'tool', tool: { id: 't1', name: 'web_search', input: {}, status: 'done' } }}
      canGoBack={false} onBack={back} onClose={() => {}} onOpenTarget={() => {}}
    />)
    await userEvent.click(screen.getByRole('button', { name: 'Tilbage til Miljø' }))
    expect(back).toHaveBeenCalledOnce()
  })
})

describe('InspectorPanel — tilbage-knappens destination', () => {
  const source = {
    url: 'https://docs.example.com/a', domaene: 'docs.example.com', origin: 'tool_result' as const,
  }
  it('siger «Tilbage til Miljø» når der ikke er en historik at gå til', () => {
    render(<InspectorPanel target={{ type: 'source', source }} canGoBack={false}
      onBack={() => {}} onClose={() => {}} onOpenTarget={() => {}} />)
    expect(screen.getByRole('button', { name: 'Tilbage til Miljø' })).toBeInTheDocument()
  })
  it('siger bare «Tilbage» når den går til det forrige panel', () => {
    // Fra en kilde aabnet FRA et tool gaar knappen til tool-resultatet.
    // «Tilbage til Miljø» ville laese en forkert destination op.
    render(<InspectorPanel target={{ type: 'source', source }} canGoBack
      onBack={() => {}} onClose={() => {}} onOpenTarget={() => {}} />)
    expect(screen.getByRole('button', { name: 'Tilbage' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Tilbage til Miljø' })).not.toBeInTheDocument()
  })
})
