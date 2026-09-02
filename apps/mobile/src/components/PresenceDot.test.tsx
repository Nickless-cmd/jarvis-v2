import { render } from '@testing-library/react-native'
import { PresenceDot } from './PresenceDot'

describe('PresenceDot', () => {
  it('viser hvad han laver', async () => {
    const s = await render(<PresenceDot presence={{ state: 'working' }} />)
    expect(s.getByText('arbejder')).toBeTruthy()
  })

  it('viser hvornaar hjertet sidst slog', async () => {
    const s = await render(<PresenceDot presence={{ state: 'awake', last_beat_ago_s: 120 }} />)
    expect(s.getByText('vågen · for 2 min siden')).toBeTruthy()
  })

  // En netvaerksfejl er praecis det oejeblik hvor fristelsen til at vise noget
  // levende er stoerst — og hvor det ville vaere en loegn.
  it('siger det aabent naar vi ikke kan se ham', async () => {
    const s = await render(
      <PresenceDot presence={{ state: 'unknown', reason: 'kunne ikke nå Jarvis' }} />
    )
    expect(s.getByText('kunne ikke nå Jarvis')).toBeTruthy()
  })

  it('har en laesbar etiket for skaermlaesere', async () => {
    const s = await render(<PresenceDot presence={{ state: 'quiet', last_beat_ago_s: 7200 }} />)
    expect(s.getByLabelText('Jarvis er stille · for 2 t siden')).toBeTruthy()
  })
})
