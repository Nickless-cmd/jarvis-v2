import { describe, it, expect } from 'vitest'
import { JarvisRing } from './JarvisRing'
import { render } from '@testing-library/react'
import { PresenceDot } from './PresenceDot'

describe('PresenceDot', () => {
  it('keeps Puls visible and stops animation when work finishes', () => {
    const { container, rerender, getByLabelText } = render(<PresenceDot status="working" />)
    expect(getByLabelText('Jarvis arbejder…')).toBeTruthy()
    expect(container.querySelector('.jarvis-pulse.is-working')).not.toBeNull()
    rerender(<PresenceDot status="done" />)
    expect(getByLabelText('Jarvis')).toBeTruthy()
    expect(container.querySelector('.jarvis-pulse')).not.toBeNull()
    expect(container.querySelector('.is-working')).toBeNull()
  })
  it.each(['error', 'interrupted'])('preserves the interrupted signal for %s', (status) => {
    const { container, getByLabelText } = render(<PresenceDot status={status} />)
    expect(getByLabelText('Afbrudt')).toBeTruthy()
    expect(container.querySelector('.jarvis-pulse.is-error')).not.toBeNull()
    expect(container.querySelector('.is-working')).toBeNull()
  })
})

/* ── Loaders går i fase (spec punkt 8, 30/9-2026) ───────────────────────────
 *
 * En CSS-animation starter når elementet monteres. Fire mærker monteret på
 * fire tidspunkter puster derfor forskudt, og det ser forkert ud på en måde
 * der er svær at pege på. Rettelsen er en negativ `animation-delay` regnet
 * ud af dokument-tiden.
 */
describe('JarvisRing — fase', () => {
  it('sætter en NEGATIV fase på mærket', () => {
    const { container } = render(<JarvisRing spinning />)
    const v = (container.querySelector('.jarvis-pulse') as HTMLElement)?.style
      .getPropertyValue('--fase')
    expect(v).toMatch(/^-?\d+(\.\d+)?ms$/)
    expect(Number(v.replace('ms', ''))).toBeLessThanOrEqual(0)
  })

  it('fasen ændrer sig IKKE ved en ny render — det ville genstarte animationen', () => {
    const { container, rerender } = render(<JarvisRing spinning />)
    const el = () => (container.querySelector('.jarvis-pulse') as HTMLElement)
      .style.getPropertyValue('--fase')
    const før = el()
    rerender(<JarvisRing spinning size={30} />)
    expect(el()).toBe(før)
  })
})
