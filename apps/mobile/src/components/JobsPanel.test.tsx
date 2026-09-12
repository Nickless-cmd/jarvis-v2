import { fireEvent, render, waitFor } from '@testing-library/react-native'
import { JobsPanel } from './JobsPanel'
import * as api from '../lib/jobsApi'
import type { BaggrundsJob } from '../lib/jobsApi'

const config = { apiBaseUrl: 'https://x/', authToken: 't' } as never
const j = (o: Partial<BaggrundsJob> = {}): BaggrundsJob => ({
  id: 'bg_1', kilde: 'operator', navn: 'bg_1', kommando: 'npm test',
  status: 'running', pid: 42, sekunder: 187, exitCode: null, kanPause: true, ...o,
})

beforeEach(() => jest.restoreAllMocks())
const base = () => ({ aaben: true, onClose: jest.fn(), config })

it('viser jobbet med kommando og koerselstid', async () => {
  jest.spyOn(api, 'hentJobs').mockResolvedValue({ jobs: [j()], broOk: true })
  const screen = await render(<JobsPanel {...base()} />)
  await waitFor(() => expect(screen.getByText('npm test')).toBeTruthy())
  expect(screen.getByText('3 min 07 s')).toBeTruthy()
})

it('et PAUSET job tilbyder at genoptage, ikke at pause igen', async () => {
  jest.spyOn(api, 'hentJobs').mockResolvedValue({ jobs: [j({ status: 'paused' })], broOk: true })
  const screen = await render(<JobsPanel {...base()} />)
  await waitFor(() => expect(screen.getByTestId('job-resume-bg_1')).toBeTruthy())
  expect(screen.queryByTestId('job-pause-bg_1')).toBeNull()
})

it('pause sender pause — og henter STRAKS igen', async () => {
  // Et tryk der foerst ser ud til at virke tre sekunder senere, laeses som et
  // tryk der ikke virkede.
  const hent = jest.spyOn(api, 'hentJobs').mockResolvedValue({ jobs: [j()], broOk: true })
  const handling = jest.spyOn(api, 'jobHandling').mockResolvedValue(undefined)
  const screen = await render(<JobsPanel {...base()} />)
  await waitFor(() => expect(screen.getByTestId('job-pause-bg_1')).toBeTruthy())
  const foer = hent.mock.calls.length
  fireEvent.press(screen.getByTestId('job-pause-bg_1'))
  await waitFor(() => expect(handling).toHaveBeenCalledWith(config, expect.anything(), 'pause'))
  await waitFor(() => expect(hent.mock.calls.length).toBeGreaterThan(foer))
})

it('et job der ikke kan pauses har ingen pause-knap — men kan stoppes', async () => {
  jest.spyOn(api, 'hentJobs').mockResolvedValue({
    jobs: [j({ kanPause: false, status: 'exited', exitCode: 3 })], broOk: true,
  })
  const screen = await render(<JobsPanel {...base()} />)
  await waitFor(() => expect(screen.getByTestId('job-stop-bg_1')).toBeTruthy())
  expect(screen.queryByTestId('job-pause-bg_1')).toBeNull()
})

it('en DOED bro siges hoejt — en tom liste maa ikke betyde to ting', async () => {
  jest.spyOn(api, 'hentJobs').mockResolvedValue({ jobs: [], broOk: false })
  const screen = await render(<JobsPanel {...base()} />)
  await waitFor(() => expect(screen.getByTestId('jobs-bro-nede')).toBeTruthy())
})

it('tom OG rask bro siger bare at der ingenting koerer', async () => {
  jest.spyOn(api, 'hentJobs').mockResolvedValue({ jobs: [], broOk: true })
  const screen = await render(<JobsPanel {...base()} />)
  await waitFor(() => expect(screen.getByTestId('jobs-tom')).toBeTruthy())
  expect(screen.queryByTestId('jobs-bro-nede')).toBeNull()
})

it('et afsluttet job viser sin exit-kode frem for en tid', async () => {
  jest.spyOn(api, 'hentJobs').mockResolvedValue({
    jobs: [j({ status: 'exited', exitCode: 3, kanPause: false })], broOk: true,
  })
  const screen = await render(<JobsPanel {...base()} />)
  await waitFor(() => expect(screen.getByText('stop 3')).toBeTruthy())
})

it('LUKKET panel henter slet ikke', async () => {
  // Ellers ville den pulse hvert 3. sekund resten af appens levetid.
  const hent = jest.spyOn(api, 'hentJobs').mockResolvedValue({ jobs: [], broOk: true })
  await render(<JobsPanel {...base()} aaben={false} />)
  expect(hent).not.toHaveBeenCalled()
})
