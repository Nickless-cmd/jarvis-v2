import { fireEvent, render, waitFor } from '@testing-library/react-native'
import { WorkspacePicker } from './WorkspacePicker'
import * as ws from '../lib/workspaceApi'

const config = { apiBaseUrl: 'https://x/', authToken: 't' } as never

beforeEach(() => {
  jest.restoreAllMocks()
  jest.spyOn(ws, 'hentServerRoedder').mockResolvedValue([
    { navn: 'repo', sti: '/media/projects/jarvis-v2' },
  ])
  jest.spyOn(ws, 'hentTrae').mockResolvedValue([
    { navn: 'home', mappe: true },
    { navn: 'noter.txt', mappe: false },
  ])
})

const base = () => ({
  aaben: true, onClose: jest.fn(), config, nuvaerende: null, onVaelg: jest.fn(),
})

it('en server-rod vises MED sin sti', async () => {
  // Et valg man ikke kan se konsekvensen af er et gaet.
  const screen = await render(<WorkspacePicker {...base()} />)
  await waitFor(() => expect(screen.getByText('repo')).toBeTruthy())
  expect(screen.getByText('/media/projects/jarvis-v2')).toBeTruthy()
})

it('at vaelge en server-rod sender NAVNET, ikke stien', async () => {
  // Ruten rolle-kontrollerer paa navnet; en sti ville blive afvist.
  const p = base()
  const screen = await render(<WorkspacePicker {...p} />)
  await waitFor(() => expect(screen.getByTestId('rod-repo')).toBeTruthy())
  fireEvent.press(screen.getByTestId('rod-repo'))
  expect(p.onVaelg).toHaveBeenCalledWith('container', 'repo')
})

it('mapper kan aabnes — filer kan IKKE', async () => {
  const screen = await render(<WorkspacePicker {...base()} />)
  await waitFor(() => expect(screen.getByTestId('mappe-home')).toBeTruthy())
  // Filen staar der, saa man kan se at man er det rigtige sted...
  expect(screen.getByText('noter.txt')).toBeTruthy()
  // ... men den er ikke en knap.
  expect(screen.queryByTestId('mappe-noter.txt')).toBeNull()
})

it('«brug denne mappe» vaelger den sti man staar i', async () => {
  const p = base()
  const screen = await render(<WorkspacePicker {...p} />)
  await waitFor(() => expect(screen.getByTestId('mappe-home')).toBeTruthy())
  fireEvent.press(screen.getByTestId('mappe-home'))
  await waitFor(() => expect(screen.getByText('/home')).toBeTruthy())
  fireEvent.press(screen.getByTestId('ws-vaelg-denne'))
  expect(p.onVaelg).toHaveBeenCalledWith('workstation', '/home')
})

it('en doed forbindelse SIGES — den ligner ellers en tom mappe', async () => {
  // De to ser ens ud og betyder stik modsat.
  jest.spyOn(ws, 'hentTrae').mockRejectedValue(new Error('bro nede'))
  const screen = await render(<WorkspacePicker {...base()} />)
  await waitFor(() => expect(screen.getByText(/svarer computeren/)).toBeTruthy())
})

it('aabner dér hvor sessionen allerede peger hen', async () => {
  const spion = jest.spyOn(ws, 'hentTrae').mockResolvedValue([])
  await render(
    <WorkspacePicker {...base()} nuvaerende={{ kind: 'workstation', root: '/home/bs/p' }} />,
  )
  await waitFor(() => expect(spion).toHaveBeenCalledWith(config, 'workstation', '/home/bs/p', ''))
})
