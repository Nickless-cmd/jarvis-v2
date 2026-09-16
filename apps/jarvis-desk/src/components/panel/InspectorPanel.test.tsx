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
