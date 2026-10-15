import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

/**
 * «Opret side-opgave» i miljø-feltet (Bjørn 15/10-2026).
 *
 * Posten står under «Opret pull request» — men den er bevidst IKKE gated på
 * git, og den anden test her holder netop det: en sideopgave har intet med et
 * repo at gøre, så en post der forsvandt i en mappe uden git ville være en tavs
 * udeladelse af præcis den slags huset jagter.
 */
const getGitStatus = vi.fn()
vi.mock('../../lib/api', async (orig) => ({
  ...(await orig() as object),
  getGitStatus: (...a: unknown[]) => getGitStatus(...a),
}))

import { EnvironmentPanel } from './EnvironmentPanel'
const cfg = { apiBaseUrl: 'http://x', authToken: 't' }

describe('EnvironmentPanel — Opret side-opgave', () => {
  beforeEach(() => {
    getGitStatus.mockReset()
    getGitStatus.mockResolvedValue({ is_git: true, branch: 'main', dirty: 0, added: 0, removed: 0 })
  })

  it('posten kalder tilbage så boksen kan åbnes', async () => {
    const aabn = vi.fn()
    render(<EnvironmentPanel config={cfg} kind="container" root="/r" working
      isOwner onOpretSideOpgave={aabn} />)
    await waitFor(() => expect(screen.getByText('main')).toBeInTheDocument())
    await userEvent.click(screen.getByRole('button', { name: 'Opret side-opgave' }))
    expect(aabn).toHaveBeenCalledTimes(1)
  })

  it('kræver ikke git — posten er der også når mappen ikke er et repo', async () => {
    getGitStatus.mockResolvedValue({ is_git: false, branch: '', dirty: 0, added: 0, removed: 0 })
    render(<EnvironmentPanel config={cfg} kind="container" root="/r" working
      isOwner onOpretSideOpgave={vi.fn()} />)
    expect(await screen.findByRole('button', { name: 'Opret side-opgave' })).toBeInTheDocument()
    // Pull request-posten er væk (intet repo) — sideopgave-posten er der stadig.
    expect(screen.queryByRole('button', { name: /Opret pull request/ })).toBeNull()
  })

  it('uden callback vises posten ikke — ingen død knap', async () => {
    render(<EnvironmentPanel config={cfg} kind="container" root="/r" working isOwner />)
    await waitFor(() => expect(screen.getByText('main')).toBeInTheDocument())
    expect(screen.queryByRole('button', { name: 'Opret side-opgave' })).toBeNull()
  })
})
