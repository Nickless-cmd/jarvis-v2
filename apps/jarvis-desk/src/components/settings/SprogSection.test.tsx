import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

const getAccountMe = vi.fn()
const setAccountLanguage = vi.fn().mockResolvedValue(undefined)
vi.mock('../../lib/coworkApi', () => ({
  getAccountMe: (...a: unknown[]) => getAccountMe(...a),
  setAccountLanguage: (...a: unknown[]) => setAccountLanguage(...a),
}))

import { SprogSection } from './SprogSection'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }

describe('SprogSection', () => {
  beforeEach(() => { getAccountMe.mockReset(); setAccountLanguage.mockClear() })

  it('viser nuværende sprog og skifter det', async () => {
    getAccountMe.mockResolvedValue({ user_id: 'u1', email: '', email_verified: true, language: 'da', role: 'owner', tier: 'owner' })
    render(<SprogSection config={cfg} />)
    const sel = await screen.findByLabelText(/sprog/i)
    expect((sel as HTMLSelectElement).value).toBe('da')
    fireEvent.change(sel, { target: { value: 'en' } })
    await waitFor(() => expect(setAccountLanguage).toHaveBeenCalledWith(cfg, 'en'))
  })
})
