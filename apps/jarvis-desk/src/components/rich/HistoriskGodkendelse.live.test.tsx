import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { HistoriskGodkendelse, type GodkendelsesHaendelse } from './HistoriskGodkendelse'

/**
 * DEL 3 — rækken i transcriptet ER fladen.
 *
 * 31/10-2026. Kortet laa i `.composer-area` og skubbede samtalen op. Bjørns
 * ord: «skubber chatview op» og «aldrig samme størrelse». Nu ligger det som en
 * række i samtalen — men en persisteret række er historik og kan ikke besvares.
 *
 * Derfor to tilstande, og de skal ikke blandes sammen:
 *
 *   historik  — status som tekst, ingen knapper. Serveren har fejet posten.
 *   live      — knapper, fordi det ER den godkendelse der venter lige nu.
 *
 * Den farlige fejl er den modsatte af den man forventer: at en AFGJORT række
 * får knapper. Så ser et gammelt svar ud som et åbent spørgsmål, og man kan
 * klikke på noget der ikke findes længere.
 */

const afgjort: GodkendelsesHaendelse = {
  approval_id: 'a1',
  tool: 'bash',
  action: 'rm -rf /tmp/x',
  status: 'approved',
}

const venter: GodkendelsesHaendelse = { ...afgjort, status: 'pending' }

describe('HistoriskGodkendelse — live vs. historik', () => {
  it('en afgjort række har ingen knapper', () => {
    render(<HistoriskGodkendelse data={afgjort} />)
    expect(screen.queryByRole('button', { name: /godkend/i })).toBeNull()
    expect(screen.queryByRole('button', { name: /afvis/i })).toBeNull()
    expect(screen.getByText(/godkendt/i)).toBeInTheDocument()
  })

  it('en ventende række UDEN live-tilstand har stadig ingen knapper', () => {
    // Historik fra en tidligere session kan have status `pending` — runnet døde
    // før nogen svarede. Den må ikke se besvarlig ud.
    render(<HistoriskGodkendelse data={venter} />)
    expect(screen.queryByRole('button', { name: /godkend/i })).toBeNull()
  })

  it('den ventende række MED live-tilstand får knapper', () => {
    render(
      <HistoriskGodkendelse
        data={venter}
        live={{ canApprove: true, onApprove: vi.fn(), onDeny: vi.fn() }}
      />,
    )
    expect(screen.getByRole('button', { name: /godkend/i })).toBeEnabled()
    expect(screen.getByRole('button', { name: /afvis/i })).toBeEnabled()
  })

  it('knapperne sender det RIGTIGE approval_id', async () => {
    const onApprove = vi.fn()
    const onDeny = vi.fn()
    render(
      <HistoriskGodkendelse
        data={venter}
        live={{ canApprove: true, onApprove, onDeny }}
      />,
    )
    await userEvent.click(screen.getByRole('button', { name: /godkend/i }))
    expect(onApprove).toHaveBeenCalledWith('a1')
    await userEvent.click(screen.getByRole('button', { name: /afvis/i }))
    expect(onDeny).toHaveBeenCalledWith('a1')
  })

  it('en afgjort række faar ikke knapper selv om den sendes som live', () => {
    // Baandet skal holdes i komponenten, ikke kun i kalderen: status er
    // sandheden om hvorvidt der kan svares.
    render(
      <HistoriskGodkendelse
        data={afgjort}
        live={{ canApprove: true, onApprove: vi.fn(), onDeny: vi.fn() }}
      />,
    )
    expect(screen.queryByRole('button', { name: /godkend/i })).toBeNull()
  })

  it('kommandoen er i DOM men foldet sammen — linjen har fast højde', () => {
    render(<HistoriskGodkendelse data={venter} />)
    const krop = document.querySelector('.approvallinje-krop')
    expect(krop?.getAttribute('data-aaben')).toBe('false')
    // Teksten skal kunne findes (skærmlæsere, tests) — ikke display:none.
    // Opslaget er praeciseret til <pre>'en: kommandoen staar OGSAA i
    // resume-linjen, og et bredt opslag rammer begge (samme fælde som
    // ApprovalCard-testen).
    expect(screen.getByText('rm -rf /tmp/x', { selector: 'pre' })).toBeInTheDocument()
  })

  it('folden aabner paa klik', async () => {
    render(<HistoriskGodkendelse data={venter} />)
    await userEvent.click(screen.getByRole('button', { name: /vis kommandoen/i }))
    expect(document.querySelector('.approvallinje-krop')?.getAttribute('data-aaben')).toBe('true')
  })
})
