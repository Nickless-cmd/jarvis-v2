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

/**
 * «Privatliv & cookies» stod under skrivefeltet, men linket åbnede bare
 * indstillinger, og ordet cookies optrådte ingen steder i panelet. En
 * overskrift der lover noget siden ikke svarer på, er værre end ingen.
 */
describe('cookies og adgang', () => {
  it('svarer på cookie-spørgsmålet — og svaret er nul', () => {
    // Efterprøvet i kilden 8/9-2026: intet `document.cookie`, ingen
    // cookie-baseret auth, ingen analytics. Så det er dét siden siger.
    render(<DataPrivacyPanel />)
    expect(screen.getByText('Cookies')).toBeInTheDocument()
    expect(screen.getByText(/bruger ingen cookies/i)).toBeInTheDocument()
  })

  it('siger hvad der FAKTISK ligger på maskinen', () => {
    render(<DataPrivacyPanel />)
    expect(screen.getByText(/adgangstoken/i)).toBeInTheDocument()
    expect(screen.getByText(/Ingen indhold/i)).toBeInTheDocument()
  })

  it('siger hvad Jarvis kan gøre på maskinen — og at der ikke spørges', () => {
    // Den ubehagelige, men sande linje. `approvalRace` i broen er eksporteret
    // og har nul kaldere, så app'en spørger IKKE pr. handling; godkendelser
    // håndhæves på serveren. En privatlivsside der påstod andet ville lyve.
    render(<DataPrivacyPanel />)
    expect(screen.getByText(/Hvad Jarvis kan gøre på denne maskine/)).toBeInTheDocument()
    expect(screen.getByText(/spørger dig ikke om lov for hver handling/i)).toBeInTheDocument()
  })
})
