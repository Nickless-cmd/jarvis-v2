import { render, act } from '@testing-library/react-native'
import { VideoGenerationCard } from './VideoGenerationCard'
import { ImageGenerationCard } from './ImageGenerationCard'

/**
 * Uret er ikke pynt.
 *
 * `pollinations_image` er målt til ~8 s; `pollinations_video` bruger 39 s på
 * pipelinen og har op til 600 s timeout. Et prik-gitter der pulser i ti
 * minutter siger ikke noget andet efter otte minutter end efter ét — og det er
 * dér man tror turen er hængt og lukker appen. Uret er den eneste oplysning
 * der ændrer sig, så testen måler at det TÆLLER, ikke bare at det står der.
 */

beforeEach(() => jest.useFakeTimers())
afterEach(() => jest.useRealTimers())

describe('VideoGenerationCard', () => {
  it('siger hvad der sker', async () => {
    const s = await render(<VideoGenerationCard />)
    expect(s.getByTestId('video-generation-progress')).toBeTruthy()
    expect(s.getByLabelText('Genererer video')).toBeTruthy()
  })

  it('uret TAELLER', async () => {
    const s = await render(<VideoGenerationCard />)
    expect(s.getByTestId('video-generation-ur')).toHaveTextContent('0 s')
    await act(async () => { jest.advanceTimersByTime(7000) })
    expect(s.getByTestId('video-generation-ur')).toHaveTextContent('7 s')
  })

  it('over et minut staar der minutter og sekunder', async () => {
    const s = await render(<VideoGenerationCard />)
    await act(async () => { jest.advanceTimersByTime(95_000) })
    expect(s.getByTestId('video-generation-ur')).toHaveTextContent('1:35')
  })

  it('er IKKE det samme kort som billedernes', async () => {
    const video = await render(<VideoGenerationCard />)
    expect(video.queryByTestId('image-generation-progress')).toBeNull()
    video.unmount()
    const billede = await render(<ImageGenerationCard />)
    expect(billede.queryByTestId('video-generation-progress')).toBeNull()
  })
})
