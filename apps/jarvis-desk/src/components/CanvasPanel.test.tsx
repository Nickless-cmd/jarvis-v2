import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import type { Mock } from 'vitest'
import { CanvasPanel } from './CanvasPanel'
import { onCanvasSend, canvasBesked } from '../lib/canvasBus'
import { SessionContext } from '../contexts/SessionContext'
import { foreslaaFortsaettelse } from '../lib/dokumentApi'

vi.mock('../lib/dokumentApi', () => ({
  listDokumenter: vi.fn(),
  opretDokument: vi.fn(),
  opdaterDokument: vi.fn(),
  udgivDokument: vi.fn(),
  foreslaaFortsaettelse: vi.fn(),
}))

import { listDokumenter } from '../lib/dokumentApi'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }

/** Samtale-konteksten er det eneste canvas bruger den til: at kende sessionen. */
const medSamtale = (ui: React.ReactElement) => (
  <SessionContext.Provider value={{ activeId: 's1' } as never}>{ui}</SessionContext.Provider>
)

beforeEach(() => {
  ;(listDokumenter as Mock).mockResolvedValue([
    {
      id: 'doc-1', sessionId: 's1', titel: 'Plan', tekst: 'v1',
      contentType: 'text/markdown', version: 3, opdateret: '',
    },
  ])
  ;(foreslaaFortsaettelse as Mock).mockReset()
})

describe('CanvasPanel', () => {
  let af: (() => void) | null = null
  afterEach(() => { af?.(); af = null })

  it('sender den rettede tekst tilbage til samtalen', () => {
    const modtaget = vi.fn()
    af = onCanvasSend(modtaget)
    render(<CanvasPanel canvas={{ titel: 'Plan', tekst: 'v1' }} />)
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'v2' } })
    fireEvent.click(screen.getByText('Send til samtalen'))
    expect(modtaget).toHaveBeenCalledWith({ titel: 'Plan', tekst: 'v2' })
    expect(canvasBesked({ titel: 'Plan', tekst: 'v2' })).toContain('v2')
  })

  it('siger det højt når ingen samtale lytter', () => {
    render(<CanvasPanel canvas={{ titel: 'Plan', tekst: 'v1' }} />)
    fireEvent.click(screen.getByText('Send til samtalen'))
    expect(screen.getByRole('alert').textContent).toContain('intet blev sendt')
  })

  it('henter IKKE et forslag af sig selv — kun når man beder om det', async () => {
    ;(foreslaaFortsaettelse as Mock).mockResolvedValue('En ny sætning.')
    render(medSamtale(<CanvasPanel canvas={{ titel: 'Plan', tekst: 'v1' }} config={cfg} />))

    await waitFor(() => expect(screen.getByText('Foreslå')).toBeEnabled())

    // Det er hele kontrakten: ingen automatisk hentning. Bjørn 17/9-2026 —
    // grå tekst der kommer dumpende mens man skriver er «virkelig træls».
    expect(foreslaaFortsaettelse).not.toHaveBeenCalled()
    expect(screen.queryByTestId('canvas-forslag')).toBeNull()

    fireEvent.click(screen.getByText('Foreslå'))

    await waitFor(() => expect(screen.getByTestId('canvas-forslag')).toBeTruthy())
    expect(foreslaaFortsaettelse).toHaveBeenCalledWith(cfg, 'doc-1')
    expect(screen.getByText('En ny sætning.')).toBeTruthy()
  })

  it('Indsæt gør forslaget til rigtig tekst, og boksen forsvinder', async () => {
    ;(foreslaaFortsaettelse as Mock).mockResolvedValue('En ny sætning.')
    render(medSamtale(<CanvasPanel canvas={{ titel: 'Plan', tekst: 'v1' }} config={cfg} />))
    await waitFor(() => expect(screen.getByText('Foreslå')).toBeEnabled())

    fireEvent.click(screen.getByText('Foreslå'))
    await waitFor(() => expect(screen.getByText('Indsæt')).toBeTruthy())
    fireEvent.click(screen.getByText('Indsæt'))

    const felt = screen.getByRole('textbox') as HTMLTextAreaElement
    expect(felt.value).toContain('En ny sætning.')
    expect(screen.queryByTestId('canvas-forslag')).toBeNull()
  })

  it('Luk kaster forslaget væk uden at røre teksten', async () => {
    ;(foreslaaFortsaettelse as Mock).mockResolvedValue('En ny sætning.')
    render(medSamtale(<CanvasPanel canvas={{ titel: 'Plan', tekst: 'v1' }} config={cfg} />))
    await waitFor(() => expect(screen.getByText('Foreslå')).toBeEnabled())

    fireEvent.click(screen.getByText('Foreslå'))
    await waitFor(() => expect(screen.getByText('Luk')).toBeTruthy())
    fireEvent.click(screen.getByText('Luk'))

    expect((screen.getByRole('textbox') as HTMLTextAreaElement).value).toBe('v1')
    expect(screen.queryByTestId('canvas-forslag')).toBeNull()
  })

  it('et tomt forslag siges højt i stedet for at se ud som en død knap', async () => {
    ;(foreslaaFortsaettelse as Mock).mockResolvedValue('')
    render(medSamtale(<CanvasPanel canvas={{ titel: 'Plan', tekst: 'v1' }} config={cfg} />))
    await waitFor(() => expect(screen.getByText('Foreslå')).toBeEnabled())

    fireEvent.click(screen.getByText('Foreslå'))
    await waitFor(() =>
      expect(screen.getByRole('status').textContent).toContain('Intet forslag endnu'),
    )
  })
})
