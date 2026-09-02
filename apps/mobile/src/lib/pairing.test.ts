import { parsePairingPayload } from './pairing'

it('parser JSON {url, code}', () => {
  expect(parsePairingPayload('{"url":"https://x.dk/","code":"abc"}')).toEqual({ url: 'https://x.dk/', code: 'abc' })
})

it('parser kort form {u, c}', () => {
  expect(parsePairingPayload('{"u":"https://y.dk/","c":"k9"}')).toEqual({ url: 'https://y.dk/', code: 'k9' })
})

it('bar kode → default url', () => {
  const r = parsePairingPayload('raw-code-123')
  expect(r?.code).toBe('raw-code-123')
  expect(r?.url).toBe('https://api.srvlab.dk/')
})

it('JSON uden kode → null', () => {
  expect(parsePairingPayload('{"url":"https://x.dk/"}')).toBeNull()
})

it('tom → null', () => {
  expect(parsePairingPayload('   ')).toBeNull()
})
