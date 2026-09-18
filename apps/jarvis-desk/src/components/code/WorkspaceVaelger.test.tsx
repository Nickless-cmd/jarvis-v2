/**
 * Workspace-vælgeren (Bjørn 18/9-2026: «workstation skal være en dropdown hvor
 * man kan vælge trusted folder og ny lokal worktree»).
 *
 * Før var det en ren etiket. De to ting i menuen er forskellige af natur: en
 * betroet mappe VÆLGES, en ny worktree OPRETTES — og testene holder begge.
 */
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

const hentBetroedeMapper = vi.fn()
const opretWorktree = vi.fn()
vi.mock('../../lib/gitWorkspace', () => ({
  hentBetroedeMapper: (...a: unknown[]) => hentBetroedeMapper(...a),
  opretWorktree: (...a: unknown[]) => opretWorktree(...a),
}))

import { WorkspaceVaelger } from './WorkspaceVaelger'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }

describe('workspace-vælgeren', () => {
  beforeEach(() => {
    hentBetroedeMapper.mockReset().mockResolvedValue([
      { kind: 'workstation', root: '/media/projects/jarvis-v2', trusted_at: 'a' },
      { kind: 'workstation', root: '/home/bs/andet', trusted_at: 'b' },
    ])
    opretWorktree.mockReset().mockResolvedValue({ ok: true, path: '.worktrees/sidespor' })
  })

  const vis = (onVaelg = vi.fn()) => {
    render(
      <WorkspaceVaelger
        config={cfg} kind="workstation" root="/media/projects/jarvis-v2" onVaelg={onVaelg}
      />,
    )
    return onVaelg
  }

  it('lister de betroede mapper når man åbner', async () => {
    vis()
    fireEvent.click(screen.getByTitle('Vælg arbejdsmappe'))

    expect(await screen.findByText('/home/bs/andet')).toBeTruthy()
    expect(screen.getByText('Ny lokal worktree')).toBeTruthy()
  })

  it('et valg giver mappen videre', async () => {
    const onVaelg = vis()
    fireEvent.click(screen.getByTitle('Vælg arbejdsmappe'))
    fireEvent.click(await screen.findByText('/home/bs/andet'))

    expect(onVaelg).toHaveBeenCalledWith({ kind: 'workstation', root: '/home/bs/andet' })
  })

  it('opretter en worktree og peger på den FULDE sti', async () => {
    const onVaelg = vis()
    fireEvent.click(screen.getByTitle('Vælg arbejdsmappe'))
    await screen.findByText('Ny lokal worktree')

    fireEvent.change(screen.getByLabelText('Navn på ny worktree'), { target: { value: 'sidespor' } })
    fireEvent.click(screen.getByRole('button', { name: /Opret worktree/ }))

    await waitFor(() => expect(opretWorktree).toHaveBeenCalledWith(
      cfg, { kind: 'workstation', root: '/media/projects/jarvis-v2', name: 'sidespor' },
    ))
    // Serveren svarer med en sti RELATIV til repoet; vælgeren skal gøre den hel,
    // ellers peger den på ingenting.
    expect(onVaelg).toHaveBeenCalledWith({
      kind: 'workstation', root: '/media/projects/jarvis-v2/.worktrees/sidespor',
    })
  })

  it('opret-knappen er død uden et navn', async () => {
    vis()
    fireEvent.click(screen.getByTitle('Vælg arbejdsmappe'))
    await screen.findByText('Ny lokal worktree')

    expect(screen.getByRole('button', { name: /Opret worktree/ })).toBeDisabled()
  })

  it('siger det højt hvis oprettelsen fejler', async () => {
    opretWorktree.mockResolvedValue({ ok: false, error: 'findes allerede' })
    vis()
    fireEvent.click(screen.getByTitle('Vælg arbejdsmappe'))
    await screen.findByText('Ny lokal worktree')

    fireEvent.change(screen.getByLabelText('Navn på ny worktree'), { target: { value: 'x' } })
    fireEvent.click(screen.getByRole('button', { name: /Opret worktree/ }))

    expect(await screen.findByText('findes allerede')).toBeTruthy()
  })
})
