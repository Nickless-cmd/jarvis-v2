import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent, cleanup } from '@testing-library/react'
import { LivenessIndicator } from './LivenessIndicator'

/** 29/9-2026: liveness er nu en kort tilstandslinje. Arbejdet står i tur-headeren. */

function vis(props: Partial<Parameters<typeof LivenessIndicator>[0]> = {}) {
  return render(
    <LivenessIndicator
      status="idle"
      elapsedMs={0}
      density="compact"
      {...props}
    />,
  )
}

describe('LivenessIndicator · kort status over composeren', () => {
  it('gentager ikke tur-headerens fil- og værktøjsaktivitet', () => {
    cleanup()
    const { container } = vis({ status: 'working', elapsedMs: 754_000, tokens: 45_200, thoughtMs: 1000, thoughtAfsluttet: true })
    expect(container.textContent).toContain('45.2k tokens')
    expect(container.textContent).toContain('Thought for 1s')
    expect(container.textContent).not.toMatch(/Redigerer|læser|andre/)
    expect(container.querySelector('.liveness-arbjede')).toBeNull()
  })
})

describe('LivenessIndicator · komprimering er en tilstand', () => {
  it('viser komprimerings-teksten i selve linjen', () => {
    cleanup()
    const { container } = vis({ status: 'working', compacting: true })
    expect(screen.getByText(/Komprimerer kontekst/)).toBeInTheDocument()
    // ÉN linje — ikke to stablede .liveness-elementer.
    expect(container.querySelectorAll('.liveness')).toHaveLength(1)
    expect(container.querySelector('.liveness')?.className).toContain('is-compacting')
  })
})

describe('LivenessIndicator · job-linjen i hvile', () => {
  it('bærer KUN job-tallet når intet run kører men jobs gør', () => {
    cleanup()
    const { container } = vis({ status: 'idle', runningJobs: 2, tokens: 45_200 })
    expect(screen.getByText('2 jobs kører')).toBeInTheDocument()
    // Runets rester er væk: ingen tokens, ingen verbum, ingen sektioner.
    expect(screen.queryByText(/tokens/)).toBeNull()
    expect(screen.queryByText('klar')).toBeNull()
    expect(container.querySelector('.liveness')?.className).toContain('is-jobs')
  })

  it('ental ved ét job', () => {
    cleanup()
    vis({ status: 'idle', runningJobs: 1 })
    expect(screen.getByText('1 job kører')).toBeInTheDocument()
  })

  it('linjen er ikke en job-linje når intet kører', () => {
    cleanup()
    const { container } = vis({ status: 'idle', runningJobs: 0 })
    expect(container.querySelector('.liveness')?.className).not.toContain('is-jobs')
  })
})

describe('BilledLightbox · fuld størrelse', () => {
  it('åbner på klik, lukker på Escape og på klik udenfor', async () => {
    const { KlikbartBillede } = await import('../rich/BilledLightbox')
    cleanup()
    const { container } = render(<KlikbartBillede src="https://x/i.png" alt="diagram" />)
    expect(screen.queryByRole('dialog')).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: /Åbn diagram/ }))
    expect(screen.getByRole('dialog')).toBeInTheDocument()

    fireEvent.keyDown(window, { key: 'Escape' })
    expect(screen.queryByRole('dialog')).toBeNull()

    // Klik på baggrunden (dialogen selv) lukker igen.
    fireEvent.click(screen.getByRole('button', { name: /Åbn diagram/ }))
    fireEvent.click(screen.getByRole('dialog'))
    expect(screen.queryByRole('dialog')).toBeNull()
    expect(container.querySelector('.billed-knap')).not.toBeNull()
  })
})
