import { popRoute, pushRoute, replaceTopRoute, topRoute, type MobileRoute } from './mobileRoutes'

describe('mobileRoutes', () => {
  it('pushes and reads the top route', () => {
    const stack = pushRoute([], { name: 'settings' })
    expect(topRoute(stack)).toEqual({ name: 'settings' })
  })

  it('moves an existing route to the top instead of duplicating it', () => {
    const stack = pushRoute(
      [{ name: 'settings' }, { name: 'artifacts' }],
      { name: 'settings' },
    )
    expect(stack).toEqual([{ name: 'artifacts' }, { name: 'settings' }])
  })

  it('pops only the top route', () => {
    const stack: MobileRoute[] = [{ name: 'settings' }, { name: 'activity' }]
    expect(popRoute(stack)).toEqual([{ name: 'settings' }])
    expect(popRoute([])).toEqual([])
  })

  it('replaces the top route and keeps the rest of the stack', () => {
    const stack: MobileRoute[] = [{ name: 'settings' }, { name: 'activity' }]
    expect(replaceTopRoute(stack, { name: 'images' })).toEqual([{ name: 'settings' }, { name: 'images' }])
    expect(replaceTopRoute([], { name: 'images' })).toEqual([{ name: 'images' }])
  })
})
