import { fireEvent, render } from '@testing-library/react-native'
import { ArtifactsScreen } from './ArtifactsScreen'

jest.mock('../state/AuthContext', () => ({
  useAuth: () => ({ config: { apiBaseUrl: 'https://api.srvlab.dk/', authToken: 'token' } })
}))

const item = (rel: string, over: Record<string, unknown> = {}) => ({
  path: `/media/projects/jarvis-v2/${rel}`, rel, lastAt: '2026-09-18T17:40:00+00:00',
  sessionId: 'chat-1', sessionTitle: 'yo... du må lige samle op',
  edits: 2, sessionCount: 1, add: 42, del: 19, ...over,
})
const liste = (items: ReturnType<typeof item>[]) => ({
  ok: true, root: '/media/projects/jarvis-v2', scanned: 1463, total: items.length, items,
})

it('viser filerne med navn, mappe og grøn/rød linjetal', async () => {
  const screen = await render(
    <ArtifactsScreen onClose={jest.fn()} initial={liste([item('core/services/decision_review_daemon.py'), item('README.md', { add: 308, del: 0 })])} />
  )
  expect(screen.getByText('Artefakter')).toBeTruthy()
  expect(screen.getByText('decision_review_daemon.py')).toBeTruthy()
  expect(screen.getByText('core/services')).toBeTruthy()
  expect(screen.getByText('+42')).toBeTruthy()
  expect(screen.getByText('−19')).toBeTruthy()
  // En ren tilføjelse viser intet «−0».
  expect(screen.queryByText('−0')).toBeNull()
  expect(screen.getByText('Læst ud af 1463 svar')).toBeTruthy()
})

it('et tryk åbner samtalen hvor filen sidst blev rørt', async () => {
  const aabn = jest.fn()
  const screen = await render(
    <ArtifactsScreen onClose={jest.fn()} onOpenSession={aabn} initial={liste([item('README.md')])} />
  )
  fireEvent.press(screen.getByTestId('artefakt-README.md'))
  expect(aabn).toHaveBeenCalledWith('chat-1')
})

it('ærlig tom tilstand', async () => {
  const screen = await render(<ArtifactsScreen onClose={jest.fn()} initial={liste([])} />)
  expect(screen.getByText('Ingen artefakter endnu.')).toBeTruthy()
})

// Før var fejl og tom den samme skærm — det var sådan den brækkede rute gemte sig.
it('en fejl vises som en fejl, ikke som tom', async () => {
  const screen = await render(
    <ArtifactsScreen onClose={jest.fn()} initial={{ ok: false, root: '', scanned: 0, total: 0, items: [], error: 'ingen gyldig mappe' }} />
  )
  expect(screen.getByText('Kunne ikke hente artefakter')).toBeTruthy()
  expect(screen.getByText('ingen gyldig mappe')).toBeTruthy()
  expect(screen.queryByText('Ingen artefakter endnu.')).toBeNull()
})
