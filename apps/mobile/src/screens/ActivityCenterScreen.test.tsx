import { fireEvent, render } from '@testing-library/react-native'
import { ActivityCenterScreen } from './ActivityCenterScreen'

it('shows active runs as a mobile activity center', async () => {
  const screen = await render(
    <ActivityCenterScreen
      onClose={jest.fn()}
      runs={[{ sessionId: 's1', runId: 'r1', status: 'working' }]}
      outboxCount={2}
      presenceSummary="Pixel aktiv"
    />
  )

  expect(screen.getByText('Aktivitet')).toBeTruthy()
  expect(screen.getByText('r1')).toBeTruthy()
  expect(screen.getByText('2 i kø')).toBeTruthy()
})

it('viser notifikationer og kan godkende', async () => {
  const afgoer = jest.fn().mockResolvedValue({ ok: true, fejl: '' })
  const { findByText, getByText } = await render(
    <ActivityCenterScreen
      onClose={() => {}}
      runs={[]}
      notifikationer={[{
        id: '1', slags: 'approval', titel: 'Vil du tillade bash?', tekst: '',
        session_id: 's-1', oprettet: new Date().toISOString(),
        kan_afgoere: true, foraeldet: false,
      }]}
      onAfgoer={afgoer}
    />,
  )
  await findByText('Vil du tillade bash?')
  fireEvent.press(getByText('Godkend'))
  expect(afgoer).toHaveBeenCalledWith('1', true)
})

it('en fejl ser ikke ud som en tom liste', async () => {
  const { findByText, queryByText } = await render(
    <ActivityCenterScreen onClose={() => {}} runs={[]} notifikationer={null} notifFejl />,
  )
  await findByText(/kunne ikke hentes/i)
  expect(queryByText(/Ingen notifikationer/)).toBeNull()
})
