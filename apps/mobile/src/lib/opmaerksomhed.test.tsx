import { act, fireEvent, render } from '@testing-library/react-native'
import { udgiv, udenSamtale, skalKvittere, type Opmaerksomhed } from './opmaerksomhed'
import { OpmaerksomhedsLinje } from '../components/OpmaerksomhedsLinje'

const p = (session_id: string, tilstand: Opmaerksomhed['tilstand'], titel = 'T') =>
  ({ session_id, run_id: 'r', tilstand, titel, tekst: '', tid: 1 })
const tom = { waiting: 0, failed: 0, review: 0, running: 0 }

describe('tilstands-hjernen paa telefonen', () => {
  beforeEach(() => udgiv(null))

  it('linjen er tavs naar intet kraever dig', async () => {
    const s = await render(<OpmaerksomhedsLinje onAabn={() => {}} />)
    await act(async () => udgiv({ tilstand: 'idle', etiket: 'Intet kræver dig', antal: tom, baggrund: 2, indbakke: 24, fokus: null, punkter: [] }))
    expect(s.queryByTestId('opmaerksomhed')).toBeNull()
  })

  it('viser den vindende tilstand med antal, og tryk aabner fokus-samtalen', async () => {
    const aabn = jest.fn()
    const s = await render(<OpmaerksomhedsLinje onAabn={aabn} />)
    const f = p('s-1', 'review', 'Kæledyret')
    await act(async () => udgiv({ tilstand: 'review', etiket: 'Færdig — se svaret', antal: { ...tom, review: 2 }, baggrund: 0, indbakke: 0, fokus: f, punkter: [f, p('s-2', 'review')] }))
    expect(s.getByText('Færdig — se svaret · 2')).toBeTruthy()
    expect(s.getByText('Kæledyret')).toBeTruthy()
    await fireEvent.press(s.getByTestId('opmaerksomhed'))
    expect(aabn).toHaveBeenCalledWith('s-1')
  })

  it('kvittering fjerner samtalen og regner tilstanden om', () => {
    const o: Opmaerksomhed = { tilstand: 'failed', etiket: 'Noget gik galt', antal: { ...tom, failed: 1, running: 1 }, baggrund: 0, indbakke: 0,
      fokus: p('s-1', 'failed'), punkter: [p('s-1', 'failed'), p('s-2', 'running')] }
    expect(skalKvittere(o, 's-1')).toBe(true)
    expect(skalKvittere(o, 's-2')).toBe(false) // en der kører skal ikke kvitteres væk
    const e = udenSamtale(o, 's-1')
    expect(e.tilstand).toBe('running')
    expect(e.etiket).toBe('Arbejder')
    expect(e.antal).toEqual({ ...tom, running: 1 })
  })
})
