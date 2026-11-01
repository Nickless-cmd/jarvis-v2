import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { HistoriskGodkendelse } from './HistoriskGodkendelse'
import type { GodkendelsesHaendelse } from '../../lib/godkendelseIFolden'

/**
 * UDFALDET, IKKE AFGØRELSEN (1/11-2026).
 *
 * Bjørn: «og hvis godkendelsen ikk gik igennem? det ved kun du = så skal det
 * osse fikses».
 *
 * Beviset lå i basen: `approval-c48e924bff23` blev godkendt 28/10 kl. 14:38:07
 * og erklæret `outcome_unknown` kl. 16:43:15. `approval_claims` havde svaret
 * hele tiden — samtalen fik det aldrig.
 *
 * Serveren skriver nu en tredje række når udfaldet ikke er det gode. Denne
 * test vogter den anden halvdel: at rækken ikke falder i `ukendt` og viser
 * `failed` som en rå engelsk streng midt i et dansk svar.
 */

function haendelse(over: Partial<GodkendelsesHaendelse> = {}): GodkendelsesHaendelse {
  return {
    approval_id: 'approval-test',
    tool: 'bash',
    action: 'rm -rf /tmp/x',
    status: 'approved',
    ...over,
  }
}

describe('HistoriskGodkendelse — udfaldet har sin egen tekst', () => {
  it('viser «Godkendt» når kommandoen gik igennem', () => {
    render(<HistoriskGodkendelse data={haendelse({ status: 'approved' })} />)
    expect(screen.getByText('Godkendt')).toBeInTheDocument()
  })

  it('viser «Kørte ikke igennem» — ikke den rå streng «failed»', () => {
    render(<HistoriskGodkendelse data={haendelse({ status: 'failed' })} />)
    expect(screen.getByText('Kørte ikke igennem')).toBeInTheDocument()
    expect(screen.queryByText('failed')).toBeNull()
  })

  it('viser «Udfald ukendt» — den tilstand der kostede to timers løgn', () => {
    render(<HistoriskGodkendelse data={haendelse({ status: 'outcome_unknown' })} />)
    expect(screen.getByText('Udfald ukendt')).toBeInTheDocument()
    expect(screen.queryByText('outcome_unknown')).toBeNull()
  })

  it('viser «Kørte aldrig» når runnet døde før afsendelsen', () => {
    render(
      <HistoriskGodkendelse data={haendelse({ status: 'aborted_before_dispatch' })} />,
    )
    expect(screen.getByText('Kørte aldrig')).toBeInTheDocument()
  })

  it('en afgjort række får ALDRIG knapper, uanset hvad kalderen sender', () => {
    // Baandet holdes i komponenten, ikke kun hos kalderen: ellers kunne et
    // gammelt svar se ud som et åbent spørgsmål.
    render(
      <HistoriskGodkendelse
        data={haendelse({ status: 'failed' })}
        live={{ canApprove: true, onApprove: () => {}, onDeny: () => {} }}
      />,
    )
    expect(screen.queryByText('Godkend')).toBeNull()
    expect(screen.getByText('Kørte ikke igennem')).toBeInTheDocument()
  })
})
