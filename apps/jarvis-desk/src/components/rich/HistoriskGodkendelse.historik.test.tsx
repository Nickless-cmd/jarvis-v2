import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { HistoriskGodkendelse, type GodkendelsesHaendelse } from './HistoriskGodkendelse'

/**
 * Rækken i transcriptet er HISTORIK — og kan ikke besvares.
 *
 * 16/11-2026. Kontrakten er vendt tilbage til udgangspunktet, fordi den første
 * version af DEL 3 (31/10) gjorde rækken til den PRIMAERE flade. Bjørn:
 * «approval cards lander over turhoved og ikk over composer som de skulle???
 * hver gang der kommer en skal jeg scrolle til toppen af din tur for at
 * godkende!»
 *
 * Han havde ret: spørgsmålet stod øverst i turen og skulle FINDES, ikke bare
 * besvares. Det flydende kort i `.composer-notices` er nu den eneste flade
 * med knapper, og det ligger uden for scroll-containeren.
 *
 * Den farlige fejl er stadig den samme, bare spejlet: at en række får knapper
 * igen. Så står den samme godkendelse to steder, og det ene sted skal man
 * scrolle til.
 */

const afgjort: GodkendelsesHaendelse = {
  approval_id: 'a1',
  tool: 'bash',
  action: 'rm -rf /tmp/x',
  status: 'approved',
}

const venter: GodkendelsesHaendelse = { ...afgjort, status: 'pending' }

describe('HistoriskGodkendelse — ren historik', () => {
  it('en afgjort række viser sin status som tekst', () => {
    render(<HistoriskGodkendelse data={afgjort} />)
    expect(screen.getByText(/godkendt/i)).toBeInTheDocument()
  })

  it('en ventende række har INGEN knapper — heller ikke naar den venter lige nu', () => {
    // Kernen i rettelsen: raekken maa ikke kunne besvares. Kan den det, er der
    // to steder at svare, og det ene er det man skal scrolle til.
    render(<HistoriskGodkendelse data={venter} />)
    expect(screen.queryByRole('button', { name: /godkend/i })).toBeNull()
    expect(screen.queryByRole('button', { name: /afvis/i })).toBeNull()
    expect(screen.getByText(/afventer/i)).toBeInTheDocument()
  })

  it('holder rå kommando helt ude af kortets layout', () => {
    render(<HistoriskGodkendelse data={venter} />)
    expect(document.querySelector('.approval-details-dialog')).toBeNull()
    expect(screen.queryByText('rm -rf /tmp/x', { selector: 'pre' })).toBeNull()
  })

  it('åbner kommandoen i en modal detalje-dialog', async () => {
    render(<HistoriskGodkendelse data={venter} />)
    await userEvent.click(screen.getByRole('button', { name: /vis detaljer for bash/i }))
    const dialog = screen.getByRole('dialog', { name: 'bash' })
    expect(dialog).toBeInTheDocument()
    expect(screen.getByText('rm -rf /tmp/x', { selector: 'pre' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Luk detaljer' }))
    expect(screen.queryByRole('dialog')).toBeNull()
  })

  it('tegnes altid som historik — aldrig som live', () => {
    const { container } = render(<HistoriskGodkendelse data={venter} />)
    expect(container.querySelector('.approvalcard-historik')).not.toBeNull()
    expect(container.querySelector('.approvalcard-live')).toBeNull()
    expect(container.querySelector('.approvalcard-actionbar')).toBeNull()
  })
})
