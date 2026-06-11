import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ArtifactPanel } from './ArtifactPanel'

describe('ArtifactPanel', () => {
  it('viser placeholder når intet artifact', () => {
    render(<ArtifactPanel artifact={null} onClose={() => {}} />)
    expect(screen.getByText(/intet at vise/i)).toBeTruthy()
  })
  it('viser titel + markdown-indhold', () => {
    render(<ArtifactPanel artifact={{ kind: 'markdown', title: 'Min Spec', content: '# Overskrift' }} onClose={() => {}} />)
    expect(screen.getByText('Min Spec')).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Overskrift' })).toBeTruthy()
  })
  it('kalder onClose når luk klikkes', () => {
    const onClose = vi.fn()
    render(<ArtifactPanel artifact={{ kind: 'code', title: 'a.js', language: 'js', content: 'const x=1' }} onClose={onClose} />)
    screen.getByLabelText('Luk panel').click()
    expect(onClose).toHaveBeenCalled()
  })
  it('henter og viser fil-indhold for file-artifact', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(
      JSON.stringify({ path: 'docs/x.md', content: '# Fil-titel', language: 'markdown' }),
      { status: 200, headers: { 'content-type': 'application/json' } },
    )))
    render(<ArtifactPanel artifact={{ kind: 'file', title: 'x.md', filePath: 'docs/x.md' }} onClose={() => {}} config={{ apiBaseUrl: 'http://t', authToken: 't' }} />)
    expect(await screen.findByRole('heading', { name: 'Fil-titel' })).toBeTruthy()
  })
})
