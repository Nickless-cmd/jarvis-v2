import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ApprovalCard } from './ApprovalCard'

/** Kortets frist — et kort må ikke kunne hænge med døde knapper.
 *
 * Bjørn 25/10-2026: «approval cards må ikk kunne dø et run … eller approval
 * card bliver afvist eller godkendt.» Et kort hvor BEGGE knapper fejler er
 * præcis det der ikke må findes: det ser brugbart ud og er det ikke.
 *
 * `StreamContext` holder op med at spørge når den HAR et kort, så et udløb på
 * serveren blev aldrig opdaget her. Fristen kommer derfor med fra serveren,
 * og kortet skal selv sige til.
 */
describe('ApprovalCard', () => {
  it('renders action text inert and fires onApprove (owner)', async () => {
    const onApprove = vi.fn()
    render(<ApprovalCard approvalId="a1" tool="operator_bash" action={'<b>rm</b>'} risk="destructive" canApprove onApprove={onApprove} onDeny={() => {}} />)
    // `selector: 'pre'`: teksten står nu OGSÅ i resume-linjen (den er hele
    // pointen med den faste højde), men kravet om at den vises INERT gælder
    // `<pre>`-en. Uden selectoren fandt getByText to elementer og fejlede —
    // ikke fordi kontrakten blev brudt, men fordi den blev målt for bredt.
    expect(screen.getByText('<b>rm</b>', { selector: 'pre' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /godkend/i }))
    expect(onApprove).toHaveBeenCalledWith('a1')
  })
  it('member sees read-only (no approve button)', () => {
    render(<ApprovalCard approvalId="a1" tool="x" action="y" risk="normal" canApprove={false} onApprove={() => {}} onDeny={() => {}} />)
    expect(screen.queryByRole('button', { name: /godkend/i })).toBeNull()
  })

  it('viser en nedtælling når fristen er kendt', () => {
    const omFemMin = new Date(Date.now() + 5 * 60_000).toISOString()
    render(<ApprovalCard approvalId="a1" tool="bash" action="ls" risk="medium" canApprove expiresAt={omFemMin} onApprove={() => {}} onDeny={() => {}} />)
    // «4:59 tilbage» e.l. — vi kræver bare at der står noget med «tilbage».
    expect(screen.getByText(/tilbage$/)).toBeInTheDocument()
  })

  it('et udløbet kort viser ingen knapper — de ville fejle alligevel', () => {
    const forEtMinSiden = new Date(Date.now() - 60_000).toISOString()
    render(<ApprovalCard approvalId="a1" tool="bash" action="ls" risk="medium" canApprove expiresAt={forEtMinSiden} onApprove={() => {}} onDeny={() => {}} />)
    expect(screen.queryByRole('button', { name: /godkend/i })).toBeNull()
    expect(screen.queryByRole('button', { name: /afvis/i })).toBeNull()
    expect(screen.getByText(/Fristen løb ud/i)).toBeInTheDocument()
    expect(screen.getByText(/Runnet er afsluttet/i)).toBeInTheDocument()
  })

  it('uden frist virker kortet som før — ingen nedtælling, knapper intakte', async () => {
    const onApprove = vi.fn()
    render(<ApprovalCard approvalId="a1" tool="bash" action="ls" risk="medium" canApprove onApprove={onApprove} onDeny={() => {}} />)
    expect(screen.queryByText(/tilbage$/)).toBeNull()
    await userEvent.click(screen.getByRole('button', { name: /godkend/i }))
    expect(onApprove).toHaveBeenCalledWith('a1')
  })
})
