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

// V4: mobilen kunne ikke rydde en notifikation — desk kunne, via et tryk der
// sendte /set. `run_done` og alt med `kilde='egen'` (fx `release`) lukkes
// aldrig af hydreringen; uden et tryk-igennem sad taelleren fast og voksede,
// indtil man aabnede desk.
it('en post uden handling er trykbar — den aabner samtalen', async () => {
  const aabn = jest.fn()
  const { findByText, getByText } = await render(
    <ActivityCenterScreen
      onClose={() => {}}
      runs={[]}
      notifikationer={[{
        id: '1', slags: 'run_done', titel: 'Svaret er klar', tekst: '',
        session_id: 's-1', oprettet: new Date().toISOString(),
        kan_afgoere: false, foraeldet: false,
      }]}
      onAabn={aabn}
    />,
  )
  await findByText('Svaret er klar')
  fireEvent.press(getByText('Svaret er klar'))
  expect(aabn).toHaveBeenCalledWith(expect.objectContaining({ id: '1', session_id: 's-1' }))
})

// Samme regel som desk: en post MED en afgoerelse har sine egne
// Godkend/Afvis-knapper og maa ikke ogsaa reagere paa et tryk paa kortet —
// ellers kan et tryk ved siden af en knap lukke posten uden en beslutning.
it('en post der kan afgoeres reagerer IKKE paa et tryk paa selve kortet', async () => {
  const aabn = jest.fn()
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
      onAabn={aabn}
    />,
  )
  await findByText('Vil du tillade bash?')
  fireEvent.press(getByText('Vil du tillade bash?'))
  expect(aabn).not.toHaveBeenCalled()
})
