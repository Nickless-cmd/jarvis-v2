import { bubble } from './bubbleModule'

// I jest findes NativeModules.BubbleModule ikke → guard skal aktiveres.
describe('bubbleModule guard (intet native modul)', () => {
  it('isSupported → false uden native modul', async () => {
    expect(await bubble.isSupported()).toBe(false)
  })
  it('float/show/setPersistent kaster ikke', () => {
    expect(() => bubble.floatCurrentChat('s1', 'Titel')).not.toThrow()
    expect(() => bubble.showConversationBubble('s1', 'Titel', 'Hej')).not.toThrow()
    expect(() => bubble.setPersistent(true, 's1', 'Titel')).not.toThrow()
  })
})
