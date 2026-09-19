import { fireEvent, render, waitFor } from '@testing-library/react-native'
import { SvarstilSection } from './SvarstilSection'

const mockApiFetch = jest.fn()
jest.mock('../lib/apiClient', () => ({
  apiFetch: (...a: unknown[]) => mockApiFetch(...a),
}))

const cfg = { apiBaseUrl: 'https://x/', authToken: 'tok' }

describe('SvarstilSection', () => {
  beforeEach(() => mockApiFetch.mockReset())

  it('viser den gemte stil og sender et skift som objekt (ikke JSON-streng)', async () => {
    mockApiFetch.mockResolvedValueOnce({ output_style: 'technical' })
    mockApiFetch.mockResolvedValueOnce({ status: 'ok' })
    const screen = await render(<SvarstilSection config={cfg} />)
    await waitFor(() =>
      expect(screen.getByLabelText('Svarstil Teknisk').props.accessibilityState.selected).toBe(true))
    fireEvent.press(screen.getByLabelText('Svarstil Kort'))
    await waitFor(() => expect(mockApiFetch).toHaveBeenLastCalledWith(
      cfg, '/api/preferences', { method: 'POST', body: { output_style: 'concise' } }))
    expect(await screen.findByText('Gemt')).toBeTruthy()
  })

  it('ruller tilbage og viser fejlen hvis serveren afviser', async () => {
    mockApiFetch.mockResolvedValueOnce({ output_style: 'balanced' })
    mockApiFetch.mockRejectedValueOnce(new Error('HTTP 400: ukendt stil'))
    const screen = await render(<SvarstilSection config={cfg} />)
    await waitFor(() =>
      expect(screen.getByLabelText('Svarstil Normal').props.accessibilityState.selected).toBe(true))
    fireEvent.press(screen.getByLabelText('Svarstil Uddybende'))
    expect(await screen.findByText('HTTP 400: ukendt stil')).toBeTruthy()
    expect(screen.getByLabelText('Svarstil Normal').props.accessibilityState.selected).toBe(true)
  })
})
