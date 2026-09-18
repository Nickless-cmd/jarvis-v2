/**
 * Arbejdsmappe-vælgeren (Bjørn 18/9-2026).
 *
 * Første udgave læste serverens `workspace_trust`-tabel. Det var FORKERT
 * kilde: den havde ti rækker fra juni-juli med `C:\` og
 * `/Users/bjornslot/Documents` — mapper fra andre maskiner og et andet
 * styresystem. Bjørn sagde det direkte: «trusted folder i workstation er på
 * min maskine».
 *
 * Kilden er nu de mapper der faktisk HAR været valgt i desk, plus den native
 * vælger. Testene pinner den kilde, fordi det var selve fejlen.
 */
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

const opretWorktree = vi.fn()
vi.mock('../../lib/gitWorkspace', () => ({
  opretWorktree: (...a: unknown[]) => opretWorktree(...a),
}))

import { WorkspaceVaelger } from './WorkspaceVaelger'
import { husArbejdsmappe } from '../../lib/arbejdsmapper'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }
const ROD = '/media/projects/jarvis-v2'

const vis = (props: Record<string, unknown> = {}) => {
  const onVaelg = vi.fn()
  render(
    <WorkspaceVaelger
      config={cfg} kind="workstation" root={ROD} onVaelg={onVaelg} {...props}
    />,
  )
  return onVaelg
}
const åbn = () => fireEvent.click(screen.getByTitle(ROD))

describe('arbejdsmappe-vælgeren', () => {
  beforeEach(() => {
    localStorage.clear()
    opretWorktree.mockReset().mockResolvedValue({ ok: true, path: '.worktrees/sidespor' })
  })

  it('viser mappens navn, ikke «Workstation»', () => {
    vis()
    expect(screen.getByTitle(ROD).textContent).toContain('jarvis-v2')
  })

  it('lister de mapper der HAR været valgt på maskinen', () => {
    husArbejdsmappe('/home/bs/andet')
    vis()
    åbn()

    expect(screen.getByText('Mapper på din maskine')).toBeTruthy()
    expect(screen.getByText('/home/bs/andet')).toBeTruthy()
    // Den aktuelle mappe skal selv stå der, også første gang.
    expect(screen.getByText(ROD)).toBeTruthy()
  })

  it('et valg giver mappen videre', () => {
    husArbejdsmappe('/home/bs/andet')
    const onVaelg = vis()
    åbn()
    fireEvent.click(screen.getByText('/home/bs/andet'))

    expect(onVaelg).toHaveBeenCalledWith({ kind: 'workstation', root: '/home/bs/andet' })
  })

  it('åbner den native vælger og husker det den får', async () => {
    const onVaelgMappe = vi.fn().mockResolvedValue('/home/bs/nyt')
    const onVaelg = vis({ onVaelgMappe })
    åbn()
    fireEvent.click(screen.getByRole('button', { name: /Vælg en anden mappe/ }))

    await waitFor(() => expect(onVaelg).toHaveBeenCalledWith({
      kind: 'workstation', root: '/home/bs/nyt',
    }))
  })

  it('opretter en worktree og peger på den FULDE sti', async () => {
    const onVaelg = vis()
    åbn()
    fireEvent.change(screen.getByLabelText('Navn på ny worktree'), { target: { value: 'sidespor' } })
    fireEvent.click(screen.getByRole('button', { name: /Opret worktree/ }))

    await waitFor(() => expect(opretWorktree).toHaveBeenCalledWith(
      cfg, { kind: 'workstation', root: ROD, name: 'sidespor' },
    ))
    // Serveren svarer med en sti RELATIV til repoet; uden at gøre den hel
    // ville den pege på ingenting.
    expect(onVaelg).toHaveBeenCalledWith({
      kind: 'workstation', root: `${ROD}/.worktrees/sidespor`,
    })
  })

  it('siger det højt hvis oprettelsen fejler', async () => {
    opretWorktree.mockResolvedValue({ ok: false, error: 'findes allerede' })
    vis()
    åbn()
    fireEvent.change(screen.getByLabelText('Navn på ny worktree'), { target: { value: 'x' } })
    fireEvent.click(screen.getByRole('button', { name: /Opret worktree/ }))

    expect(await screen.findByText('findes allerede')).toBeTruthy()
  })
})
