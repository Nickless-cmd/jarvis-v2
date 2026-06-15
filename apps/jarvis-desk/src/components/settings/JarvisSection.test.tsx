import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

const getJarvisOverview = vi.fn()
const setVisibleModel = vi.fn().mockResolvedValue(undefined)
vi.mock('../../lib/coworkApi', () => ({
  getJarvisOverview: (...a: unknown[]) => getJarvisOverview(...a),
  setVisibleModel: (...a: unknown[]) => setVisibleModel(...a),
}))

import { JarvisSection } from './JarvisSection'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }

describe('JarvisSection', () => {
  beforeEach(() => { getJarvisOverview.mockReset(); setVisibleModel.mockClear() })

  it('viser lane-modeller og vælger visible-model', async () => {
    getJarvisOverview.mockResolvedValue({
      lanes: [
        { lane: 'visible', provider: 'ollama', model: 'glm-5.1', active: true, credentials_ready: true },
        { lane: 'cheap', provider: 'free', model: 'qwen', active: true, credentials_ready: true },
      ],
      visible_options: [
        { provider: 'ollama', model: 'glm-5.1' },
        { provider: 'deepseek', model: 'v4-flash' },
      ],
    })
    render(<JarvisSection config={cfg} />)
    await waitFor(() => expect(screen.getAllByText(/glm-5.1/).length).toBeGreaterThanOrEqual(1))
    const sel = screen.getByLabelText(/synlig model/i)
    fireEvent.change(sel, { target: { value: 'deepseek|v4-flash' } })
    await waitFor(() => expect(setVisibleModel).toHaveBeenCalledWith(cfg, 'deepseek', 'v4-flash'))
  })
})
