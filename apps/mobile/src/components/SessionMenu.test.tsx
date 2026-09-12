import { Alert } from 'react-native'
import { fireEvent, render } from '@testing-library/react-native'
import { SessionMenu } from './SessionMenu'
import type { ChatSession } from '../lib/types'

// Bjoern bad om fire handlinger "ligesom i desk appen". Maalt 12/9-2026 kan
// desk-appen kun TO af dem - rename og delete. Pin og arkivér fandtes hverken
// i desk, i api'et eller som kolonne.
//
// Tre af de fire kan fortrydes ved at goere det modsatte. Sletning kan ikke,
// og derfor er den den eneste der spoerger.

const s = (o: Partial<ChatSession> = {}): ChatSession => ({
  id: 's1', title: 'En samtale', updated_at: '2026-09-01T00:00:00Z', ...o,
})

const props = () => ({
  open: true, onClose: jest.fn(), onRename: jest.fn(),
  onDelete: jest.fn(), onSetFlags: jest.fn(),
})

it('fastgoer sender pinned=true', async () => {
  const p = props()
  const screen = await render(<SessionMenu {...p} session={s()} />)
  fireEvent.press(screen.getByText(/Fastgør øverst|Frigør/))
  expect(p.onSetFlags).toHaveBeenCalledWith('s1', { pinned: true })
})

it('en fastgjort samtale tilbyder at FRIGOERE, ikke at fastgoere igen', async () => {
  // En menu der tilbyder en tilstand man allerede er i, faar folk til at tro
  // at der skete noget.
  const p = props()
  const screen = await render(<SessionMenu {...p} session={s({ pinned: true })} />)
  expect(screen.getByText('Frigør')).toBeTruthy()
  fireEvent.press(screen.getByText(/Fastgør øverst|Frigør/))
  expect(p.onSetFlags).toHaveBeenCalledWith('s1', { pinned: false })
})

it('arkivér sender archived=true', async () => {
  const p = props()
  const a = await render(<SessionMenu {...p} session={s()} />)
  fireEvent.press(a.getByText(/Arkivér|Hent ud af arkiv/))
  expect(p.onSetFlags).toHaveBeenCalledWith('s1', { archived: true })
})

// ÉN render pr. test. To render() i samme test efterlader to traeer, og RNTL's
// oprydning bagefter rammer saa ikke dem begge: de FIRE foelgende tests fejlede
// alle paa «Unable to find an element with text» — og bestod enkeltvis.
it('en arkiveret samtale tilbyder at hente ud, ikke at arkivere igen', async () => {
  const p = props()
  const b = await render(<SessionMenu {...p} session={s({ archived: true })} />)
  expect(b.getByText('Hent ud af arkiv')).toBeTruthy()
  fireEvent.press(b.getByText(/Arkivér|Hent ud af arkiv/))
  expect(p.onSetFlags).toHaveBeenCalledWith('s1', { archived: false })
})

it('omdoeb: feltet aabner med det nuvaerende navn', async () => {
  const p = props()
  const screen = await render(<SessionMenu {...p} session={s()} />)
  fireEvent.press(screen.getByText('Omdøb'))
  const felt = await screen.findByPlaceholderText('Nyt navn')
  // Feltet er forudfyldt, saa man retter frem for at skrive forfra.
  expect(felt.props.value).toBe('En samtale')
})

it('SLETNING spoerger foerst', async () => {
  const spion = jest.spyOn(Alert, 'alert').mockImplementation(() => undefined)
  const p = props()
  const screen = await render(<SessionMenu {...p} session={s()} />)
  fireEvent.press(screen.getByText('Slet samtale'))
  expect(spion).toHaveBeenCalled()
  expect(String(spion.mock.calls[0]?.[1])).toContain('kan ikke fortrydes')
  // Og den sletter IKKE foer man bekraefter.
  expect(p.onDelete).not.toHaveBeenCalled()
  spion.mockRestore()
})

it('de tre andre spoerger IKKE — kun sletning kan ikke fortrydes', async () => {
  const spion = jest.spyOn(Alert, 'alert').mockImplementation(() => undefined)
  const p = props()
  const screen = await render(<SessionMenu {...p} session={s()} />)
  fireEvent.press(screen.getByText(/Fastgør øverst|Frigør/))
  expect(spion).not.toHaveBeenCalled()
  spion.mockRestore()
})

it('bekraeftelsen kalder onDelete', async () => {
  let bekraeft: (() => void) | undefined
  const spion = jest.spyOn(Alert, 'alert').mockImplementation((_t, _b, knapper) => {
    bekraeft = (knapper as { text: string; onPress?: () => void }[])
      .find((k) => k.text === 'Slet')?.onPress
  })
  const p = props()
  const screen = await render(<SessionMenu {...p} session={s()} />)
  fireEvent.press(screen.getByText('Slet samtale'))
  bekraeft?.()
  expect(p.onDelete).toHaveBeenCalledWith('s1')
  spion.mockRestore()
})
