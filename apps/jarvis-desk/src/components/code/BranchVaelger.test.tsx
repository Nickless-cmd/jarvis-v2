/**
 * Branch-vælgeren (Bjørn 18/9-2026: «main skal osse være dropdown med søge fet
 * øverst og et view med alle branches og i bunden et + ikon til opret og
 * udcheck ny branch»).
 *
 * Før var branchen en ren etiket, og API'et kunne kun svare på hvilken branch
 * man stod på. Testene holder de fire ting kravet består af: søgefeltet
 * øverst, listen, plus-knappen der opretter, og at et skift faktisk sendes.
 */
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

const hentBranches = vi.fn()
const skiftBranch = vi.fn()
vi.mock('../../lib/gitWorkspace', () => ({
  hentBranches: (...a: unknown[]) => hentBranches(...a),
  skiftBranch: (...a: unknown[]) => skiftBranch(...a),
}))

import { BranchVaelger } from './BranchVaelger'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }
const vis = (aktuel = 'main') =>
  render(<BranchVaelger config={cfg} kind="container" root="/r" aktuel={aktuel} />)

describe('branch-vælgeren', () => {
  beforeEach(() => {
    hentBranches.mockReset().mockResolvedValue({
      ok: true, current: 'main', local: ['main', 'feature/ny'], remote: ['origin/gammel'],
    })
    skiftBranch.mockReset().mockResolvedValue({ ok: true, current: 'feature/ny' })
  })

  it('henter FØRST når man åbner — ikke bare for at tegne etiketten', async () => {
    vis()
    expect(hentBranches).not.toHaveBeenCalled()

    fireEvent.click(screen.getByTitle('Skift branch'))
    await waitFor(() => expect(hentBranches).toHaveBeenCalledTimes(1))
  })

  it('viser søgefelt øverst og alle branches', async () => {
    vis()
    fireEvent.click(screen.getByTitle('Skift branch'))

    await screen.findByRole('option', { name: /feature\/ny/ })
    expect(screen.getByLabelText('Søg i branches')).toBeTruthy()
    expect(screen.getByRole('option', { name: /origin\/gammel/ })).toBeTruthy()
  })

  it('søgningen filtrerer listen', async () => {
    vis()
    fireEvent.click(screen.getByTitle('Skift branch'))
    await screen.findByRole('option', { name: /feature\/ny/ })

    fireEvent.change(screen.getByLabelText('Søg i branches'), { target: { value: 'gammel' } })

    expect(screen.queryByRole('option', { name: /feature\/ny/ })).toBeNull()
    expect(screen.getByRole('option', { name: /origin\/gammel/ })).toBeTruthy()
  })

  it('et navn der ikke findes bliver til «opret og skift»', async () => {
    vis()
    fireEvent.click(screen.getByTitle('Skift branch'))
    await screen.findByRole('option', { name: /feature\/ny/ })

    fireEvent.change(screen.getByLabelText('Søg i branches'), { target: { value: 'helt-ny' } })
    const opret = screen.getByRole('button', { name: /Opret og skift til/ })
    fireEvent.click(opret)

    await waitFor(() => expect(skiftBranch).toHaveBeenCalledWith(
      cfg, { kind: 'container', root: '/r', name: 'helt-ny', create: true },
    ))
  })

  it('et klik på en eksisterende branch skifter uden at oprette', async () => {
    vis()
    fireEvent.click(screen.getByTitle('Skift branch'))
    fireEvent.click(await screen.findByRole('option', { name: /feature\/ny/ }))

    await waitFor(() => expect(skiftBranch).toHaveBeenCalledWith(
      cfg, { kind: 'container', root: '/r', name: 'feature/ny', create: false },
    ))
  })

  it('siger det højt hvis skiftet ikke lykkedes', async () => {
    skiftBranch.mockResolvedValue({ ok: false, error: 'uncommitted changes' })
    vis()
    fireEvent.click(screen.getByTitle('Skift branch'))
    fireEvent.click(await screen.findByRole('option', { name: /feature\/ny/ }))

    expect(await screen.findByText('uncommitted changes')).toBeTruthy()
  })

  // Bjørn 18/9-2026: «main dropdown fejler med kunne ikke indlæse branches».
  // Den besked var husets egen. Den dækkede over broen nede, en mappe der ikke
  // findes, og en mappe der ikke er et repo — og kun den ene af dem kan han
  // selv rette. Serverens grund skal hele vejen op på skærmen.
  it('viser serverens grund, ikke husets generiske besked', async () => {
    hentBranches.mockResolvedValue({
      ok: false, current: '', local: [], remote: [],
      error: 'broen: bridge_disconnected',
    })
    vis()
    fireEvent.click(screen.getByTitle('Skift branch'))

    expect(await screen.findByText('broen: bridge_disconnected')).toBeTruthy()
    expect(screen.queryByText('Kunne ikke læse branches')).toBeNull()
  })

  it('falder tilbage til den generiske besked når serveren intet siger', async () => {
    hentBranches.mockResolvedValue({ ok: false, current: '', local: [], remote: [] })
    vis()
    fireEvent.click(screen.getByTitle('Skift branch'))

    expect(await screen.findByText('Kunne ikke læse branches')).toBeTruthy()
  })
})
