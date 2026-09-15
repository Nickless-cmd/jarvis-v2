import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { RunsTable } from './RunsTable'
import type { McRun } from '../../../lib/missionControlApi'

/**
 * «Til gennemsyn» = afbrudte kørsler.
 *
 * Bjørn 15/9-2026: «afventer dig mangler til gemmensyn som arbejde havde...
 * eller bliver det vist der os?» — nej. Spanden fandtes kun i den slettede
 * WorkQueue, og «fejlet» dækker failed/cancelled/error, så `interrupted` faldt
 * kun i «alle».
 *
 * Målt på 30 dage: 2.861 completed, 78 INTERRUPTED, 13 failed, 13 cancelled.
 * Afbrudte er den største ikke-færdige kategori.
 */
vi.mock('./RunDetail', () => ({ RunDetail: () => <div /> }))

const kørsler = [
  { run_id: 'r-faerdig', status: 'completed', text_preview: 'faerdig' },
  { run_id: 'r-afbrudt', status: 'interrupted', text_preview: 'halvt arbejde' },
  { run_id: 'r-fejlet', status: 'failed', text_preview: 'gik galt' },
  { run_id: 'r-koerer', status: 'running', text_preview: 'i gang' },
] as unknown as McRun[]

const tegn = () => render(<RunsTable config={undefined} runs={kørsler} />)

describe('Runs-filteret kender afbrudte kørsler', () => {
  it('«til gennemsyn» findes som filter', () => {
    tegn()
    expect(screen.getByRole('button', { name: /til gennemsyn/ })).toBeTruthy()
  })

  it('filteret viser KUN den afbrudte', async () => {
    tegn()
    await userEvent.click(screen.getByRole('button', { name: /til gennemsyn/ }))
    expect(screen.getByText(/halvt arbejde/)).toBeTruthy()
    expect(screen.queryByText(/gik galt/)).toBeNull()
    expect(screen.queryByText(/^faerdig$/)).toBeNull()
  })

  it('«fejlet» tager IKKE den afbrudte med', async () => {
    // Det var hele grunden til at den forsvandt: interrupted er hverken
    // fejlet eller færdigt.
    tegn()
    await userEvent.click(screen.getByRole('button', { name: /^fejlet/ }))
    expect(screen.getByText(/gik galt/)).toBeTruthy()
    expect(screen.queryByText(/halvt arbejde/)).toBeNull()
  })

  it('tallet staar paa knappen, saa man kan se det uden at klikke', () => {
    tegn()
    expect(screen.getByRole('button', { name: /til gennemsyn\s*1/ })).toBeTruthy()
  })

  it('«alle» viser stadig alt', () => {
    tegn()
    expect(screen.getByRole('button', { name: /alle\s*4/ })).toBeTruthy()
  })
})
