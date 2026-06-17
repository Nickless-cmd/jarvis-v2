import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

const exportMyData = vi.fn()
const downloadJson = vi.fn()
vi.mock('../lib/accountApi', () => ({
  exportMyData: (...a: unknown[]) => exportMyData(...a),
  downloadJson: (...a: unknown[]) => downloadJson(...a),
}))

import { DataPrivacyPanel } from './DataPrivacyPanel'

describe('DataPrivacyPanel', () => {
  beforeEach(() => { exportMyData.mockReset(); downloadJson.mockReset() })

  it('navngiver data, Google-scopes og GDPR-rettigheder', () => {
    render(<DataPrivacyPanel />)
    expect(screen.getByText('Data & privatliv')).toBeInTheDocument()
    expect(screen.getByText(/Chat-historik/)).toBeInTheDocument()
    expect(screen.getByText(/Gmail\/Kalender\/Drive/)).toBeInTheDocument()
    expect(screen.getByText(/Dine rettigheder \(GDPR\)/)).toBeInTheDocument()
  })

  it('viser ikke eksport-knap uden config', () => {
    render(<DataPrivacyPanel />)
    expect(screen.queryByText(/Download mine data/)).not.toBeInTheDocument()
  })

  it('eksport-knap henter data + trigger download', async () => {
    exportMyData.mockResolvedValue({ profile: { email: 'x' } })
    render(<DataPrivacyPanel config={{ apiBaseUrl: 'http://x', authToken: 't' }} />)
    fireEvent.click(screen.getByText('Download mine data (JSON)'))
    await waitFor(() => expect(exportMyData).toHaveBeenCalled())
    await waitFor(() => expect(downloadJson).toHaveBeenCalledWith({ profile: { email: 'x' } }, 'jarvis-mine-data.json'))
    expect(await screen.findByText(/blev downloadet/)).toBeInTheDocument()
  })
})
