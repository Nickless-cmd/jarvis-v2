import { act, fireEvent, render } from '@testing-library/react-native'
import { ThinkingSummary } from './ThinkingSummary'

describe('ThinkingSummary', () => {
  it('viser varigheden', async () => {
    const screen = await render(<ThinkingSummary seconds={14} text="hm" />)
    expect(screen.getByText('Tænkte i 14 s')).toBeTruthy()
  })

  it('bruger dansk komma og skjuler tom decimal', async () => {
    const a = await render(<ThinkingSummary seconds={3.4} text="x" />)
    expect(a.getByText('Tænkte i 3,4 s')).toBeTruthy()
  })

  it('skifter til minutter over 60 s', async () => {
    const screen = await render(<ThinkingSummary seconds={95} text="x" />)
    expect(screen.getByText('Tænkte i 1 min 35 s')).toBeTruthy()
  })

  // Uden en måling skriver vi ikke «Tænkte» — det ville være en paastand vi
  // ikke har daekning for.
  it('viser INTET uden maalt varighed', async () => {
    const a = await render(<ThinkingSummary text="noget" />)
    expect(a.queryByTestId('thinking-summary')).toBeNull()
    const b = await render(<ThinkingSummary seconds={0} text="noget" />)
    expect(b.queryByTestId('thinking-summary')).toBeNull()
  })

  it('folder teksten ud og sammen igen', async () => {
    const screen = await render(<ThinkingSummary seconds={9} text="min overvejelse" />)
    expect(screen.queryByText('min overvejelse')).toBeNull()

    await act(async () => { fireEvent.press(screen.getByTestId('thinking-summary')) })
    expect(screen.getByText('min overvejelse')).toBeTruthy()

    await act(async () => { fireEvent.press(screen.getByTestId('thinking-summary')) })
    expect(screen.queryByText('min overvejelse')).toBeNull()
  })

  it('uden tekst er linjen ikke tryk-bar', async () => {
    const screen = await render(<ThinkingSummary seconds={5} />)
    expect(screen.getByTestId('thinking-summary').props.accessibilityState?.disabled).toBe(true)
  })
})
