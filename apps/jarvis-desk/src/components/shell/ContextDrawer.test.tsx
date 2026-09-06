import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ContextDrawer } from './ContextDrawer'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }

vi.mock('../../lib/coworkApi', () => ({
  getKontekst: vi.fn(async () => ({
    har_data: true,
    filer: ['SOUL.md', 'USER.md'],
    udeladt: [],
    kilder: ['memory recall bundle', 'inner life'],
    tegn: 37260,
    dele: 52,
  })),
}))

describe('ContextDrawer', () => {
  it('viser målte tal, ikke runde estimater', async () => {
    render(<ContextDrawer config={cfg} />)
    // 37260 tegn / 4 ≈ 9315 tokens → 9,3k
    await waitFor(() => expect(screen.getByText(/2 filer · 2 kilder · ~9\.3k/)).toBeTruthy())
  })
})

describe('ContextDrawer uden data', () => {
  it('viser intet frem for en tom ramme', async () => {
    const { getKontekst } = await import('../../lib/coworkApi')
    ;(getKontekst as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      har_data: false, filer: [], udeladt: [], kilder: [], tegn: 0, dele: 0,
    })
    const { container } = render(<ContextDrawer config={cfg} />)
    await waitFor(() => expect(container.querySelector('.ctx-drawer')).toBeNull())
  })
})
