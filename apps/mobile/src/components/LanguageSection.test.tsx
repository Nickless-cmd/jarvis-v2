import { fireEvent, render, waitFor } from '@testing-library/react-native'
import { I18nProvider } from '../i18n/I18nContext'
import { LanguageSection } from './LanguageSection'

const mockSetAccountLanguage = jest.fn(
  async (_config: unknown, _language: unknown) => undefined
)
jest.mock('../lib/apiClient', () => ({
  setAccountLanguage: (config: unknown, language: unknown) => mockSetAccountLanguage(config, language)
}))

const cfg = { apiBaseUrl: 'https://x/', authToken: 'tok' }

describe('LanguageSection', () => {
  beforeEach(() => {
    jest.useFakeTimers()
    mockSetAccountLanguage.mockClear()
  })

  afterEach(() => {
    jest.clearAllTimers()
    jest.useRealTimers()
  })

  it('skifter app-sprog med det samme og gemmer paa kontoen', async () => {
    const screen = await render(
      <I18nProvider initialLocale="da">
        <LanguageSection config={cfg} currentLanguage="da" />
      </I18nProvider>
    )

    expect(screen.getByText('Sprog')).toBeTruthy()
    await fireEvent.press(screen.getByText('English'))

    await waitFor(() => expect(mockSetAccountLanguage).toHaveBeenCalledWith(cfg, 'en'))
    expect(screen.getByText('Language')).toBeTruthy()
    expect(screen.getByText('Saved')).toBeTruthy()
  })
})
