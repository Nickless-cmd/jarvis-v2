import { render } from '@testing-library/react-native'
import { ArtifactsScreen } from './ArtifactsScreen'

jest.mock('../state/AuthContext', () => ({
  useAuth: () => ({ config: { apiBaseUrl: 'https://api.srvlab.dk/', authToken: 'token' } })
}))

it('viser artifacts som et bibliotek', async () => {
  const screen = await render(
    <ArtifactsScreen
      onClose={jest.fn()}
      initialArtifacts={[{
        id: 'a1',
        kind: 'patch',
        title: 'Byg memory-skærm',
        detail: '2 files changed',
        createdAt: '2026-09-05T10:00:00Z'
      }]}
    />
  )

  expect(screen.getByText('Artifacts')).toBeTruthy()
  expect(screen.getByText('Byg memory-skærm')).toBeTruthy()
  expect(screen.getByText('Patch')).toBeTruthy()
  expect(screen.getByText('2 files changed')).toBeTruthy()
  expect(screen.getByText('Preview')).toBeTruthy()
  expect(screen.getByText('Senest')).toBeTruthy()
})

it('viser ærlig tom tilstand', async () => {
  const screen = await render(<ArtifactsScreen onClose={jest.fn()} initialArtifacts={[]} />)
  expect(screen.getByText('Ingen artifacts endnu.')).toBeTruthy()
})
