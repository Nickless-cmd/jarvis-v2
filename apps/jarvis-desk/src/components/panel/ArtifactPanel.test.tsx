import { describe, it, expect, vi } from 'vitest'
import { render, screen, act } from '@testing-library/react'
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

  // ---------------------------------------------------------------------
  // Blinket (7/9-2026): Bjørn kunne ikke scrolle i et 67 KB tool-register —
  // panelet gik til tom og blinkede. Effekten afhang af `config`-OBJEKTET, og
  // App.tsx byggede et nyt literal ved hver render, så hver forældre-render
  // nulstillede indholdet og genhentede filen.
  // ---------------------------------------------------------------------
  it('genhenter IKKE når forælderen sender et nyt config-objekt med samme værdier', async () => {
    const hent = vi.fn().mockResolvedValue(new Response(
      JSON.stringify({ path: 'docs/x.md', content: '# Fil-titel', language: 'markdown' }),
      { status: 200, headers: { 'content-type': 'application/json' } },
    ))
    vi.stubGlobal('fetch', hent)
    const artifact = { kind: 'file' as const, title: 'x.md', filePath: 'docs/x.md' }
    const { rerender } = render(
      <ArtifactPanel artifact={artifact} onClose={() => {}} config={{ apiBaseUrl: 'http://t', authToken: 't' }} />,
    )
    expect(await screen.findByRole('heading', { name: 'Fil-titel' })).toBeTruthy()

    // Tre forældre-renders med FRISKE objekter — præcis det App.tsx gjorde.
    for (let i = 0; i < 3; i++) {
      await act(async () => {
        rerender(
          <ArtifactPanel artifact={artifact} onClose={() => {}} config={{ apiBaseUrl: 'http://t', authToken: 't' }} />,
        )
      })
    }
    expect(hent).toHaveBeenCalledTimes(1)
    // Indholdet står stadig — det var dét der forsvandt.
    expect(screen.getByRole('heading', { name: 'Fil-titel' })).toBeTruthy()
  })

  it('henter igen når filstien faktisk skifter', async () => {
    const hent = vi.fn().mockResolvedValue(new Response(
      JSON.stringify({ path: 'docs/y.md', content: '# Anden', language: 'markdown' }),
      { status: 200, headers: { 'content-type': 'application/json' } },
    ))
    vi.stubGlobal('fetch', hent)
    const cfg = { apiBaseUrl: 'http://t', authToken: 't' }
    const { rerender } = render(
      <ArtifactPanel artifact={{ kind: 'file', title: 'x.md', filePath: 'docs/x.md' }} onClose={() => {}} config={cfg} />,
    )
    await act(async () => {
      rerender(
        <ArtifactPanel artifact={{ kind: 'file', title: 'y.md', filePath: 'docs/y.md' }} onClose={() => {}} config={cfg} />,
      )
    })
    expect(hent).toHaveBeenCalledTimes(2)
  })
})
