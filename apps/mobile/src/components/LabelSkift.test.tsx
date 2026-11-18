import { render } from '@testing-library/react-native'
import { Animated } from 'react-native'
import { LabelSkift } from './LabelSkift'

jest.mock('../lib/useReducedMotion', () => ({ useReducedMotion: () => mockReduced }))

let mockReduced = false

const animation = (): Animated.CompositeAnimation => ({
  start: (callback) => callback?.({ finished: true }),
  stop: jest.fn(),
  reset: jest.fn(),
})

describe('LabelSkift', () => {
  let spring: jest.SpyInstance
  let timing: jest.SpyInstance

  beforeEach(() => {
    mockReduced = false
    spring = jest.spyOn(Animated, 'spring').mockImplementation(animation)
    timing = jest.spyOn(Animated, 'timing').mockImplementation(animation)
  })

  afterEach(() => {
    spring.mockRestore()
    timing.mockRestore()
  })

  it('første tegning starter ingen animation', async () => {
    await render(<LabelSkift tekst="Klar" arbejder={false} farve="#fff" />)

    expect(spring).not.toHaveBeenCalled()
    expect(timing).not.toHaveBeenCalled()
  })

  it('hver ændret tekst giver en ny indgangsanimation', async () => {
    const s = await render(<LabelSkift tekst="Før" arbejder={false} farve="#fff" />)

    await s.rerender(<LabelSkift tekst="Anden" arbejder={false} farve="#fff" />)
    expect(spring).toHaveBeenCalledTimes(1)

    await s.rerender(<LabelSkift tekst="Tredje" arbejder={false} farve="#fff" />)
    expect(spring).toHaveBeenCalledTimes(2)
  })

  it('uændret tekst over flere tegninger starter ingen ny animation', async () => {
    const s = await render(<LabelSkift tekst="Stabil" arbejder={false} farve="#fff" />)

    await s.rerender(<LabelSkift tekst="Stabil" arbejder={false} farve="#fff" />)
    await s.rerender(<LabelSkift tekst="Stabil" arbejder={false} farve="#fff" />)
    await s.rerender(<LabelSkift tekst="Stabil" arbejder={false} farve="#fff" />)

    expect(spring).not.toHaveBeenCalled()
    expect(timing).not.toHaveBeenCalled()
  })

  it('reduceret bevægelse starter ingen animation ved skift', async () => {
    mockReduced = true
    const s = await render(<LabelSkift tekst="Arbejder" arbejder farve="#fff" />)

    await s.rerender(<LabelSkift tekst="Færdig" arbejder={false} farve="#fff" />)

    expect(spring).not.toHaveBeenCalled()
    expect(timing).not.toHaveBeenCalled()
  })
})
