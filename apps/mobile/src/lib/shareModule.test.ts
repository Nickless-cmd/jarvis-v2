import { deling } from './shareModule'

// I jest findes NativeModules.ShareModule ikke → wrapperen skal være stum,
// ikke kaste. En manglende bro må ikke vælte opstarten.
it('giver ingen deling når broen mangler', async () => {
  await expect(deling.vedOpstart()).resolves.toBeNull()
})

it('lytteren er en no-op der stadig kan afmeldes', () => {
  const stop = deling.lyt(() => undefined)
  expect(typeof stop).toBe('function')
  expect(() => stop()).not.toThrow()
})
