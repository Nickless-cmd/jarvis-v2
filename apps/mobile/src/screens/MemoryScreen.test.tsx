import { act, fireEvent, render } from '@testing-library/react-native'
import { MemoryScreen } from './MemoryScreen'

jest.mock('../state/AuthContext', () => ({
  useAuth: () => ({ config: { apiBaseUrl: 'https://api.srvlab.dk/', authToken: 'token' } })
}))

beforeEach(() => {
  global.fetch = jest.fn().mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => ({
      memory_md: '## Preferencer\n- Kaffe sort',
      user_md: '# Bjørn\nBor i Svendborg',
      recent_sensory: [],
      brain_count: 2
    })
  })
})

it('viser memory-sektioner og brain count', async () => {
  const screen = await render(
    <MemoryScreen
      onClose={jest.fn()}
      onOpenDataControls={jest.fn()}
      initialMemory={{
        sections: [{ title: 'Preferencer', preview: 'Kaffe sort' }],
        identityPreview: '# Bjørn\nBor i Svendborg',
        recentSenses: [],
        brainCount: 2
      }}
    />
  )

  expect(screen.getByText('Hukommelse')).toBeTruthy()
  expect(screen.getByText('Preferencer')).toBeTruthy()
  expect(screen.getByText('2 private brain-poster')).toBeTruthy()
})

it('har en tydelig vej til eksport og sletning', async () => {
  const openData = jest.fn()
  const screen = await render(
    <MemoryScreen
      onClose={jest.fn()}
      onOpenDataControls={openData}
      initialMemory={{ sections: [], identityPreview: '', recentSenses: [], brainCount: 0 }}
    />
  )

  await act(async () => { fireEvent.press(screen.getByText('Datastyring')) })
  expect(openData).toHaveBeenCalledTimes(1)
})
