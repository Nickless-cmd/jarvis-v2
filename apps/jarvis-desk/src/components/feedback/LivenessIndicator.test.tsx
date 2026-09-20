import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent, cleanup } from '@testing-library/react'
import { LivenessIndicator } from './LivenessIndicator'
import type { ContentBlock } from '../../lib/sseProtocol'

/**
 * Liveness-linjen, fire ting Bjørn bad om 20/9-2026:
 *
 *  1. Sektionerne klippes, så et langt run ikke gør linjen tre linjer høj.
 *  2. Komprimering er en TILSTAND i linjen — ikke et banner ved siden af.
 *  3. I hvile med kørende baggrundsjob bærer linjen KUN job-tallet.
 *  4. Bølgen gennem hele linjen er CSS (app.css), ikke testbar her — men
 *     prikkernes farve er, og den er teal nu.
 */
const tool = (name: string): ContentBlock => ({ type: 'tool_use', name, id: name } as ContentBlock)

/** Otte familier — nok til at klippet bider. */
const LANGT_RUN: ContentBlock[] = [
  tool('read_file'), tool('read_file'), tool('edit_file'), tool('search'),
  tool('find_files'), tool('web_search'), tool('bash'), tool('remember_this'),
]

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

describe('LivenessIndicator · sektionerne klippes', () => {
  it('viser «og N andre» i stedet for at lade linjen vokse', () => {
    cleanup()
    vis({ status: 'working', elapsedMs: 754_000, tokens: 45_200, blocks: LANGT_RUN })
    // 7 familier → 2 vises, 5 samles. (Ledene pakkes i spans med « · » foran,
    // så vi matcher på delstreng — ikke på hele elementets tekst.)
    expect(screen.getByText(/og 5 andre/)).toBeInTheDocument()
    // Den første er med — rækkefølgen er CC's: mest fortællende først.
    // Nutid mens runnet kører.
    expect(screen.getByText(/Redigerer 1 fil/)).toBeInTheDocument()
  })

  it('klipper ikke når der er få sektioner', () => {
    cleanup()
    vis({ status: 'working', blocks: [tool('read_file'), tool('edit_file')] })
    expect(screen.queryByText(/andre/)).toBeNull()
  })
})

describe('LivenessIndicator · komprimering er en tilstand', () => {
  it('viser komprimerings-teksten i selve linjen', () => {
    cleanup()
    const { container } = vis({ status: 'working', compacting: true, blocks: LANGT_RUN })
    expect(screen.getByText(/Komprimerer kontekst/)).toBeInTheDocument()
    // ÉN linje — ikke to stablede .liveness-elementer.
    expect(container.querySelectorAll('.liveness')).toHaveLength(1)
    expect(container.querySelector('.liveness')?.className).toContain('is-compacting')
  })
})

describe('LivenessIndicator · job-linjen i hvile', () => {
  it('bærer KUN job-tallet når intet run kører men jobs gør', () => {
    cleanup()
    const { container } = vis({ status: 'idle', runningJobs: 2, tokens: 45_200, blocks: LANGT_RUN })
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
