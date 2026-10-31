import { describe, it, expect } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ApprovalCard } from './ApprovalCard'

/**
 * Linjen er fast, kommandoen er bag et klik — målt 31/10-2026.
 *
 * Bjørns symptom, gentaget: «skubber chatview op» og «aldrig samme størrelse».
 * Kortet lå i flow oven over composeren med kommandoen i en `<pre>` der havde
 * `max-height: min(40vh, 360px)`. Derfor voksede det fra ~60 px til 360 px,
 * og hver px blev taget fra transcriptet.
 *
 * Det disse tests værner er FORUDSIGELIGHEDEN, ikke et bestemt tal: den
 * kollapsede linje må ikke ændre form når kommandoen bliver længere. Den
 * faktiske højde måles i Chromium (jsdom har ingen layout-motor), men DOM'en
 * kan bevise at indholdet er pakket ind i folden og ikke står frit.
 *
 * Mutationsprøvet: sættes `<pre>` ud af `.approvallinje-krop`, fejler test 1.
 * Sættes folden altid åben (`data-aaben` hårdt til "true"), fejler test 2.
 */
describe('ApprovalCard — folden', () => {
  const grund = {
    approvalId: 'a1',
    tool: 'bash',
    action: 'rm -rf /tmp/x\nog mere tekst her',
    risk: 'medium',
    canApprove: true,
    onApprove: () => {},
    onDeny: () => {},
  }

  it('kommandoen ligger inde i folden, ikke frit i kortet', () => {
    const { container } = render(<ApprovalCard {...grund} />)
    const krop = container.querySelector('.approvallinje-krop')
    expect(krop, 'folden mangler — saa vokser kortet med kommandoen igen').toBeTruthy()
    expect(krop!.querySelector('pre.approvalcard-action')).toBeTruthy()
    // Og den må IKKE ogsaa staa uden for folden: to steder = to højder.
    expect(container.querySelectorAll('pre.approvalcard-action')).toHaveLength(1)
  })

  it('folden starter lukket og åbner på klik', async () => {
    const { container } = render(<ApprovalCard {...grund} />)
    const krop = container.querySelector('.approvallinje-krop')!
    expect(krop.getAttribute('data-aaben')).toBe('false')

    const aabn = screen.getByRole('button', { name: /rm -rf/ })
    expect(aabn.getAttribute('aria-expanded')).toBe('false')

    await userEvent.click(aabn)
    expect(krop.getAttribute('data-aaben')).toBe('true')
    expect(aabn.getAttribute('aria-expanded')).toBe('true')
  })

  it('skjult kommando er inert — man kan ikke tabbe til noget man ikke kan se', () => {
    const { container } = render(<ApprovalCard {...grund} />)
    const pre = container.querySelector('pre.approvalcard-action')!
    expect(pre.hasAttribute('inert')).toBe(true)
  })

  it('åben kommando er ikke inert', async () => {
    const { container } = render(<ApprovalCard {...grund} />)
    await userEvent.click(screen.getByRole('button', { name: /rm -rf/ }))
    const pre = container.querySelector('pre.approvalcard-action')!
    expect(pre.hasAttribute('inert')).toBe(false)
  })

  it('resume-linjen viser kun første linje — ikke hele kommandoen', () => {
    const { container } = render(<ApprovalCard {...grund} />)
    const resume = container.querySelector('.approvallinje-resume')!
    expect(resume.textContent).toBe('rm -rf /tmp/x')
    expect(resume.textContent).not.toContain('og mere tekst')
  })

  it('en meget lang kommando forkortes på linjen', () => {
    const lang = 'a'.repeat(300)
    const { container } = render(<ApprovalCard {...grund} action={lang} />)
    const resume = container.querySelector('.approvallinje-resume')!
    expect(resume.textContent!.length).toBeLessThanOrEqual(72)
    expect(resume.textContent!.endsWith('…')).toBe(true)
  })

  it('knapperne sidder på linjen, ikke inde i folden', () => {
    const { container } = render(<ApprovalCard {...grund} />)
    const linje = container.querySelector('.approvallinje') as HTMLElement
    expect(linje.querySelector('button[class*="approvalcard"]')).toBeNull()
    expect(within(linje).queryByRole('button', { name: /godkend/i })).toBeTruthy()
    const krop = container.querySelector('.approvallinje-krop') as HTMLElement
    expect(within(krop).queryByRole('button', { name: /godkend/i })).toBeNull()
  })
})
